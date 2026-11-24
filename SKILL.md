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

## Routing

Open a file only when its triggers match the task; never preload the set. Core Defaults below apply without opening anything.

| Open | Task touches |
|---|---|
| `skills/common/security-performance.md` | **start here** for any server event, callback, command, export, NUI callback, state sync, database mutation, reward, item, money, permission, cooldown, or hot loop: event trust boundary, payload validation, throttles, callback safety, atomic state changes, identifier trust, SQL injection, persistence |
| `skills/common/give-value-hardening.md` | shop/inventory/give-item/economy event hardening, rewards, crafting, trades, payouts, dupes, anti-cheat on value, the give-value checklist, admin/ACE gating, audit trails, abuse response |
| `skills/common/client-input-validation.md` | anti-cheat on client-reported data: state bags and custom sync, NUI callback payloads, client entity handles/net IDs, built-in client events (`weaponDamageEvent`, `startProjectileEvent`, `ptFxEvent`, `explosionEvent`), client coords and distance |
| `skills/common/server-hardening.md` | `server.cfg` hardening convars, secrets and convar exposure, operator/txAdmin/database access, `SetHttpHandler` endpoints, the resource sandbox, third-party resource vetting, security logging |
| `skills/common/performance.md` | CPU hot paths, caches and reverse indexes, staged waits, pool scans, cleanup on player drop / resource stop, anti-overengineering |
| `skills/common/review-questions.md` | reviewing or auditing code against these rules |
| `skills/common/fxserver.md` | `fxmanifest.lua`, resource layout, load order, dependency list, UI files |
| `skills/common/style.md` | full style, formatting, and CfxLua rules |
| `skills/common/resource-structure.md` | shared client/server/config/event/state structure |
| `skills/common/networking.md` | OneSync: networked entities, net IDs vs handles, entity ownership, routing buckets/instances, broadcasts, player scope, entity lifecycle events, built-in client events |
| `skills/common/network-performance.md` | bandwidth, event spam, `-1` broadcasts, latent events, payload size, repeated full fetches, snapshot-then-deltas, state bag cost, network overflow kicks |
| `skills/common/nui.md` | in-game browser UI (HTML/CSS/JS, React/Svelte/Vue), `SendNUIMessage`, `RegisterNUICallback`, `SetNuiFocus`, `ui_page`, JSON contracts, frontend hygiene, XSS |
| `skills/common/runtime.md` | threads/waits, the `source` variable, exports and stale references, identifiers, convars, resource lifecycle, yield hazards, game-build gating |
| `skills/common/database.md` | SQL, OxMySQL/mysql-async, schema, transactions, migrations, dirty saves, persisted state |
| `skills/common/native-rules.md` | natives, entities, weapons, ammo, vehicles, horses, peds, blips, props, routing buckets (add the matching game rules) |
| `skills/common/native-usage.md` | turning a native reference entry into a Lua call: name conversion, `Citizen.InvokeNative` by hash, out-pointer params, RDR3 struct args, build gates, confidence policy |
| `skills/common/debugging.md` | diagnosis, reproduction, traces, NUI errors, database failures, native bugs, load order, performance investigation (add the matching `memory/` files) |
| `skills/common/frameworks.md` | ESX, QBCore, Qbox, VORP, RSG: player lookup, money, items, jobs, lifecycle events, bridge |
| `skills/common/ox-lib.md` | the resource already uses ox_lib, or the user explicitly accepts adding it |
| `skills/common/ox-ecosystem.md` | ox_inventory (items, stashes, shops, `registerHook` dupe prevention) or ox_target (options re-validated server-side) |
| `skills/common/input.md` | player input: rebindable keybinds (`RegisterKeyMapping`), control checks and polling cost, disabling controls, RedM prompts |
| `skills/common/streaming.md` | `stream/` assets, `data_file` metas, runtime model/dict requests with a timeout |
| `skills/common/locale.md` | translatable text: ox_lib locale or a shared locale table, keys over hardcoded strings, placeholders, missing keys |
| `skills/common/operations.md` | live-server behavior: saving before a txAdmin scheduled restart, admin-action events, performance budgets |
| `skills/common/multi-resource.md` | exports, events, callbacks, dependencies, shared scripts, convars, state bags, or framework integration across resources |
| `skills/common/asset-protection.md` | protecting a resource the author sells or distributes: CFX Asset Escrow, `escrow_ignore`, server-side value, secret hygiene |
| `skills/common/fxserver-components.md` | native C++ server components added to an official artifact through `components.json`: portability, build pins, never replacing `citizen-server-impl` |
| `skills/fivem/rules.md`, `skills/redm/rules.md` | the resource is game-specific, or shared behavior might differ |
| `references/server.cfg.example` | setting up or reviewing `server.cfg` |
| `references/audit-findings-schema.md` | writing or validating `findings.json` for a `/b3sty-review` full audit |

Native references - `references/natives/fivem-gta5-natives.md` (GTA V/FiveM) and `references/natives/redm-rdr3-natives.md` (RDR3/RedM) - are multi-megabyte generated dumps. Never read one whole, and never page through it. Search the matching game's file for the native name or hash, then read only the matched entry's line range, e.g. `rg -n "GET_ENTITY_HEALTH" references/natives/fivem-gta5-natives.md` then read those lines plus ~40 after. Search only to verify a specific native name, hash, namespace, signature, parameter behavior, or game difference.

Run `scripts/validate_b3sty_skill.py` after editing this skill package and before publishing it.

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

## Commands

Slash commands installed with the Claude Code plugin:

- `commands/b3sty-review.md` - `/b3sty-review`: coverage-led, adversarially verified audit with confirmed/needs_validation/rejected verdicts (`scripts/b3sty_audit_ledger.py` seeds the entry-point ledger; `scripts/validate_audit_findings.py` checks the findings).
- `commands/b3sty-new-resource.md` - `/b3sty-new-resource`: scaffold a new resource that follows these rules.
- `commands/b3sty-perf.md` - `/b3sty-perf`: find and fix CPU and network performance problems with a measured/estimated report.
- `commands/b3sty-ideate.md` - `/b3sty-ideate`: parallel divergent ideation for open-ended design decisions; isolated generator branches under CFX frames, then a critic that rejects anything breaking these rules before deepening the best ideas.

## Memory

Read only when debugging or reusing a learned pattern. Memory files hold facts learned from real work (each entry carries a date and game build); they cross-link to `skills/` for the stable rules and do not duplicate rule text.

- `memory/common/native-bugs.md`, `memory/fivem/native-bugs.md`, `memory/redm/native-bugs.md` - known native issues and workarounds: shared, FiveM-only, RedM-only (e.g. `SetPedAmmoByType` reserve ammo).
- `memory/common/common-errors.md` - recurring shared Lua/resource errors and fixes.
- `memory/common/cfx-patterns.md` - reusable shared FXServer/CfxLua implementation patterns (controller, index map, cleanup, config split, persistence).
- `memory/common/security-performance.md` - learned shared security/performance patterns and quick-reference checklists.
- `memory/fivem/README.md`, `memory/redm/README.md` - the game-specific memory namespaces.
