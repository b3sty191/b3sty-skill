# FXServer Rules

## fxmanifest

- Keep `fxmanifest.lua` explicit and minimal: declare client, server, shared, UI and dependency files; load nothing unused.
- Use `fx_version 'cerulean'`. Every Lua script runs on Lua 5.4 (bitwise `&`, `|`, `~`, `<<`, `>>` are standard): Cfx removed Lua 5.3 in June 2025, so `lua54 'yes'` is deprecated and unneeded (fivem-docs resource manifest, checked 2026-11-24). An old resource that never set it now runs on 5.4: `print` formats with `__tostring` and ignores a global `tostring` override, `math.random` is xoshiro256** so a fixed seed gives a different sequence, and since October 2026 `<=`/`>=` on tables need `__le` (`memory/common/common-errors.md`). CfxLua adds compound assignment operators and backtick hashes on top - CfxLua-only, never in standard Lua or standalone tooling (`skills/common/style.md` -> CfxLua Syntax).
- Dual-game resources: `games { 'rdr3', 'gta5' }`, plus `rdr3_warning` whenever RedM is supported. FiveM-only manifests: `skills/fivem/rules.md`; RedM-only: `skills/redm/rules.md`.
- ASCII banner headers are fine if they fit the resource style; never hardcode project branding (author names, descriptions, framework imports) unless the resource belongs to that project.

## Typical Layout

- Group the manifest: `shared_scripts`, `client_scripts`, `server_scripts`, `files`.
- `core/client.lua` + `core/server.lua` for main logic, `config.lua` for small/shared config the resource broadly needs, `configs/*.lua` for large split modules - included only where the current script needs them.
- Addon globs (`addons/**/*client*.lua`, `addons/**/*server*.lua`) when the resource is intentionally extensible.
- Keep config files in `files` when clients must access them.
- Browser UI: declare `ui_page` and list every browser asset in `files`; bridge mechanics (focus, callbacks, message contracts) are in `skills/common/nui.md`.
- Load order and `ensure`/`start` semantics: `skills/common/runtime.md` -> Resource Lifecycle, `skills/common/multi-resource.md` -> Dependencies And Load Order.

## Server Logic

- Validate all input server-side, keep permission checks server-side, and never keep important gameplay state only on the client.

## Server Config

- Security hardening baseline for `server.cfg`: `references/server.cfg.example`; the rules behind it are in `skills/common/server-hardening.md` -> Server Hardening And Operations.
- Prefer `setr sv_stateBagStrictMode true` where the artifact supports it: only the server may then modify networked entity state and player state. Client-side non-replicated entities are unaffected, but are not authoritative replicated state.
- Client code requests state changes through validated `:server:` events or callbacks, then renders the replicated state.
- Audit existing resources before enabling strict mode: client-side replicated state bag writes stop working.
- `ensure [name]` starts every resource under any bracketed folder called `[name]`, at any depth under `resources/`, so a generic category name collides with existing trees: `ensure [maps]` also started cfx-server-data's `[gamemodes]/[maps]` (fivem-map-hipster, fivem-map-skater), which ESX then stopped with script errors (verified 2026-11-26, artifact 38781). Give a category you `ensure` a project-unique name (`[crest-maps]`, `[dropin-maps]`).
- Never put `;` in a `.cfg` comment: `;` separates commands even after `#`, so the rest of the line runs as a command. `## ... entwhy); resgate_accept and` ran `resgate_accept and`, and ordinary prose comments print `No such command the.` at every boot (verified 2026-11-26, artifact 38781). Grep for it: `grep -n ';' *.cfg | grep '#'`.

## Resource Lifecycle

- Handle start and stop cleanly: clean up entities, blips, zones, timers and callbacks on stop.
- Never assume resource start order unless dependencies are declared.
