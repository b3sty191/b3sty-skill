# FXServer Rules

## fxmanifest

- Keep `fxmanifest.lua` explicit and minimal: declare client, server, shared, UI and dependency files; load nothing unused.
- Use `fx_version 'cerulean'` and `lua54 'yes'`. `lua54 'yes'` selects Lua 5.4 (bitwise `&`, `|`, `~`, `<<`, `>>` are standard); CfxLua adds compound assignment operators and backtick hashes on top - CfxLua-only, never in standard Lua or standalone tooling (`skills/common/style.md` -> CfxLua Syntax).
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

## Resource Lifecycle

- Handle start and stop cleanly: clean up entities, blips, zones, timers and callbacks on stop.
- Never assume resource start order unless dependencies are declared.
