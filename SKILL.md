---
name: b3sty-skill
description: "b3sty rules for writing, refactoring, reviewing/auditing, debugging, optimizing, or designing FiveM/RedM Lua resources: fxmanifest, natives/InvokeNative, events/callbacks/exports, NUI (XSS), OneSync (net IDs, ownership, routing buckets, state bags), built-in client events, ESX/QBCore/Qbox/VORP/RSG/ox, oxmysql/SQL injection, ACE, secrets/convars, SetHttpHandler, txAdmin/server.cfg, throttles, dupes/anti-cheat, runtime gotchas (source, threads, game builds), cleanup. Use for any FXServer resource task."
---

# b3sty Skill

Rules and working memory for RedM/FiveM Lua resources. The user just asks in plain words; there are no commands.
Core Defaults apply to every task. Open a mode or routed file only when its triggers match - never preload.

## Modes

| Request | Read |
|---|---|
| review, audit, security check, pen-test, PR review, before release or sale | `modes/review.md` |
| new resource, create/scaffold/bootstrap, "make me a ... script" | `modes/new-resource.md` |
| lag, stutter, hitching, resmon, profiling, network overflow kicks, optimize | `modes/perf.md` |
| ideas, brainstorm, feature design, "how should I build this" | `modes/ideate.md` |

Ordinary coding tasks (write, fix, refactor, explain) need no mode.

## Workflow

1. Identify the target: RedM/FiveM/shared; client/server/NUI/database/cross-resource; resource name; framework and dependency assumptions.
2. Inspect the local project first; follow its patterns unless they conflict with these rules.
3. Load only the matching files below; for a broad review start at the changed surfaces, then open their files.
4. Public server events, callbacks, commands, exports, NUI callbacks, inter-resource calls: untrusted boundaries.
5. Verify uncertain native names, hashes, signatures, game differences against the matching native reference first.
6. Verify concretely: start/load order, event names, server validation, cleanup paths, hot paths, manual repro steps.
7. Record recurring fixes and newly verified engine quirks in the right `memory/` namespace, with date and game build.

## Routing

A bare name is a file in `skills/common/` (`nui` is `skills/common/nui.md`); other paths are written out.

