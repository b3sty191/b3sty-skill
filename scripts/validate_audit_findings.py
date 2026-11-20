#!/usr/bin/env python3
"""Validate a b3sty audit `findings.json` so prose and JSON cannot disagree.

A `/b3sty-review` full audit writes findings as machine-checkable records with
one of three verdicts. The rules here enforce the discipline that makes the
audit trustworthy:

- `confirmed`   - a real boundary failure with a bounded observed result. Only
                  this verdict carries severity, and severity may not exceed the
                  demonstrated impact.
- `needs_validation` - a source-grounded lead blocked on a fact the review
                  could not settle (a live FXServer, a deployment convar, a
                  framework version). It names the exact blocker and a plan, and
                  it has NO severity - it is not a quiet low-confidence bug.
- `rejected`    - a candidate disproved during review, kept so the next run does
                  not re-report it without new evidence.

Usage:
    python3 validate_audit_findings.py <findings.json>
    python3 validate_audit_findings.py --selftest

Pure standard library.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

VERDICTS = {"confirmed", "needs_validation", "rejected"}
SURFACES = {
    "net_event", "builtin_event", "nui_callback", "command", "callback",
    "export", "http_handler", "sql", "xss", "state_bag", "other",
}
SEVERITIES = {"critical", "high", "medium", "low", "informational"}
CONFIDENCE = {"high", "medium", "low"}
TRACE_KINDS = {"entrypoint", "propagation", "sink"}
FINGERPRINT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$")

COMMON = {"fingerprint", "verdict", "surface", "title", "description", "trace", "evidence"}
BY_VERDICT = {
    "confirmed": COMMON | {"root_cause", "intended_behavior", "conditions", "abuse",
                           "remediation", "severity", "confidence"},
    "needs_validation": COMMON | {"claimed_root_cause", "blockers", "validation_plan"},
    "rejected": COMMON | {"claimed_root_cause", "reason"},
}
# Fields that must NOT appear under a verdict, so a needs_validation lead can
# never smuggle a severity and a confirmed record can never hide a blocker.
FORBIDDEN = {
    "confirmed": {"claimed_root_cause", "blockers", "validation_plan", "reason"},
    "needs_validation": {"severity", "confidence", "remediation", "abuse", "reason", "root_cause"},
    "rejected": {"severity", "confidence", "remediation", "abuse", "blockers",
                 "validation_plan", "root_cause"},
}


def err(errors, fp, msg):
    errors.append(f"[{fp}] {msg}")


def check_trace(trace, fp, errors):
    if not isinstance(trace, list) or not trace:
        err(errors, fp, "trace must be a non-empty array")
        return
    for i, step in enumerate(trace):
        if not isinstance(step, dict):
            err(errors, fp, f"trace[{i}] must be an object")
            continue
        kind = step.get("kind")
        if kind not in TRACE_KINDS:
            err(errors, fp, f"trace[{i}].kind must be one of {sorted(TRACE_KINDS)}")
        f = step.get("file")
        if not isinstance(f, str) or not f or f.startswith("/") or ".." in f.split("/"):
            err(errors, fp, f"trace[{i}].file must be a repo-relative path")
        if not isinstance(step.get("line"), int) or step.get("line", 0) < 1:
            err(errors, fp, f"trace[{i}].line must be a positive integer")
    if len(trace) > 1:
        if trace[0].get("kind") != "entrypoint":
            err(errors, fp, "a multi-step trace must start with an entrypoint")
        if trace[-1].get("kind") != "sink":
            err(errors, fp, "a multi-step trace must end with a sink")
        for i, step in enumerate(trace[1:-1], 1):
            if step.get("kind") != "propagation":
                err(errors, fp, f"trace[{i}] between ends must be propagation")
    else:
        if trace[0].get("kind") not in {"entrypoint", "sink"}:
            err(errors, fp, "a one-step trace uses kind entrypoint or sink")


def check_record(rec, errors, seen):
    fp = rec.get("fingerprint", "<no-fingerprint>")
    if not isinstance(rec, dict):
        errors.append("finding must be an object")
        return
    verdict = rec.get("verdict")
    if verdict not in VERDICTS:
        err(errors, fp, f"verdict must be one of {sorted(VERDICTS)}")
        return

    if not isinstance(rec.get("fingerprint"), str) or not FINGERPRINT_RE.match(rec.get("fingerprint", "")):
        err(errors, fp, "fingerprint must match ^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$")
    else:
        if rec["fingerprint"] in seen:
            err(errors, fp, "duplicate fingerprint")
        seen.add(rec["fingerprint"])

    for field in ("title", "description", "evidence"):
        if not isinstance(rec.get(field), str) or not rec.get(field, "").strip():
            err(errors, fp, f"{field} must be a non-empty string")
    if rec.get("surface") not in SURFACES:
        err(errors, fp, f"surface must be one of {sorted(SURFACES)}")

    allowed = BY_VERDICT[verdict]
    for key in rec:
        if key not in allowed:
            if key in FORBIDDEN[verdict]:
                err(errors, fp, f"'{key}' is not allowed on a {verdict} record")
            else:
                err(errors, fp, f"unknown field '{key}' on a {verdict} record")
    for key in allowed:
        if key not in rec:
            err(errors, fp, f"{verdict} record is missing '{key}'")

    check_trace(rec.get("trace"), fp, errors)

    if verdict == "confirmed":
        if rec.get("severity") not in SEVERITIES:
            err(errors, fp, f"severity must be one of {sorted(SEVERITIES)}")
        if rec.get("confidence") not in CONFIDENCE:
            err(errors, fp, f"confidence must be one of {sorted(CONFIDENCE)}")
        if not isinstance(rec.get("conditions"), list) or not rec.get("conditions"):
            err(errors, fp, "conditions must be a non-empty array")
        for field in ("root_cause", "intended_behavior", "abuse", "remediation"):
            if not isinstance(rec.get(field), str) or not rec.get(field, "").strip():
                err(errors, fp, f"{field} must be a non-empty string")
    elif verdict == "needs_validation":
        if not isinstance(rec.get("claimed_root_cause"), str) or not rec.get("claimed_root_cause", "").strip():
            err(errors, fp, "claimed_root_cause must be a non-empty string")
        if not isinstance(rec.get("blockers"), list) or not rec.get("blockers"):
            err(errors, fp, "blockers must be a non-empty array")
        plan = rec.get("validation_plan")
        if not isinstance(plan, dict):
            err(errors, fp, "validation_plan must be an object")
        else:
            extra = set(plan) - {"local", "live_test_server"}
            if extra:
                err(errors, fp, f"validation_plan has unknown keys {sorted(extra)}")
            has = [k for k in ("local", "live_test_server")
                   if isinstance(plan.get(k), str) and plan.get(k, "").strip()]
            if not has:
                err(errors, fp, "validation_plan needs a non-empty 'local' or 'live_test_server' step")
    else:  # rejected
        if not isinstance(rec.get("claimed_root_cause"), str) or not rec.get("claimed_root_cause", "").strip():
            err(errors, fp, "claimed_root_cause must be a non-empty string")
        if not isinstance(rec.get("reason"), str) or not rec.get("reason", "").strip():
            err(errors, fp, "reason must be a non-empty string")


def validate(data) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, list):
        return ["findings.json must be a top-level JSON array"]
    if len(data) > 2000:
        return ["findings.json has more than 2000 records"]
    seen: set[str] = set()
    for rec in data:
        check_record(rec, errors, seen)
    return errors


# --- selftest fixtures ---------------------------------------------------

_GOOD = [
    {
        "fingerprint": "shop-buy-trusts-client-price",
        "verdict": "confirmed",
        "surface": "net_event",
        "title": "shop:server:buy trusts the client price",
        "description": "The server grants the item using the price in the payload.",
        "trace": [
            {"kind": "entrypoint", "file": "core/server.lua", "line": 12, "note": "RegisterNetEvent"},
            {"kind": "sink", "file": "core/server.lua", "line": 20, "note": "addItem with client price"},
        ],
        "evidence": "price comes straight from data.price with no lookup",
        "root_cause": "server reads price from the client instead of its own config",
        "intended_behavior": "price is decided server-side from Config.Items",
        "conditions": ["player can trigger shop:server:buy"],
        "abuse": "a client sends price 0 and receives the item for free",
        "remediation": "look the price up in Config.Items server-side; ignore the payload price",
        "severity": "high",
        "confidence": "high",
    },
    {
        "fingerprint": "ace-check-depends-on-deploy-convar",
        "verdict": "needs_validation",
        "surface": "command",
        "title": "admin command gated only by an ACE that may be unset",
        "description": "The giveitem command checks an ACE whose grant is not in source.",
        "trace": [{"kind": "entrypoint", "file": "core/server.lua", "line": 44}],
        "evidence": "IsPlayerAceAllowed(src, 'shop.admin') with no matching add_ace in repo",
        "claimed_root_cause": "the ACE may be ungranted, leaving the command open",
        "blockers": ["the add_ace/add_principal lines live in server.cfg, not in the repo"],
        "validation_plan": {
            "live_test_server": "on a test server with no shop.admin grant, confirm a non-admin is refused",
        },
    },
    {
        "fingerprint": "nui-name-innerhtml",
        "verdict": "rejected",
        "surface": "xss",
        "title": "player name into innerHTML",
        "description": "Looked like stored XSS but the value is escaped first.",
        "trace": [{"kind": "sink", "file": "html/app.js", "line": 30}],
        "evidence": "the name is passed through escapeHtml() on line 28 before assignment",
        "claimed_root_cause": "player name rendered via innerHTML",
        "reason": "escapeHtml on line 28 neutralizes the value; no injection reaches the DOM",
    },
]

_BAD_CASES = [
    ([{**_GOOD[1], "severity": "high"}], "severity on needs_validation"),
    ([{**_GOOD[0], "severity": "banana"}], "bad severity enum"),
    ([_GOOD[0], _GOOD[0]], "duplicate fingerprint"),
    ([{**_GOOD[0], "fingerprint": "bad fingerprint!"}], "bad fingerprint chars"),
    ([{**_GOOD[0], "trace": [{"kind": "sink", "file": "/abs/path.lua", "line": 1}]}], "absolute path"),
    ([{k: v for k, v in _GOOD[0].items() if k != "remediation"}], "missing remediation"),
    ([{**_GOOD[1], "validation_plan": {}}], "empty validation_plan"),
    ([{**_GOOD[0], "trace": [{"kind": "propagation", "file": "a.lua", "line": 2},
                             {"kind": "sink", "file": "a.lua", "line": 3}]}], "trace not starting at entrypoint"),
]


def selftest() -> int:
    ok = True
    good_errors = validate(_GOOD)
    if good_errors:
        ok = False
        print("selftest FAIL: valid fixtures rejected:")
        for e in good_errors:
            print("  " + e)
    for data, label in _BAD_CASES:
        if not validate(data):
            ok = False
            print(f"selftest FAIL: bad fixture accepted ({label})")
    print("audit findings validator selftest passed." if ok else "audit findings validator selftest FAILED.")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("findings", nargs="?", help="path to findings.json")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return selftest()
    if not args.findings:
        parser.error("findings.json path required (or --selftest)")

    try:
        data = json.loads(open(args.findings, encoding="utf-8").read())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"could not read findings.json: {exc}", file=sys.stderr)
        return 2

    errors = validate(data)
    if errors:
        print(f"findings.json validation failed ({len(errors)} errors):")
        for e in errors[:100]:
            print("- " + e)
        return 1
    print(f"findings.json valid ({len(data)} records).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
