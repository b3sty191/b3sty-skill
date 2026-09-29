---
name: b3sty-skill
description: b3sty rules for implementing, reviewing, debugging, refactoring, or optimizing RedM/FiveM Lua resources. Use for FXServer manifests, client/server Lua, natives/entities, native invocation (hashes, InvokeNative, marshalling, RDR3 structs), events/callbacks/exports, NUI bridge (SendNUIMessage, RegisterNUICallback, SetNuiFocus) and NUI XSS, OneSync networking (net IDs, ownership, routing buckets, broadcasts), built-in client events (weaponDamageEvent, explosionEvent), anti-cheat/event-security hardening (give-item/money dupes, ACE permissions, SQL injection, secrets/convars, identifier trust, payload bounds, audit trails), SetHttpHandler endpoints, server.cfg hardening and third-party resource vetting, throttles/cooldowns, state bags, CFX runtime gotchas (threads, source, exports, identifiers, game builds), config splitting, ox_lib, SQL/OxMySQL persistence, ESX/QBCore/Qbox/VORP/RSG framework bridges, multi-resource integration, performance, cleanup, and learned memory updates.
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
- Add `skills/common/security-performance.md` -> Event Trust Boundary, Give-Value Event Hardening, ACE Permissions, Built-in Client Events, Config/Convars/Secrets, Identifier Trust, and Server Hardening And Operations for shop/inventory/give-item/economy event hardening, anti-cheat, admin/ACE gating, secrets, SQL injection, the give-value checklist, SetHttpHandler endpoints, hardening convars, and third-party resource vetting.
- Add `skills/common/networking.md` when the feature creates networked entities, relies on entity ownership, uses routing buckets/instances, broadcasts to clients, reacts to player scope, or handles built-in client events (`weaponDamageEvent`, `startProjectileEvent`, `ptFxEvent`, and the rest).
- Add `skills/common/nui.md` when the resource has an in-game browser UI (HTML/CSS/JS, React/Svelte/Vue), `SendNUIMessage`, `RegisterNUICallback`, `SetNuiFocus`, or a `ui_page` in the manifest.
- Add `skills/common/runtime.md` for threads/waits, the `source` variable, exports and stale references, identifiers, convars, resource lifecycle, yield hazards, or game-build gating.
- Add `skills/common/network-performance.md` for bandwidth, event spam, `-1` broadcasts, latent events, payload size, repeated full fetches, state bag cost, or network overflow kicks.
- Add `skills/common/database.md` when SQL, OxMySQL/mysql-async, schema, transactions, migrations, dirty saves, or persisted state is involved.
- Add `skills/common/native-rules.md` and the matching game rules when code calls natives, handles entities, weapons, ammo, vehicles, horses, peds, blips, props, or routing buckets.
- Add `skills/common/native-usage.md` when translating a native reference entry into a Lua call, invoking by hash with `Citizen.InvokeNative`, handling out-pointer params, packing RDR3 struct arguments, or gating natives by game build.
- Search the matching native reference only when verifying a specific native name, hash, namespace, signature, parameter behavior, or game difference.
- Add `skills/common/debugging.md` and the relevant `memory/` files when the task is diagnosis, reproduction, traces, NUI errors, database failures, native bugs, or performance investigation.
- Add `skills/common/frameworks.md` when the resource uses ESX, QBCore, Qbox, VORP, or RSG (player lookup, money, items, jobs, lifecycle events, bridge).
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
- Capture `local source = source` at the top of every server handler before any yield; re-validate it after. Full mechanics in `skills/common/runtime.md`.
- Built-in client events (`weaponDamageEvent`, `startProjectileEvent`, `ptFxEvent`, and the rest) are client-callable; validate them like any `:server:` event. Full list in `skills/common/networking.md`.

### CfxLua

- In RedM/FiveM code, supported compound operators (`+=`, `-=`, `*=`, `/=`, `<<=`, `>>=`, `&=`, `|=`, `^=`) are fine when clearer. `^=` is bitwise XOR (`x = x ~ y`), not power. Do **not** use `++`/`--`.
- These operators are CfxLua-only - never use them in standard Lua or standalone Lua tooling.

### Natives

- Docs name `GET_ENTITY_HEALTH` -> Lua global `GetEntityHealth`; leading-underscore names drop the underscore; hash-only natives use `Citizen.InvokeNative(hash, ...)` with a `--[[NAME]]` comment.
- BOOL results from named natives and bare `Citizen.InvokeNative` are `1`/`false`, never `true` - test with `if`/`not`, never `== true`. Append `Citizen.ResultAsInteger()` to int-returning hash calls so a real `0` is not `false`; under it a BOOL is `1`/`0` and `0` is truthy, so compare `~= 0`.
- Float params must be float-subtype numbers in named and hash calls alike (`SetEntityHeading(ped, 90)` is broken) - write `1.0`, coerce computed values with `+ 0.0`.
- Prefer hash constants via backtick literals or `joaat`; compare hashes to hashes, never to hex strings.
- Full mechanics (out params, marshalling, RDR3 structs, builds, confidence): `skills/common/native-usage.md`.

### Config

