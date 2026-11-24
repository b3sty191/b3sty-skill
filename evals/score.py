#!/usr/bin/env python3
"""Score a review-mode audit against the planted defects in an eval case.

The eval cases under `evals/cases/` are small resources with documented,
intentionally planted vulnerabilities (see `evals/EXPECTATIONS.json`). Run the
skill in review mode (`modes/review.md`), full audit, against a case, point it at an output
directory, then score the `findings.json` it produced:

    python3 evals/score.py --expectations evals/EXPECTATIONS.json \\
        --case fivem_shop --findings <out>/findings.json

An expectation counts as caught when the findings file has a `confirmed` or
`needs_validation` record whose trace touches the expected file and whose
title/description/surface mentions one of the expectation's keywords. Each
finding can satisfy at most one expectation (maximum one-to-one matching), so
one broad finding cannot inflate recall. The score is recall (planted defects
found / planted defects), with how many of those catches were `confirmed`.

Cases may also list decoys in `EXPECTATIONS.json` (`"decoys": {case: [...]}`):
code that is correct but looks risky. A leftover finding that touches a decoy's
file and mentions its keywords is reported as a decoy hit - a false positive on
correct code. Remaining findings are listed so the reviewer can tell real
extras from noise.

This measures the auditor, not a resource. It is the skill's own benchmark.

    python3 evals/score.py --selftest

Pure standard library.
"""

from __future__ import annotations

import argparse
import json
import sys

USEFUL_VERDICTS = {"confirmed", "needs_validation"}


def finding_text(rec: dict) -> str:
    parts = [str(rec.get("title", "")), str(rec.get("description", "")),
             str(rec.get("surface", "")), str(rec.get("root_cause", "")),
             str(rec.get("claimed_root_cause", "")), str(rec.get("evidence", ""))]
    return " ".join(parts).lower()


def finding_files(rec: dict) -> list[str]:
    files = []
    for step in rec.get("trace", []) or []:
        f = step.get("file")
        if isinstance(f, str):
            files.append(f)
    return files


def file_matches(expected: str, actual_files: list[str]) -> bool:
    expected = expected.lstrip("./")
    for f in actual_files:
        f = f.lstrip("./")
        if f == expected or f.endswith("/" + expected) or f.endswith(expected):
            return True
    return False


def _matches(spec: dict, rec: dict) -> bool:
    if not file_matches(spec["file"], finding_files(rec)):
        return False
    keywords = [k.lower() for k in spec.get("keywords", [])]
    text = finding_text(rec)
    return not keywords or any(kw in text for kw in keywords)


def _max_matching(expectations: list[dict], usable: list[dict]) -> dict[int, int]:
    """Maximum bipartite matching expectation -> finding (Kuhn's algorithm)."""
    edges = [[i for i, rec in enumerate(usable) if _matches(exp, rec)] for exp in expectations]
    owner: dict[int, int] = {}  # finding index -> expectation index

    def assign(e: int, seen: set[int]) -> bool:
        for f in edges[e]:
            if f in seen:
                continue
            seen.add(f)
            if f not in owner or assign(owner[f], seen):
                owner[f] = e
                return True
        return False

    for e in range(len(expectations)):
        assign(e, set())
    return {e: f for f, e in owner.items()}


def score_case(expectations: list[dict], findings: list[dict], decoys: list[dict] | None = None) -> dict:
    usable = [f for f in findings if f.get("verdict") in USEFUL_VERDICTS]
    match = _max_matching(expectations, usable)
    used = set(match.values())

    caught = [exp["id"] for e, exp in enumerate(expectations) if e in match]
    missed = [exp["id"] for e, exp in enumerate(expectations) if e not in match]
    confirmed = [expectations[e]["id"] for e, f in match.items() if usable[f].get("verdict") == "confirmed"]

    decoy_hits = []
    for decoy in decoys or []:
        for i, rec in enumerate(usable):
            if i not in used and _matches(decoy, rec):
                used.add(i)
                decoy_hits.append(f"{decoy['id']}: {rec.get('fingerprint') or rec.get('title', '?')}")

    unmatched = [
        (usable[i].get("fingerprint") or usable[i].get("title", "?"))
        for i in range(len(usable)) if i not in used
    ]
    total = len(expectations)
    recall = len(caught) / total if total else 1.0
    return {
        "total": total,
        "caught": caught,
        "caught_confirmed": confirmed,
        "missed": missed,
        "recall": recall,
        "decoy_hits": decoy_hits,
        "unmatched_findings": unmatched,
    }


