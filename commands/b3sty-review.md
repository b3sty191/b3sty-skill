---
description: Security-review or full audit of a RedM/FiveM Lua resource against the b3sty rules, with a deterministic entry-point coverage ledger, adversarial per-finding verification, and confirmed/needs_validation/rejected verdicts. Use when asked to review, audit, security-check, or pen-test a FiveM or RedM resource, a server event, an NUI bridge, or a PR touching CFX Lua, or before releasing or selling a resource. Covers server authority, give-item/give-money dupes, event and NUI trust boundaries, SQL injection, XSS, OneSync, lifecycle cleanup, framework usage, and performance.
argument-hint: [resource path, files, or PR]
---

# b3sty Resource Review

Target: $ARGUMENTS

Find defects that violate a real trust boundary in a RedM/FiveM resource, prove
each one against the source, and report it with the smallest server-side fix.
This is defensive, source-first review. A candidate with no concrete affected
principal, resource, or security outcome is not a confirmed finding.

Paths under `skills/`, `memory/`, `references/`, and `scripts/` below are
relative to the b3sty-skill root (the folder holding the main `SKILL.md`; with
the plugin install, the plugin root).

Do not edit the target's code during review. Propose fixes; apply them only when
asked.

## Modes

- **Guidance mode (default)** — a question, a focused look at a few files, or a
  PR diff. Work the relevant phases below and answer in chat. Do not build a
  ledger or write `findings.json` unless asked.
- **Full-audit mode** — "audit", "full/complete security review", "pen-test
  this resource", or a request for the report files. Run all five phases and
  write the deliverables. Pick a scratch output directory **outside the target's
  own resource folder** (so an audit file never ships inside the resource);
  state where it is.

If the request could be either, ask one question before building a ledger.

## Phase 1 — Scope and map

- Identify the game (`games` in `fxmanifest.lua`), the framework (ESX, QBCore,
  Qbox, VORP, RSG, or none), ox_lib use, NUI (`ui_page`), and database use.
- Note the server-authority model: where money, items, jobs, and saved state
  actually live (`skills/common/frameworks.md`).
- A scoped request (named files, one subsystem, a diff) audits only that subset;
  say so in the report and mark the rest out of scope, never "clean".

## Phase 2 — Build the coverage ledger (the coverage claim)

Generate the deterministic entry-point ledger instead of eyeballing a grep:

```bash
python3 <skill-dir>/scripts/b3sty_audit_ledger.py <target> -o <out>/ledger.json
```

It emits one unit per untrusted boundary — net events, built-in client events,
NUI callbacks, commands, exports, framework/ox_lib callbacks, HTTP handlers, SQL
calls, replicated state-bag handlers, and browser XSS sinks — each with
`file:line` and a `side` (server/client/either) that tells you how hostile the
input is. It over-reports; that is the point. In guidance mode you may run it or
inventory by hand, but every boundary you review must be a ledger unit or a
noted addition.

The ledger is the coverage claim. "I reviewed auth" is not coverage; a closed
unit with the paths you read is. A unit is closed only after you have read its
handler to the sink. If you find a boundary the scan missed (a dynamically named
event, an indirect dispatch), add a unit for it — never review it silently.

## Phase 3 — Hunt each unit to a verdict

Work units in priority order: unauthenticated/lowest-trust surfaces first, then
boundaries over the most valuable resources (money, items, cross-player data,
admin/console, release), then the rest. For each unit, open only the rule files
it needs:

| Surface found | Open |
|---|---|
| Any `:server:` event, callback, command, export | `skills/common/security-performance.md` (Required Event Pattern, Give-Value Event Hardening, Review Questions) |
| Money, items, rewards, shops | `skills/common/security-performance.md` -> Give-value event checklist |
| Framework calls (ESX/QBCore/Qbox/VORP/RSG) | `skills/common/frameworks.md` |
| NUI, `RegisterNUICallback`, XSS sinks | `skills/common/nui.md` |
| Networked entities, net IDs, buckets, built-in client events | `skills/common/networking.md` |
| SQL, oxmysql | `skills/common/database.md` |
| Threads, `source` across yields, exports, lifecycle | `skills/common/runtime.md` |
| Net event spam, `-1` broadcasts, payload size, state bags | `skills/common/network-performance.md` |
| Natives, hashes | `skills/common/native-usage.md`, then `references/natives/` |
| Game-specific code | `skills/fivem/rules.md` or `skills/redm/rules.md` |
| Cross-resource exports/events | `skills/common/multi-resource.md` |

