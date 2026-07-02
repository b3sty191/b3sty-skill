# Shared Resource Structure Rules

Use this file for rules that apply to both RedM and FiveM. Use `skills/fivem/rules.md` or `skills/redm/rules.md` when behavior is game-specific.

## Resource Structure

- Keep client, server, shared, and config concerns separated.
- A common small-resource structure is:
  - `config.lua`
  - `configs/*.lua` for large split config/data files
  - `objects.lua` or another data file when a dataset is large and focused
  - `core/client.lua`
  - `core/server.lua`
  - `addons/` for optional extensions
- Keep simple hardcoded values close to the logic when that is easier to read.
- Split large lists and repeated data into config/data files that return tables.
- Use CfxLua syntax extensions such as supported compound assignment operators only in RedM/FiveM Lua code.

## Events

- Validate server-side event input.
- Do not trust client-provided state for money, inventory, permissions, or ownership.
- Prefer explicit event names with the resource prefix.
- All custom events must use resource-prefixed event names with a side marker.
- Required format:
  - `resource_name:server:action` for events handled on the server.
  - `resource_name:client:action` for events handled on the client.
- Example names:
  - `resource_name:server:add`
  - `resource_name:server:remove`
  - `resource_name:client:playerDropped`
- This makes event ownership and direction easy to identify while reading code.

## State

- The server should own important gameplay state.
- The client should mainly render, attach objects, show UI, and clean up local entities.
- `Player(source).state` and state bags are acceptable for syncing visible state to clients.
- When using state bags, keep the server responsible for changing the state and let clients react to render changes.

## Entities And Objects

- Check entity handles before using them.
- Load models before creating objects, for example with `lib.RequestModel`.
- Delete old entities before replacing them when needed.
- Clean up entities on resource stop, player drop, or when synced state disables them.
- Reattach loops are acceptable when objects may detach or disappear, but keep the wait time appropriate.

## Performance

- Avoid tight loops with `Wait(0)` unless frame-level work is required.
- Increase wait time when polling inactive state.
- Cache expensive lookups where safe.
- Avoid eager-loading large config/data files when only one script needs them.
- Require only the config modules needed by the current client/server file.
- Keep hot loops small and avoid repeated native calls inside them when a local cached value is enough.
- Apply `skills/common/security-performance.md` for event validation, throttles, callback cleanup, dirty saves, and loop optimization.

## Compatibility

- Check whether behavior differs between RedM and FiveM before sharing code.
- b3sty resources do not assume a default framework. Write framework-free code by default.
- When a project already depends on a framework, keep framework-specific logic isolated so the rest stays portable.
- Keep game-specific logic in `skills/fivem/rules.md` or `skills/redm/rules.md` guidance unless it has been confirmed portable.
