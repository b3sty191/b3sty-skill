# Changelog

## 2026-11-25 - VORP layer, fresher platform facts, evals you can trust

### What this update helps with

**VORP servers.** New `skills/redm/vorp.md`, checked line by line against VORPCORE source (vorp_core 3.4, vorp_inventory 4.5, vorp_lib 0.5). It has the exact argument order of every inventory export, since the callback sits in a different slot almost every time. It also covers traps no doc mentions:
- `addCurrency` validates nothing: a negative amount subtracts.
- `addItem` never checks capacity and can yield.
- `subItem` with metadata returns `true` even when the stack is short.
- Re-registering a usable item silently replaces the first.
- Context-menu whitelisting covers only the event name, so the arguments stay client-controlled.

**Facts that changed in 2025-2026**, each checked at source:
- `lua54 'yes'` is deprecated.
- OneSync is forced on (citizenfx/fivem `19fa3d5`).
- `xbl`/`live` identifiers are retired, and a player's `license` can change since the Account Security Update.
- ox_lib development is back at `overextended/ox_lib`, so the CommunityOx fork is archived. Use at least 3.32.1, which fixes the nearby-player crash.
- txAdmin v8 renamed events (`playerHealed`, `scheduledRestartSkipped`) and moved host settings to `TXHOST_*`.

Three claims from the source report did not hold up and were left out:
- that strings no longer coerce in arithmetic;
- that `json.decode` changed;
- that `sv_replaceExeToSwitchBuilds` is fully deprecated.

