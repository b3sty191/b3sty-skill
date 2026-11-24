# Shared Resource Structure Rules

Applies to both RedM and FiveM; game-specific behavior is in `skills/fivem/rules.md` and `skills/redm/rules.md`.

## Resource Structure

- Separate client, server, shared and config concerns. Common small-resource layout: `config.lua`, `configs/*.lua` for large split config/data files, `objects.lua` or another data file for a large focused dataset, `core/client.lua`, `core/server.lua`, `addons/` for optional extensions.
- Simple hardcoded values next to the logic when that reads better; large lists and repeated data in config/data files that return tables.
- CfxLua syntax extensions (supported compound assignment operators) only in RedM/FiveM Lua code.

## Events

- Validate event input server-side; never trust client-provided money, inventory, permission or ownership state.
- Custom events use resource-prefixed names with a side marker - `resource_name:server:action` handled on the server, `resource_name:client:action` on the client (for example `resource_name:server:add`, `resource_name:server:remove`, `resource_name:client:playerDropped`) - so ownership and direction read off the name.

## State

- The server owns important gameplay state; the client renders, attaches objects, shows UI and cleans up local entities.
- `Player(source).state` and state bags are acceptable for syncing visible state: the server changes it, clients react and render.
- Prefer server config `setr sv_stateBagStrictMode true` so clients cannot modify replicated player/entity state bags directly. Client-side non-replicated entity state is local-only - never base gameplay authority on it.
- Client flows request state changes through validated `:server:` events or callbacks; the server updates the state bag.

## Entities And Objects

- Check entity handles before use.
- Load models first: `RequestModel(model)`, then wait with a timeout until `HasModelLoaded(model)` is true, or `lib.requestModel(model)` when the resource already depends on ox_lib (`skills/common/ox-lib.md`); `SetModelAsNoLongerNeeded(model)` after spawning.
- Delete old entities before replacing them; clean up on resource stop, player drop, or when synced state disables them.
- Reattach loops are acceptable when objects may detach or disappear - keep the wait time appropriate.

## Local Vs Networked Props

- Local client-created props by default: cosmetic, preview, attached, UI, marker, render-only. Networked/server-owned only for shared gameplay state: pickup, loot, storage, placement, blocking collision, ownership, persistence, multi-player interaction.
- Local attached props keep the server authoritative over attach state; clients render/delete local objects from state bags or validated sync. Never network attached cosmetic props just so other players see them - sync the state and let each client render its own local copy.
- Never trust client-created prop handles, entity IDs or net IDs for rewards, ownership, permissions or saved state.
- A prop that becomes interactable or valuable once placed in the world is promoted to server-owned state: validate entity/model/distance/bucket before use.
- Local props: cleanup on state disable, player out of range, player drop, resource stop. Networked props: server registry, ownership rules, validation, cleanup path.

## Performance

- `Wait(0)` loops only where frame-level work is required; raise the wait when polling inactive state; keep hot loops small, caching expensive lookups and repeated native results where safe.
- Never eager-load large config/data files: require only the config modules the current client/server file needs.
- Event validation, throttles, callback cleanup, dirty saves and loop optimization: `skills/common/security-performance.md`.

## Compatibility

- Check whether behavior differs between RedM and FiveM before sharing code.
- b3sty resources assume no default framework: framework-free by default, with framework-specific logic isolated when a project depends on one so the rest stays portable.
- Game-specific logic follows `skills/fivem/rules.md` or `skills/redm/rules.md` guidance unless it has been confirmed portable.
