# b3sty-skill evals

Small RedM/FiveM resources with documented, intentionally planted
vulnerabilities, plus a scorer. They measure the skill's own auditor: review a
case in review mode (`modes/review.md`) and score how many planted defects it catches.
This is the skill grading itself, not a review of real code.

The fixtures are deliberately insecure teaching samples. Do not copy them into a
real resource. They carry no comments that name their bugs - `EXPECTATIONS.json`
is the answer key, and the validator fails if a fixture says "PLANTED".

## Layout

- `cases/<name>/` - a buildable resource with planted defects and no hints.
- `EXPECTATIONS.json` - the answer key: planted defects per case (file, category,
  minimum severity, match keywords) and `decoys` - correct code that looks risky.
- `score.py` - scores a produced `findings.json` against `EXPECTATIONS.json`.

## Cases

- `fivem_shop` (FiveM, ESX-ish, NUI + oxmysql) - client-trusted price, SQL
  injection, `source` used after a yield, an admin command with no ACE, a `-1`
  broadcast, NUI `innerHTML` XSS, and a constant `Wait(0)` loop.
- `redm_stable` (RedM) - a server-side `GetEntityHealth` decision that is
  unreliable on RedM, and `DeleteEntity` from an unvalidated client net id.
- `redm_vorp_trader` (RedM, VORP) - a bounty paid from a client amount, a
  purchase with no balance check, a pelt sale that trusts a metadata `subItem`,
  a context-menu handler paying a client price, a client-chosen cart spawn, and
  a `getItemCount` call with the callback in the wrong slot. Two decoys (a
  fully guarded purchase, a distance-staged marker loop) measure false positives.

## Running one

1. Copy the case out of this repo first, so the auditor cannot read the answer
   key or this README, then audit the copy in full-audit mode:
   ```bash
   cp -r evals/cases/fivem_shop /tmp/eval-run/fivem_shop
   ```
   ```text
   Review /tmp/eval-run/fivem_shop in full-audit mode (findings.json in /tmp/eval-run)
   ```
2. Score the result:
   ```bash
   python3 evals/score.py --expectations evals/EXPECTATIONS.json \
       --case fivem_shop --findings <out>/findings.json
   ```

The score is recall (planted defects found / planted defects), with how many
catches were `confirmed`. One finding counts for at most one defect. Findings on
a decoy are reported as decoy hits - false positives on correct code. Other
unmatched findings are listed so you can tell a real extra find from noise. A
good run finds every planted defect, hits no decoy, and adds few extras.

`python3 evals/score.py --selftest` checks the scorer itself (run in CI).

## Using the evals to improve the skill

When a run misses a planted defect, the gap is usually a rule the skill states
weakly or a surface the ledger misses - fix the rule or the ledger generator,
not the expectation. Only change `EXPECTATIONS.json` when the planted defect
itself changes.
