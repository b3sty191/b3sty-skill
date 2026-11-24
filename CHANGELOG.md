# Changelog

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