| Open | Triggers |
|---|---|
| security-performance | **start here**: server events, callbacks, commands, exports, NUI callbacks, state sync, database mutations, rewards, items, money, permissions, cooldowns, hot loops; event trust boundary, payload validation, throttles, callback safety, atomic state changes, identifier trust, SQL injection, persistence |
| give-value-hardening | shops, inventory, give-item, economy, rewards, crafting, trades, payouts, dupes, anti-cheat on value, give-value checklist, admin/ACE gating, audit trails, abuse response |
| client-input-validation | anti-cheat on client-reported data: state bags, custom sync, NUI payloads, client entity handles/net IDs, coords/distance, built-in client events (`weaponDamageEvent`, `startProjectileEvent`, `ptFxEvent`, `explosionEvent`) |
| server-hardening | `server.cfg` convars, secrets/convar exposure, operator/txAdmin/database access, `SetHttpHandler` endpoints, resource sandbox, third-party resource vetting, security logging |
| performance | CPU hot paths, caches, reverse indexes, staged waits, pool scans, cleanup on player drop / resource stop, anti-overengineering |
| review-questions | reviewing or auditing code against these rules |
| fxserver | `fxmanifest.lua`, resource layout, load order, dependency list, UI files |
| style | full style, formatting, CfxLua rules |
| resource-structure | shared client/server/config/event/state structure |
| networking | OneSync: networked entities, net IDs vs handles, entity ownership, routing buckets/instances, broadcasts, player scope, entity lifecycle events, built-in client events |
| network-performance | bandwidth, event spam, `-1` broadcasts, latent events, payload size, repeated full fetches, snapshot-then-deltas, state bag cost, network overflow kicks |
| nui | in-game browser UI (HTML/CSS/JS, React/Svelte/Vue), `SendNUIMessage`, `RegisterNUICallback`, `SetNuiFocus`, `ui_page`, JSON contracts, frontend hygiene, XSS |
| runtime | threads/waits, the `source` variable, exports and stale references, identifiers, convars, resource lifecycle, yield hazards, game-build gating |
| database | SQL, OxMySQL/mysql-async, schema, transactions, migrations, dirty saves, persisted state |
| native-rules | natives, entities, weapons, ammo, vehicles, horses, peds, blips, props, routing buckets (plus the game rules) |
| native-usage | native reference entry -> Lua call: name conversion, `Citizen.InvokeNative` by hash, out-pointer params, RDR3 struct args, build gates, confidence policy |
| debugging | diagnosis, reproduction, traces, NUI errors, database failures, native bugs, load order, performance investigation (plus `memory/`) |
| frameworks | ESX, QBCore, Qbox, VORP, RSG: player lookup, money, items, jobs, lifecycle events, bridge |
| ox-lib | resource already uses ox_lib, or the user explicitly accepts adding it |
| ox-ecosystem | ox_inventory (items, stashes, shops, `registerHook` dupe prevention), ox_target (options re-validated server-side) |
| input | player input: rebindable keybinds (`RegisterKeyMapping`), control checks and polling cost, disabling controls, RedM prompts |
| streaming | `stream/` assets, `data_file` metas, runtime model/dict requests with a timeout |
| locale | translatable text: ox_lib locale or shared locale table, keys over hardcoded strings, placeholders, missing keys |
| operations | live server: saving before a txAdmin scheduled restart, admin-action events, performance budgets |
| multi-resource | cross-resource exports, events, callbacks, dependencies, shared scripts, convars, state bags, framework integration |
| asset-protection | selling or distributing a resource: CFX Asset Escrow, `escrow_ignore`, server-side value, secret hygiene |
| fxserver-components | C++ server components added to an official artifact via `components.json`: portability, build pins, never replace `citizen-server-impl` |
| `skills/fivem/rules.md`, `skills/redm/rules.md` | game-specific resource, or shared behavior might differ |
| `references/server.cfg.example` | setting up or reviewing `server.cfg` |
| `references/audit-findings-schema.md` | writing or validating `findings.json` for a review-mode full audit |

Natives: `references/natives/fivem-gta5-natives.md` (FiveM/GTA V) and `references/natives/redm-rdr3-natives.md` (RedM/RDR3) are multi-megabyte dumps: never read one whole, never page through it. Search the name or hash (`rg -n "GET_ENTITY_HEALTH" references/natives/fivem-gta5-natives.md`), then read only that entry plus ~40 lines. Search only to verify a specific native name, hash, namespace, signature, parameter behavior, or game difference.

After editing this skill package, run `scripts/validate_b3sty_skill.py`.

## Core Defaults

Every task, unless the task says otherwise.

**Style** - Readable code over heavy abstraction; no frameworks, dispatchers, class systems in small resources. 4-space indent, space after commas in calls, params, tables. Hardcoded inline values (models, positions, event names) are fine when clearer beside the logic; no helper functions or throwaway locals for one-off values. Name a local only when reused, expensive, validated, or clearer than the inline expression. Controller pattern: one local table with `function Controller:Method() ... end`.

**Events** - Name custom events `resource_name:server:action` / `resource_name:client:action`. Server is the source of truth for money, items, jobs, permissions, ownership, rewards, cooldowns, saved state. Public server events, callbacks, commands, exports are untrusted input: validate payloads and permissions server-side. Capture `local source = source` at the top of every server handler before any yield, re-validate after (`skills/common/runtime.md`). Built-in client events (`weaponDamageEvent`, `startProjectileEvent`, `ptFxEvent`, and the rest) are client-callable - validate like any `:server:` event; full list in `skills/common/networking.md`.