**Evals that measure something.**
- Fixtures no longer name their own bugs. The validator fails if one says `PLANTED`, and the README says to audit a copy outside the repo.
- The `fivem_shop` XSS case now really is cross-player (the last buyer's name is broadcast to everyone). It used to show only the viewer's own name, which an auditor rightly rejected as self-XSS.
- A finding can satisfy only one expectation (it used to inflate recall), catches report how many were `confirmed`, and decoys - correct code that looks risky - count false positives.
- New hint-free `redm_vorp_trader` case: 6 defects, 2 decoys.
- Review mode now treats performance as an invariant a full audit never skips.
- New `trigger-evals/` (`claude plugin eval`) checks that the skill loads for CFX work and not for Python, React, or Roblox Lua.

## 2026-11-25 - Lean rewrite: one skill, no commands to remember

### What this update helps with

**Easier to use.** The four slash commands are gone. Ask in plain words ("review this resource", "make me a shop script", "why is my server lagging", "give me ideas for...") and the skill picks the right workflow from `modes/` by itself. The README is a third of its old size: install, examples, done.

**Less paid on every session.** In Claude Code, the plugin used to add ~778 tokens of skill and command descriptions to *every* session, FiveM or not. Now one description of 505 characters (was 989), and the four command descriptions are gone.

**Less paid per task.** Measured on this branch:

| What the agent loads | Before | After |
|---|---|---|
| `SKILL.md` | 14,710 B | 12,201 B |
| Review workflow | 9,020 B (`commands/b3sty-review.md`) | 7,538 B (`modes/review.md`) |
| All rule files (`skills/`) | 248,088 B | 221,907 B |
| Memory (`memory/`) | 43,407 B | 40,260 B |

**Same quality.** Every rule file was rewritten without dropping a rule, number, API name, caveat, or verified tag. An independent audit compared every old file against its new version; the 10 regressions it found (mostly code examples) were restored. Planted-bug evals were run twice per version on the same fixtures, with the `PLANTED` comments stripped so the auditor cannot read the answers:

| Run | fivem_shop | redm_stable | Total |
|---|---|---|---|
| Before, run 1 | 5/7 | 1/2 | 6/9 |
| Before, run 2 | 5/7 | 1/2 | 6/9 |
| After, run 1 | 5/7 | 1/2 | 6/9 |
| After, run 2 | 5/7 | 2/2 | 7/9 |

Both versions miss the same two: the NUI `innerHTML` sink is rejected as self-XSS (only the viewer's own name reaches it), and the `Wait(0)` loop is a performance issue, not a security finding.

### If you used the commands
`/b3sty-review`, `/b3sty-perf`, `/b3sty-new-resource`, and `/b3sty-ideate` are now `modes/review.md`, `modes/perf.md`, `modes/new-resource.md`, and `modes/ideate.md`. Ask for the task instead, or invoke the skill directly (`/b3sty-skill review ./my_resource`).

## 2026-11-25 - Verified FXServer know-how + per-task token diet ([#6](https://github.com/b3sty191/b3sty-skill/pull/6))

### What this update helps with

**Your agent spends fewer tokens per task.** No rule was removed. Here is what was reorganised:

| What the agent loads | Before | After |
|---|---|---|
| `SKILL.md` on every invocation | ~4.1k tok | ~3.4k tok |
| Security rules for a server event, callback, or DB write | ~13k tok (one 52.7 KB file) | ~4.4k tok (core file only) |
| A typical server-event task (SKILL.md + core security) | ~17.5k tok | ~8k tok (-54%) |
| Looking up one native | risk of reading a 2.3 MB / 5.0 MB file | `rg` the name or hash, read only that entry |

**It stops two pieces of wrong advice.**
- Restarting a framework or dependency does **not** restart the resources that depend on it. They stop and stay stopped (`ResourceDependencyLoader.cpp`). The skill used to say the opposite.
- `INSERT ... ON DUPLICATE KEY UPDATE` is now advised only where the resource owns row creation. It recreates rows deleted while the player is online.

**It catches bugs the skill used to miss.** All of these were verified in FXServer/FiveM source, an offline regression test, a kill -9 crash harness, or on a live server:
- **Item/money dupes and rollbacks in save code:** monotonic `save_seq` guard, both players of a trade saved in one transaction, catalogs reloaded build-aside then swapped, never deciding a save from a client-sent flag, gating reconnects while the last save is in flight.
- **Data lost at restart:** the txAdmin 5 s shutdown default vs a real ~11 s save, `stop`/`quit`/`kill` giving no save window, detecting an unclean stop with a KVP marker.
- **Server hitches:** one-frame full saves (~220 ms at 2048 players), KVP fsync per write, Lua->JS packing for oxmysql, generational GC pauses, multi-row `UPDATE ... JOIN` batching.
- **"Desync" that is really the engine:** OneSync send cadence and range tiers, the 128 (RedM 32) player-slot cap, the 424 m 2D culling radius, `weaponDamageEvent` field meanings, the `netGameEvent` and `http_*` rate limiters.
- **Confusing runtime failures:** `return nil, reason` across exports, empty `SCRIPT ERROR` from a failing export, `GetGameTimer()` not being per-tick, hash-call argument mangling (`0xDEADBEEF`), `__le` no longer derived from `__lt` on artifact 37850+.
- **Exposure:** `/perf` is public without basic auth, plain `set` convars are readable by every resource (`add_convar_permission`), limits for admin/AI tools that run console commands, 10 known ESX Legacy 1.15.2 holes.
- **Operations:** artifact upgrade/rollback by directory swap, systemd cgroup killing a server started from a oneshot unit, `onesync_logFile`, offline Lua tests and crash-consistency harnesses, and native C++ components (`skills/common/fxserver-components.md`).

### If you link to the old layout
These sections moved verbatim out of `skills/common/security-performance.md`. Their headings are unchanged, so update the path only:
- `give-value-hardening.md`: Give-Value Event Hardening, ACE Permissions And Admin Authority, Abuse Handling
- `client-input-validation.md`: Sync Safety, NUI Callback Hardening, Entity And Net ID Validation, Built-in Client Events, Position And Interaction Checks
- `server-hardening.md`: Config, Convars, And Secrets; Logging And Secrets; Server Hardening And Operations
- `performance.md`: Performance Rules, Cleanup, Anti-Overengineering
- `review-questions.md`: Review Questions

## 2026-11-24 - Memory from a production server ([#4](https://github.com/b3sty191/b3sty-skill/pull/4))

- Added the Net Event Guard Injection pattern (a per-event guard injected into every resource without editing handlers).
- Added two errors: per-frame animation tied to FPS, and framework net events never reaching a plain `AddEventHandler`.
