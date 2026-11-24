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
title/description/surface mentions one of the expectation's keywords. The score
is recall (planted defects found / planted defects), plus a list of findings
that matched no expectation, so the reviewer can tell real extras from noise.

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


def score_case(expectations: list[dict], findings: list[dict]) -> dict:
    usable = [f for f in findings if f.get("verdict") in USEFUL_VERDICTS]
    matched_findings: set[int] = set()
    caught, missed = [], []

    for exp in expectations:
        keywords = [k.lower() for k in exp.get("keywords", [])]
        hit = None
        for i, rec in enumerate(usable):
            if not file_matches(exp["file"], finding_files(rec)):
                continue
            text = finding_text(rec)
            if any(kw in text for kw in keywords) or not keywords:
                hit = i
                break
        if hit is not None:
            matched_findings.add(hit)
            caught.append(exp["id"])
        else:
            missed.append(exp["id"])

    unmatched = [
        (usable[i].get("fingerprint") or usable[i].get("title", "?"))
        for i in range(len(usable)) if i not in matched_findings
    ]
    total = len(expectations)
    recall = len(caught) / total if total else 1.0
    return {
        "total": total,
        "caught": caught,
        "missed": missed,
        "recall": recall,
        "unmatched_findings": unmatched,
    }


def report(result: dict, case: str) -> int:
    pct = round(result["recall"] * 100)
    print(f"case {case}: caught {len(result['caught'])}/{result['total']} planted defects ({pct}% recall)")
    if result["missed"]:
        print("  MISSED: " + ", ".join(result["missed"]))
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

    return report(score_case(cases[args.case], findings), args.case)


if __name__ == "__main__":
    sys.exit(main())