def report(result: dict, case: str) -> int:
    pct = round(result["recall"] * 100)
    print(f"case {case}: caught {len(result['caught'])}/{result['total']} planted defects "
          f"({pct}% recall; {len(result['caught_confirmed'])} confirmed)")
    if result["missed"]:
        print("  MISSED: " + ", ".join(result["missed"]))
    if result["decoy_hits"]:
        print("  DECOY HITS (false positives on correct code):")
        for hit in result["decoy_hits"]:
            print("    - " + hit)
    if result["unmatched_findings"]:
        print("  findings matching no planted defect (verify - extra or false positive):")
        for fp in result["unmatched_findings"]:
            print("    - " + str(fp))
    return 0 if not result["missed"] else 1


# --- selftest ------------------------------------------------------------

_EXP = [
    {"id": "a", "file": "core/server.lua", "keywords": ["price", "client"]},
    {"id": "b", "file": "html/app.js", "keywords": ["innerhtml", "xss"]},
]
_PERFECT = [
    {"verdict": "confirmed", "surface": "net_event", "title": "buy trusts client price",
     "description": "price from the client payload", "trace": [{"kind": "sink", "file": "core/server.lua", "line": 10}]},
    {"verdict": "confirmed", "surface": "xss", "title": "name into innerHTML",
     "description": "XSS via innerHTML", "trace": [{"kind": "sink", "file": "html/app.js", "line": 5}]},
]
_PARTIAL = [_PERFECT[0]]


def selftest() -> int:
    ok = True
    full = score_case(_EXP, _PERFECT)
    if full["recall"] != 1.0 or full["missed"]:
        ok = False
        print("selftest FAIL: perfect findings did not score 1.0:", full)
    part = score_case(_EXP, _PARTIAL)
    if part["recall"] != 0.5 or part["missed"] != ["b"]:
        ok = False
        print("selftest FAIL: partial findings mis-scored:", part)
    # a rejected record must not count
    rej = score_case(_EXP, [{**_PERFECT[0], "verdict": "rejected"}, _PERFECT[1]])
    if "a" in rej["caught"]:
        ok = False
        print("selftest FAIL: a rejected record was counted as a catch")
    # one broad finding must not satisfy two expectations
    broad = {"verdict": "confirmed", "title": "client price into innerHTML", "trace": [
        {"file": "core/server.lua"}, {"file": "html/app.js"}]}
    one = score_case(_EXP, [broad])
    if len(one["caught"]) != 1:
        ok = False
        print("selftest FAIL: one finding counted for several expectations:", one)
    # matching is maximal, not greedy: the broad finding must yield 'a' to the narrow one
    narrow_b = {**_PERFECT[1]}
    both = score_case(_EXP, [broad, narrow_b])
    if both["missed"]:
        ok = False
        print("selftest FAIL: greedy matching dropped a catch:", both)
    # needs_validation counts for recall but not as confirmed
    nv = score_case(_EXP, [{**_PERFECT[0], "verdict": "needs_validation"}, _PERFECT[1]])
    if nv["recall"] != 1.0 or nv["caught_confirmed"] != ["b"]:
        ok = False
        print("selftest FAIL: confirmed breakdown wrong:", nv)
    # a leftover finding on a decoy is reported as a decoy hit
    decoy = [{"id": "d", "file": "core/server.lua", "keywords": ["buybait"]}]
    fp = {"verdict": "confirmed", "title": "buyBait has no balance check", "trace": [{"file": "core/server.lua"}]}
    dec = score_case(_EXP, _PERFECT + [fp], decoy)
    if len(dec["decoy_hits"]) != 1 or dec["unmatched_findings"]:
        ok = False
        print("selftest FAIL: decoy hit not reported:", dec)
    print("eval scorer selftest passed." if ok else "eval scorer selftest FAILED.")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--expectations")
    parser.add_argument("--case")
    parser.add_argument("--findings")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return selftest()
    if not (args.expectations and args.case and args.findings):
        parser.error("--expectations, --case and --findings are required (or --selftest)")

    exp_all = json.loads(open(args.expectations, encoding="utf-8").read())
    cases = exp_all.get("cases", {})
    if args.case not in cases:
        print(f"unknown case '{args.case}'; known: {', '.join(sorted(cases))}", file=sys.stderr)
        return 2
    findings = json.loads(open(args.findings, encoding="utf-8").read())
    if not isinstance(findings, list):
        print("findings.json must be a JSON array", file=sys.stderr)
        return 2

    decoys = exp_all.get("decoys", {}).get(args.case, [])
    return report(score_case(cases[args.case], findings, decoys), args.case)


if __name__ == "__main__":
    sys.exit(main())