For each unit, settle one invariant at a time:

1. **Authority** — does the server decide the price, amount, reward, target, and
   permission, or trust the client payload?
2. **Input** — type, range, integer, NaN, string length, table depth;
   `local source = source` captured before the first yield and re-checked after.
3. **Abuse** — throttle, in-flight lock, replay, distance/ownership, audit log.
4. **Lifecycle** — cleanup on `playerDropped`, character unload, and
   `onResourceStop`; NUI focus released; entities guarded with `DoesEntityExist`.
5. **Portability / performance** — only after the security invariants settle.

Check `memory/` for a known engine quirk before blaming the resource. Give each
unit a disposition: **covered** (read to the sink, invariant holds), **candidate**
(a boundary failure), or **blocked** (a fact you cannot settle from source).

## Phase 4 — Verify every candidate adversarially

This is the step that makes the review trustworthy, and it is not optional.

- Re-derive each candidate from scratch as if trying to **disprove** it. The
  cleanest way: hand each candidate to a fresh subagent (`Agent`/Task) that did
  not find it, with the one instruction to refute it from the source. A finding
  only one pass believes is not a finding.
- Confirm the whole path: a real lower-trust entrypoint, each propagation step,
  and the sink. Confirm native names, hashes, and signatures against
  `references/natives/`, not memory.
- Assign a verdict per `references/audit-findings-schema.md`:
  - **confirmed** — complete source trace and a bounded observed result. Carries
    severity (FiveM anchors in the schema), never above demonstrated impact.
  - **needs_validation** — source-grounded but blocked on a fact outside the
    repo (a live FXServer result, a `server.cfg` convar or ACE grant, a
    framework version). Name the exact blocker and a plan. No severity.
  - **rejected** — disproved by source or a visible control. Kept so the next
    run does not re-raise it.
- Severity is likelihood x impact, not checklist deviation. A defense-in-depth
  gap another layer already stops is a hardening note, not a finding. A guessed
  deployment behavior is `needs_validation`, never a confirmed bug.

Any runtime proof runs on a **private test server with dummy accounts** — never
a live or shared server, never real player data, and stop at the first boundary
result (the free item, the wrong balance). Most FiveM findings cannot be proven
from source alone because they need FXServer and the game; that is exactly what
`needs_validation` is for — do not inflate such a lead into confirmed, and do
not drop it either.

## Phase 5 — Report

In full-audit mode, write `<out>/findings.json` as the array in
`references/audit-findings-schema.md`, then:

```bash
python3 <skill-dir>/scripts/validate_audit_findings.py <out>/findings.json
```

Fix every error before writing prose; the JSON and the prose must agree. Then
write `<out>/REPORT.md` from the records and the ledger. In guidance mode, give
the same content in chat, grouped by verdict then severity.

The report has:

1. **Scope line** — game, framework, what was reviewed, what was out of scope or
   deferred, and whether runtime checks were possible. A scoped or source-only
   pass says plainly it is partial.
2. **Confirmed findings**, severity-first. For each:
   ```text
   [severity] file.lua:123 — one-line summary   (fingerprint)
   Boundary: who triggers it and what they gain.
   Abuse: the exact payload / steps.
   Fix: smallest server-side change, citing the rule file section.
   ```
3. **Needs-validation leads** — trace, exact blocker, and the safe test-server
   or owner-observed check. No severity.
4. **Hardening notes** — real but non-boundary improvements, kept separate from
   findings.
5. **Coverage summary from the ledger** — units covered / candidate / blocked /
   deferred, important exclusions, and plainly: no single pass is complete.

A clean resource may have zero confirmed findings — say so with the coverage and
validation limits, and do not invent low findings to fill the page. If the
review surfaced a new engine quirk or recurring mistake, propose a `memory/`
entry (date and game build included).
