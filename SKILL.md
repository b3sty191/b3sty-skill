---
name: b3sty-skill
description: b3sty rules for RedM/FiveM Lua development. Use when working on b3sty resources, FXServer manifests, Lua scripts, native/entity/event code, server validation, throttles, callbacks, state bags, config splitting, performance optimization, or RedM/FiveM debugging.
---

# b3sty Skill

Use this skill when working on b3sty RedM/FiveM resources or related Lua code. The defaults below are the high-frequency rules applied on every task; open the reference files only when the task touches that area.

## Core Defaults

Apply these on every b3sty Lua task unless the task says otherwise.

### Style

- Direct, readable code over heavy abstraction. No frameworks, dispatchers, or class systems for small resources.
- 4 spaces indentation. Spaces after commas in calls, params, and tables.
- Hardcoded inline values (model names, positions, event names) are fine when clearer beside the logic.
- Controller pattern: one local table with `function Controller:Method() ... end`.

### Events

- Every custom event uses `resource_name:server:action` or `resource_name:client:action`.
- The server is the source of truth for money, items, jobs, permissions, ownership, rewards, cooldowns, and saved state.

### CfxLua

- In RedM/FiveM code, supported compound operators (`+=`, `-=`, `*=`, `/=`, `<<=`, `>>=`, `&=`, `|=`, `^=`) are fine when clearer. Do **not** use `++`/`--`.
- These operators are CfxLua-only - never use them in standard Lua or standalone Lua tooling.

### Config

- Small/shared config in `config.lua`; large datasets split into `configs/*.lua`, each returning a table.
- Require a split config only in the script that uses it; no eager aggregators.

### Performance & Cleanup

- Cache hot lookups in locals; build reverse indexes (`Items["INDEX"][name]`) for repeated searches.
- No `Wait(0)` unless frame-level work is required; stage waits by distance/activeness.
- Clean up entities, blips, zones, timers, callbacks, throttles, and caches on player drop / resource stop. Guard entity cleanup with `DoesEntityExist`.

## Reference Files

Open lazily by task - do not preload all of them.

### Common

- `skills/common/style.md` - full style, formatting, and CfxLua rules.
- `skills/common/fxserver.md` - when editing `fxmanifest.lua` or resource layout.
- `skills/common/native-rules.md` - when calling natives, handling entities/ammo, or debugging native behavior.
- `skills/common/resource-structure.md` - shared client/server/config/event/state structure.
- `skills/common/security-performance.md` - when writing `:server:` events, callbacks, sync, DB writes, or hot loops.

### Game-Specific

- `skills/fivem/rules.md` - FiveM-only defaults, manifests, GTA V entities, and compatibility checks.
- `skills/redm/rules.md` - RedM-only defaults, manifests, RDR3 entities, and compatibility checks.

### Native References

These are large generated lookup files. Open only the matching file when verifying a native name, hash, signature, namespace, parameter behavior, or game-specific native difference.

- `references/natives/fivem-gta5-natives.md` - GTA V / FiveM native reference.
- `references/natives/redm-rdr3-natives.md` - RDR3 / RedM native reference.

## Memory

Read only when debugging or reusing a learned pattern. Memory files hold facts learned from real work (each entry carries a date and game build). They cross-link to `skills/` for the stable rules and do not duplicate rule text.

### Common

- `memory/common/native-bugs.md` - known shared native issues and workarounds.
- `memory/common/common-errors.md` - recurring shared Lua/resource errors and fixes.
- `memory/common/cfx-patterns.md` - reusable shared FXServer/CfxLua implementation patterns (controller, index map, cleanup, config split, persistence).
- `memory/common/security-performance.md` - learned shared security/performance patterns and quick-reference checklists.

### Game-Specific

- `memory/fivem/README.md` - FiveM-specific memory namespace.
- `memory/redm/README.md` - RedM-specific memory namespace.
- `memory/redm/native-bugs.md` - RedM-only native issues and workarounds (e.g. `SetPedAmmoByType` reserve ammo).
