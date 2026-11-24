# b3sty Resource Review

Use when: asked to review, audit, security-check, or pen-test a FiveM or RedM resource, a server event, an NUI bridge, or a PR touching CFX Lua, or before releasing or selling a resource.

Target: the target the user named (path, files, or PR).

Defensive, source-first review: find defects that violate a real trust boundary, prove each against the source, report the smallest server-side fix. No concrete affected principal, resource, or security outcome means no confirmed finding. Do not edit the target - propose fixes, apply only when asked. Paths are relative to the skill root (the main `SKILL.md`'s folder; the plugin root on a plugin install).

## Modes

- **Guidance (default)** - a question, a few files, a PR diff: relevant phases only, answered in chat; no ledger or `findings.json` unless asked.
- **Full audit** - "audit", "full/complete security review", "pen-test this resource", or a request for the report files: all five phases plus the deliverables, written to a scratch directory **outside the target's own resource folder** (an audit file must never ship inside the resource); state where it is.
- Ambiguous: ask one question before building a ledger.

## Phase 1 - Scope and map

- Game (`games` in `fxmanifest.lua`), framework (ESX, QBCore, Qbox, VORP, RSG, none), ox_lib, NUI (`ui_page`), database.
- Server-authority model: where money, items, jobs, and saved state actually live (`skills/common/frameworks.md`).
- A scoped request (named files, one subsystem, a diff) audits that subset only: say so, mark the rest out of scope, never "clean".

## Phase 2 - Build the coverage ledger (the coverage claim)

Deterministic entry-point ledger, not an eyeballed grep:

```bash
python3 <skill-dir>/scripts/b3sty_audit_ledger.py <target> -o <out>/ledger.json
```

One unit per untrusted boundary - net events, built-in client events, NUI callbacks, commands, exports, framework/ox_lib callbacks, HTTP handlers, SQL calls, replicated state-bag handlers, browser XSS sinks - each with `file:line` and a `side` (server/client/either) for input hostility. It over-reports by design. Guidance mode may inventory by hand; every boundary you review is still a ledger unit or a noted addition.

The ledger is the coverage claim: a closed unit with the paths you read, never "I reviewed auth". Close a unit only after reading its handler to the sink; a boundary the scan missed (dynamic event name, indirect dispatch) gets its own unit, never a silent review.

## Phase 3 - Hunt each unit to a verdict

Order: unauthenticated/lowest-trust surfaces first, then boundaries over the most valuable resources (money, items, cross-player data, admin/console, release), then the rest. Open only what a unit needs:

- Any `:server:` event, callback, command, export: `skills/common/security-performance.md` -> Required Event Pattern, `skills/common/give-value-hardening.md`, `skills/common/review-questions.md`
- Money, items, rewards, shops: `skills/common/give-value-hardening.md` -> Give-value event checklist
- Framework calls (ESX/QBCore/Qbox/VORP/RSG): `skills/common/frameworks.md`
- NUI, `RegisterNUICallback`, XSS sinks: `skills/common/nui.md`
- Networked entities, net IDs, buckets, built-in client events: `skills/common/networking.md`
- SQL, oxmysql: `skills/common/database.md`
- Threads, `source` across yields, exports, lifecycle: `skills/common/runtime.md`
- Net event spam, `-1` broadcasts, payload size, state bags: `skills/common/network-performance.md`
- Natives, hashes: `skills/common/native-usage.md`, then `references/natives/`
- Game-specific code: `skills/fivem/rules.md` or `skills/redm/rules.md`
- Cross-resource exports/events: `skills/common/multi-resource.md`

Settle one invariant at a time:

1. **Authority** - does the server decide price, amount, reward, target, and permission, or trust the client payload?
2. **Input** - type, range, integer, NaN, string length, table depth; `local source = source` captured before the first yield, re-checked after.
3. **Abuse** - throttle, in-flight lock, replay, distance/ownership, audit log.
4. **Lifecycle** - cleanup on `playerDropped`, character unload, `onResourceStop`; NUI focus released; entities guarded with `DoesEntityExist`.
5. **Portability / performance** - only once the security invariants settle.

Check `memory/` for a known engine quirk before blaming the resource. Disposition per unit: **covered** (read to the sink, invariant holds), **candidate** (a boundary failure), **blocked** (source cannot settle it).

## Phase 4 - Verify every candidate adversarially

Not optional; it is what makes the review trustworthy.

- Re-derive each candidate from scratch to **disprove** it; cleanest is a fresh subagent (`Agent`/Task) that did not find it, told only to refute it from source. A finding one pass believes is not a finding.
- Confirm the whole path: real lower-trust entrypoint, every propagation step, the sink. Confirm native names, hashes, and signatures against `references/natives/`, not memory.
- Verdict per `references/audit-findings-schema.md`:
  - **confirmed** - complete source trace, bounded observed result; the only verdict carrying severity (FiveM anchors in the schema), never above demonstrated impact.
  - **needs_validation** - source-grounded, blocked on a fact outside the repo (live FXServer result, `server.cfg` convar or ACE grant, framework version): name the exact blocker and a plan. No severity.
  - **rejected** - disproved by source or a visible control; kept so the next run does not re-raise it.
- Severity is likelihood x impact, not checklist deviation. A defense-in-depth gap another layer already stops is a hardening note; a guessed deployment behavior is `needs_validation`, never a confirmed bug.
- Runtime proof: **private test server, dummy accounts** - never live or shared, never real player data - stopping at the first boundary result (the free item, the wrong balance). Most FiveM findings need FXServer and the game, so source alone cannot prove them - that is what `needs_validation` is for; neither inflate such a lead into confirmed nor drop it.

## Phase 5 - Report

Full audit: write `<out>/findings.json` as the array in `references/audit-findings-schema.md`, then:

```bash
python3 <skill-dir>/scripts/validate_audit_findings.py <out>/findings.json
```

Fix every error before prose; JSON and prose must agree. Then write `<out>/REPORT.md` from the records and the ledger. Guidance mode gives the same content in chat, grouped by verdict then severity. Either way:

```text
Scope: game, framework, what was reviewed, what was out of scope or deferred, whether
    runtime checks were possible; a scoped or source-only pass is partial - say so.
Confirmed findings, severity-first:
    [severity] file.lua:123 — one-line summary   (fingerprint)
    Boundary: who triggers it and what they gain.
    Abuse: the exact payload / steps.
    Fix: smallest server-side change, citing the rule file section.
Needs-validation leads: trace, exact blocker, safe test-server or owner-observed check.
    No severity.
Hardening notes: real but non-boundary improvements, kept out of the findings.
Coverage from the ledger: units covered / candidate / blocked / deferred, important
    exclusions, and plainly: no single pass is complete.
```

Zero confirmed findings is a valid result - say so with the coverage and validation limits; never invent lows to fill the page. A new engine quirk or recurring mistake earns a proposed `memory/` entry (date and game build).
