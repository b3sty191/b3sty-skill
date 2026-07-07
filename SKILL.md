---
name: b3sty-skill
description: b3sty rules for implementing, reviewing, debugging, refactoring, or optimizing RedM/FiveM Lua resources. Use for FXServer manifests, client/server Lua, natives/entities, native invocation from docs (hashes, InvokeNative, marshalling, RDR3 structs), events/callbacks/exports/NUI, server validation, throttles/cooldowns, state bags, config splitting, ox_lib, SQL/OxMySQL persistence, multi-resource integration, performance, cleanup, and learned memory updates.
---

# b3sty Skill

Use this skill when working on b3sty RedM/FiveM resources or related Lua code. The defaults below are the high-frequency rules applied on every task; open the reference files only when the task touches that area.

## Operating Workflow

1. Identify the target before editing: RedM, FiveM, or shared; client, server, NUI, database, or cross-resource; resource name; framework/dependency assumptions.
2. Inspect the local project first and follow its existing patterns unless they conflict with the rules below.
3. Load only the relevant reference files from this skill. For broad reviews, start with the changed surfaces, then open the matching files listed below.
4. Treat public server events, callbacks, commands, exports, NUI callbacks, and inter-resource calls as untrusted boundaries.
5. Verify native names, hashes, signatures, and game-specific behavior against the matching native reference before relying on uncertain native behavior.
6. Finish with concrete verification: resource start/load order, event names, server validation, cleanup paths, performance hot paths, and any manual repro steps.
7. Record recurring fixes or newly verified engine quirks in the right `memory/` namespace with date and game build.

## Task Routing

- Start with `skills/common/fxserver.md` when the manifest, load order, dependency list, UI files, or resource layout changes.
- Start with `skills/common/security-performance.md` for any server event, callback, command, export, NUI callback, state sync, database mutation, reward, item, money, permission, cooldown, or hot loop.
- Add `skills/common/database.md` when SQL, OxMySQL/mysql-async, schema, transactions, migrations, dirty saves, or persisted state is involved.
- Add `skills/common/native-rules.md` and the matching game rules when code calls natives, handles entities, weapons, ammo, vehicles, horses, peds, blips, props, or routing buckets.
- Add `skills/common/native-usage.md` when translating a native reference entry into a Lua call, invoking by hash with `Citizen.InvokeNative`, handling out-pointer params, packing RDR3 struct arguments, or gating natives by game build.
- Search the matching native reference only when verifying a specific native name, hash, namespace, signature, parameter behavior, or game difference.
- Add `skills/common/debugging.md` and the relevant `memory/` files when the task is diagnosis, reproduction, traces, NUI errors, database failures, native bugs, or performance investigation.
- Add `skills/common/ox-lib.md` only when the resource already uses ox_lib or the user explicitly accepts adding it.
- Add `skills/common/multi-resource.md` when the feature crosses resources through exports, events, callbacks, dependencies, shared scripts, convars, state bags, or framework integration.
- Add `skills/fivem/rules.md` or `skills/redm/rules.md` whenever the resource is game-specific or shared behavior might differ.
- Run `scripts/validate_b3sty_skill.py` after editing this skill package and before publishing it.

## Review Priorities

- Check server authority before style.
- Check public input boundaries before internal helpers.
- Check cleanup and lifecycle before adding caches, timers, callbacks, entities, zones, or state.
- Check RedM/FiveM portability before moving code into shared files.
- Keep fixes local and direct unless repeated use justifies a helper or reference update.

## Core Defaults

Apply these on every b3sty Lua task unless the task says otherwise.

### Style

- Direct, readable code over heavy abstraction. No frameworks, dispatchers, or class systems for small resources.
- 4 spaces indentation. Spaces after commas in calls, params, and tables.
- Hardcoded inline values (model names, positions, event names) are fine when clearer beside the logic.
- Do not create helper functions or throwaway locals for one-off values; inline hardcoded values when they keep the flow easier to read.
- Name locals only when reused, expensive, validated, or clearer than the inline expression.
- Controller pattern: one local table with `function Controller:Method() ... end`.

### Events

- Every custom event uses `resource_name:server:action` or `resource_name:client:action`.
- The server is the source of truth for money, items, jobs, permissions, ownership, rewards, cooldowns, and saved state.
- Treat public server events, callbacks, commands, and exports as untrusted input; validate payloads and permissions server-side.

### CfxLua

- In RedM/FiveM code, supported compound operators (`+=`, `-=`, `*=`, `/=`, `<<=`, `>>=`, `&=`, `|=`, `^=`) are fine when clearer. Do **not** use `++`/`--`.
- These operators are CfxLua-only - never use them in standard Lua or standalone Lua tooling.

### Natives

- Docs name `GET_ENTITY_HEALTH` -> Lua global `GetEntityHealth`; leading-underscore names drop the underscore; hash-only natives use `Citizen.InvokeNative(hash, ...)` with a `--[[NAME]]` comment.
- `Citizen.InvokeNative` BOOL results are `1`/`0`, and `0` is truthy in Lua - compare `== 1`, never use the raw result in an `if`.
- Float params in hash calls must be float-subtype numbers - write `1.0`, coerce computed values with `+ 0.0`.
- Prefer hash constants via backtick literals or `joaat`; compare hashes to hashes, never to hex strings.
- Full mechanics (out params, marshalling, RDR3 structs, builds, confidence): `skills/common/native-usage.md`.

### Config

- Small/shared config in `config.lua`; large datasets split into `configs/*.lua`, each returning a table.
- Require a split config only in the script that uses it; no eager aggregators.

### Performance & Cleanup

- Render cosmetic/attached/preview props locally from server-owned state; use networked props only for shared gameplay entities.
- Cache hot lookups in locals; build reverse indexes (`Items["INDEX"][name]`) for repeated searches.
- No `Wait(0)` unless frame-level work is required; stage waits by distance/activeness.
- Clean up entities, blips, zones, timers, callbacks, throttles, and caches on player drop / resource stop. Guard entity cleanup with `DoesEntityExist`.

## Reference Files

Open lazily by task - do not preload all of them.

### Common

- `skills/common/style.md` - full style, formatting, and CfxLua rules.
- `skills/common/fxserver.md` - when editing `fxmanifest.lua` or resource layout.
- `skills/common/native-rules.md` - when calling natives, handling entities/ammo, or debugging native behavior.
- `skills/common/native-usage.md` - when turning a native reference entry into a Lua call: name conversion, `Citizen.InvokeNative`, result/pointer marshalling, RDR3 struct natives, build gates, confidence policy.
- `skills/common/resource-structure.md` - shared client/server/config/event/state structure.
- `skills/common/security-performance.md` - when writing `:server:` events, callbacks, sync, DB writes, or hot loops.
- `skills/common/database.md` - when writing SQL, OxMySQL/mysql-async persistence, migrations, transactions, or saved state.
- `skills/common/debugging.md` - when diagnosing resource failures, traces, client/server/NUI issues, DB issues, load order, or performance bugs.
- `skills/common/ox-lib.md` - when a resource already uses ox_lib or the task explicitly accepts adding ox_lib.
- `skills/common/multi-resource.md` - when resources communicate through exports, events, callbacks, dependencies, state bags, or shared libraries.

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
- `memory/fivem/native-bugs.md` - FiveM-only native issues and workarounds.
- `memory/redm/README.md` - RedM-specific memory namespace.
- `memory/redm/native-bugs.md` - RedM-only native issues and workarounds (e.g. `SetPedAmmoByType` reserve ammo).
