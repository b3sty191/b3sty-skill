# Audit findings schema

`/b3sty-review` in full-audit mode writes `findings.json`: a top-level JSON
array of records, each with one of three verdicts. `scripts/validate_audit_findings.py`
is the machine check; this file is the human contract. The rules exist so prose
and JSON can never disagree and so a lead can never quietly carry a severity it
did not earn.

## Verdicts

- **`confirmed`** - a real boundary failure with a bounded, observed result.
  The only verdict that carries `severity`, and severity may never exceed the
  demonstrated impact.
- **`needs_validation`** - a source-grounded lead blocked on a fact the review
  could not settle from the repo alone (a live FXServer result, a `server.cfg`
  convar or ACE grant, a framework/resource version). Names the exact blocker
  and a plan. No severity - it is not a low-confidence confirmed bug.
- **`rejected`** - a candidate disproved during review, kept so the next run
  does not re-report it without new evidence.

## Common fields (every record)

| Field | Type | Notes |
|---|---|---|
| `fingerprint` | string | Stable per root cause across runs and verdicts. Matches `^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$`. No line, wave, agent, or severity in it. |
| `verdict` | enum | `confirmed` \| `needs_validation` \| `rejected`. |
| `surface` | enum | `net_event`, `builtin_event`, `nui_callback`, `command`, `callback`, `export`, `http_handler`, `sql`, `xss`, `state_bag`, `other`. |
| `title` | string | One line. |
| `description` | string | What is wrong, in plain words. |
| `trace` | array | Ordered steps `{kind, file, line, note?}`. `kind` is `entrypoint`/`propagation`/`sink`. A multi-step trace starts at `entrypoint` and ends at `sink`; a one-step trace uses `entrypoint` or `sink`. `file` is repo-relative. |
| `evidence` | string | The source fact that proves the trace. |

## `confirmed` adds

`root_cause`, `intended_behavior`, `conditions` (non-empty array), `abuse`
(the concrete exploit: who triggers it, with what payload, what they gain),
`remediation` (smallest server-side fix), `severity`, `confidence`
(`high`/`medium`/`low`). Must not carry `claimed_root_cause`, `blockers`,
`validation_plan`, or `reason`.

## `needs_validation` adds

`claimed_root_cause`, `blockers` (non-empty array of the exact unresolved
facts), `validation_plan` (object with a non-empty `local` and/or
`live_test_server` step). Must not carry `severity`, `confidence`,
`remediation`, `abuse`, `reason`, or a confirmed `root_cause`.

## `rejected` adds

`claimed_root_cause` and `reason` (why source or a visible control disproves
it). Must not carry a severity, fix, blocker, plan, or confirmed root cause.

## FiveM/RedM severity anchors

Severity is likelihood x impact, never deviation from a checklist. Overall
severity cannot exceed the impact actually demonstrated.

- **critical** - any client gets unbounded money/items, runs arbitrary SQL,
  executes code on the server, or runs admin/console actions with no real gate.
- **high** - a client fully defeats one control with real stakes: job/gang or
  ownership bypass on a valuable action, cross-player inventory or money theft,
  stored NUI XSS that drives another player's callbacks, or an unauthenticated
  remote crash of the server.
- **medium** - a real boundary violation with a narrow blast radius or uncommon
  preconditions (one player grieving one entity, a leak confined to non-secret
  state).
- **low** - disclosure of non-secret internals, or an effect needing sustained
  effort for minimal gain.
- **informational** - a confirmed but minimal observation, useful mainly as a
  prerequisite inside a larger finding.

The high/medium line: does the demonstrated result fully defeat a control for
an action with real consequences, or only weaken it? If you cannot state the
concrete gain to the attacker, the severity is lower than it feels.

## What stays out of `confirmed`

- A missing best practice with no reachable boundary violation is a hardening
  note, not a finding.
- A defense-in-depth gap where another layer already stops the attack is a
  hardening note.
- A guessed `server.cfg`, proxy, framework-version, or deployment behavior is
  `needs_validation` with the exact missing fact, never a confirmed bug.
- A client-side-only effect on the attacker's own game is not a cross-boundary
  finding; the server is the boundary.