**CfxLua** - Supported compound operators (`+=`, `-=`, `*=`, `/=`, `<<=`, `>>=`, `&=`, `|=`, `^=`) are fine when clearer; `^=` is bitwise XOR (`x = x ~ y`), not power. Never `++`/`--`. CfxLua-only: never in standard Lua or standalone Lua tooling.

**Natives** - Docs name `GET_ENTITY_HEALTH` -> Lua global `GetEntityHealth`; leading-underscore names drop the underscore; hash-only natives use `Citizen.InvokeNative(hash, ...)` with a `--[[NAME]]` comment. BOOL from named natives and bare `Citizen.InvokeNative` is `1`/`false`, never `true` - test with `if`/`not`, never `== true`. Append `Citizen.ResultAsInteger()` to int-returning hash calls so a real `0` is not `false`; under it a BOOL is `1`/`0` and `0` is truthy, so compare `~= 0`. Float params must be float-subtype numbers in named and hash calls alike (`SetEntityHeading(ped, 90)` is broken) - write `1.0`, coerce computed values with `+ 0.0`. Prefer hash constants via backtick literals or `joaat`; compare hashes to hashes, never to hex strings. Out params, marshalling, RDR3 structs, builds, confidence: `skills/common/native-usage.md`.

**Config** - Small/shared config in `config.lua`; large datasets split into `configs/*.lua`, each returning a table. Load a split config only in the script that uses it; no eager aggregators. Stock CfxLua `require` cannot load resource files - use ox_lib's `require` when the resource already loads ox_lib, otherwise the cached loader in `skills/common/style.md` -> Lua Style (client reads need `files`).

**NUI** - Client-local UX, never authority: `RegisterNUICallback` payloads are untrusted, so forward valuable actions through validated `:server:` events. Render any string another player can influence (names, chat, labels) as text, never through `innerHTML`/`{@html}`/`v-html` - XSS in CEF can drive every NUI callback as the victim. Clear NUI focus (`SetNuiFocus(false, false)`) on UI close, player drop, resource stop; call each callback's `cb` exactly once. Bridge mechanics (manifest, fetch helper, contracts): `skills/common/nui.md`.

**Networking** - Validate client-provided entity handles and net IDs (existence, type, model, owner, routing bucket, distance) before trusting them. Avoid `TriggerClientEvent(name, -1)` broadcasts; scope to one player or a small recipient set, and prefer state bags for replicated visible state. Mechanics: `skills/common/networking.md`.

**Performance & cleanup** - Render cosmetic/attached/preview props locally from server-owned state; networked props only for shared gameplay entities. Cache hot lookups in locals; build reverse indexes (`Items["INDEX"][name]`) for repeated searches. No `Wait(0)` unless frame-level work is required; stage waits by distance/activeness. Avoid load-time caching of export results that go stale when the provider resource restarts (`skills/common/runtime.md`). Clean up entities, blips, zones, timers, callbacks, throttles, caches on player drop / resource stop, guarding entity cleanup with `DoesEntityExist`.

**Review order** - Server authority before style; public input boundaries before internal helpers; cleanup and lifecycle before adding caches, timers, callbacks, entities, zones, state; RedM/FiveM portability before moving code into shared files. Keep fixes local and direct unless repeated use justifies a helper or reference update.

## Memory

Read when debugging or reusing a learned pattern; write after a recurring fix or a newly verified quirk. Entries carry date and game build, cross-link `skills/` for the stable rule, and never duplicate rule text.

- `memory/common/` - `native-bugs.md` (native issues and workarounds), `common-errors.md` (recurring Lua/resource errors and fixes), `cfx-patterns.md` (reusable FXServer/CfxLua patterns: controller, index map, cleanup, config split, persistence), `security-performance.md` (learned patterns, quick-reference checklists).
- `memory/fivem/`, `memory/redm/` - game-specific namespaces: `README.md` plus `native-bugs.md` for game-only native issues (e.g. `SetPedAmmoByType` reserve ammo).
