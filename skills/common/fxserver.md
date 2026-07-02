# FXServer Rules

## fxmanifest

- Keep `fxmanifest.lua` explicit and minimal.
- Declare client, server, shared, UI, and dependency files clearly.
- Avoid loading unused files.
- Use `fx_version 'cerulean'`.
- Use `lua54 'yes'`.
- Note: `lua54 'yes'` selects the Lua 5.4 runtime, but FXServer's build also adds CfxLua extensions on top of it - the compound assignment operators and bitwise operators. Those operators are CfxLua-only and must not be used in standard Lua or standalone Lua tooling. See `skills/common/style.md` -> CfxLua Syntax for the full list.
- Use `games { 'rdr3', 'gta5' }` when the resource supports both RedM and FiveM.
- For FiveM-only manifests, apply `skills/fivem/rules.md`.
- For RedM-only manifests, apply `skills/redm/rules.md`.
- Include `rdr3_warning` when the resource supports RedM.
- ASCII banner headers are acceptable when they fit the resource style.
- Do not hardcode project-specific branding such as author names, descriptions, or framework imports unless the resource actually belongs to that project.

## Typical Layout

- Keep the manifest readable with grouped blocks:
  - `shared_scripts`
  - `client_scripts`
  - `server_scripts`
  - `files`
- Prefer paths such as `core/client.lua` and `core/server.lua` for main logic.
- Use `config.lua` for small/shared config that the resource broadly needs.
- Use `configs/*.lua` for large split config modules.
- Do not include or require split config modules unless the current runtime/script needs them.
- Use addon globs such as `addons/**/*client*.lua` and `addons/**/*server*.lua` when the resource is intentionally extensible.
- Keep config files included in `files` when clients need to access them.

## Server Logic

- Validate all inputs on the server.
- Keep permission checks server-side.
- Avoid storing important gameplay state only on the client.

## Server Config

- Prefer `setr sv_stateBagStrictMode true` when the target artifact supports it.
- With strict state bag mode enabled, only the server can modify networked entity state and player state.
- Client-side non-replicated entities are not affected, but they must not be treated as authoritative replicated state.
- Client code should request state changes through validated `:server:` events or callbacks, then render from the replicated state.
- Audit existing resources before enabling strict mode because client-side replicated state bag writes will stop working.

## Resource Lifecycle

- Handle resource start and stop cleanly.
- Clean up entities, blips, zones, timers, and callbacks when the resource stops.
- Avoid assumptions about resource start order unless dependencies are declared.