- Small/shared config in `config.lua`; large datasets split into `configs/*.lua`, each returning a table.
- Load a split config only in the script that uses it; no eager aggregators. Stock CfxLua `require` cannot load resource files - use ox_lib's `require` when the resource already loads ox_lib, otherwise the cached loader in `skills/common/style.md` -> Lua Style (client reads need `files`).

### NUI

- NUI is client-local UX, never authority. Treat `RegisterNUICallback` payloads as untrusted and forward valuable actions through validated `:server:` events.
- Render any string another player can influence (names, chat, labels) as text - never through `innerHTML`/`{@html}`/`v-html`. XSS in CEF can drive every NUI callback as the victim.
- Clear NUI focus (`SetNuiFocus(false, false)`) on UI close, player drop, and resource stop; call each callback's `cb` exactly once.
- Full bridge mechanics (manifest, `SendNUIMessage`, fetch helper, focus, contracts): `skills/common/nui.md`.

### Networking

- Validate client-provided entity handles and net IDs (existence, type, model, owner, routing bucket, distance) before trusting them.
- Avoid `TriggerClientEvent(name, -1)` broadcasts; scope to one player or a small recipient set, and prefer state bags for replicated visible state.
- Full OneSync mechanics (ownership, routing buckets, scope, built-in client events): `skills/common/networking.md`.

### Performance & Cleanup

- Render cosmetic/attached/preview props locally from server-owned state; use networked props only for shared gameplay entities.
- Cache hot lookups in locals; build reverse indexes (`Items["INDEX"][name]`) for repeated searches.
- No `Wait(0)` unless frame-level work is required; stage waits by distance/activeness.
- Avoid load-time caching of export results that can go stale when the provider resource restarts. Full mechanics in `skills/common/runtime.md`.
- Clean up entities, blips, zones, timers, callbacks, throttles, and caches on player drop / resource stop. Guard entity cleanup with `DoesEntityExist`.

## Reference Files

Open lazily by task - do not preload all of them.

### Common

- `skills/common/style.md` - full style, formatting, and CfxLua rules.
- `skills/common/fxserver.md` - when editing `fxmanifest.lua` or resource layout.
- `skills/common/native-rules.md` - when calling natives, handling entities/ammo, or debugging native behavior.
- `skills/common/native-usage.md` - when turning a native reference entry into a Lua call: name conversion, `Citizen.InvokeNative`, result/pointer marshalling, RDR3 struct natives, build gates, confidence policy.
- `skills/common/resource-structure.md` - shared client/server/config/event/state structure.
- `skills/common/networking.md` - OneSync, net IDs vs handles, entity ownership, routing buckets, scoped vs broadcast messages, player scope, entity lifecycle events, and built-in client events (`weaponDamageEvent` and friends).
- `skills/common/nui.md` - in-game browser UI (NUI): Lua<->browser bridge, `SendNUIMessage`, `RegisterNUICallback`, focus, JSON contracts, validation, frontend hygiene, performance, and security.
- `skills/common/runtime.md` - threads/waits, the `source` variable, exports and stale references, identifiers, convars, resource lifecycle, yield hazards, and game builds.
- `skills/common/network-performance.md` - net event cost model, FXServer rate limits and overflow kicks, latent events, payload shape, snapshot-then-deltas caching, audience, and state bag cost.
- `skills/common/security-performance.md` - when writing `:server:` events, callbacks, sync, DB writes, or hot loops.
- `skills/common/database.md` - when writing SQL, OxMySQL/mysql-async persistence, migrations, transactions, or saved state.
- `skills/common/debugging.md` - when diagnosing resource failures, traces, client/server/NUI issues, DB issues, load order, or performance bugs.
- `skills/common/frameworks.md` - when a resource integrates with ESX, QBCore, Qbox, VORP, or RSG: player lookup, money/item/job calls, lifecycle events, and the bridge pattern.
- `skills/common/ox-lib.md` - when a resource already uses ox_lib or the task explicitly accepts adding ox_lib.
- `skills/common/multi-resource.md` - when resources communicate through exports, events, callbacks, dependencies, state bags, or shared libraries.

### Game-Specific

- `skills/fivem/rules.md` - FiveM-only defaults, manifests, GTA V entities, and compatibility checks.
- `skills/redm/rules.md` - RedM-only defaults, manifests, RDR3 entities, and compatibility checks.

### Native References

These are large generated lookup files. Open only the matching file when verifying a native name, hash, signature, namespace, parameter behavior, or game-specific native difference.

- `references/natives/fivem-gta5-natives.md` - GTA V / FiveM native reference.
- `references/natives/redm-rdr3-natives.md` - RDR3 / RedM native reference.
- `references/server.cfg.example` - copyable server hardening baseline (open when setting up or reviewing `server.cfg`).

## Commands

Slash commands installed with the Claude Code plugin:

- `commands/b3sty-review.md` - `/b3sty-review`: review a resource and report verified findings by severity.
- `commands/b3sty-new-resource.md` - `/b3sty-new-resource`: scaffold a new resource that follows these rules.
- `commands/b3sty-perf.md` - `/b3sty-perf`: find and fix CPU and network performance problems with a measured/estimated report.

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
