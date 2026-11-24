# ox_lib Rules

Use only when a resource already depends on ox_lib or the task explicitly accepts adding it. b3sty resources do not assume ox_lib by default.

## Defaults

- Call `lib.*` directly: no wrapper framework around it, and no ox_lib added for one notification, print helper or tiny utility.
- Once the dependency exists, prefer official ox_lib modules over hand-rolled equivalents.
- Authoritative gameplay checks stay server-side even when ox_lib handles UI, callbacks, zones or progress.
- Resource-prefixed names for callbacks, menus, events and keys.

## Manifest

- Declare `dependency 'ox_lib'` when the resource cannot run without it, and load ox_lib before scripts that use `lib`, `cache` or locale helpers:
  ```lua
  shared_scripts {
      '@ox_lib/init.lua',
      'config.lua',
  }
  ```
- `'@ox_lib/init.lua'` swaps global `require` for `lib.require` - that is what lets `require('configs.items')` load resource files - so code using it breaks if ox_lib is removed (`skills/common/style.md` -> Lua Style has the no-ox_lib loader).
- Keep ox_lib imports out of standalone Lua tooling, non-Cfx scripts, and files meant to run without the dependency.
- With locale files, list them under `files` and initialize locale once.

## Callbacks

- `lib.callback.register` handlers are public input boundaries: validate `source` (first server argument) and the payload, and rate-limit entry points reachable from client UI or loops.
- Client-to-server is `lib.callback.await(name, delay, ...)` - the second argument is a delay or `false`, not a player ID. Server-to-client is `lib.callback.await(name, playerId, ...)`, only for client-observable data.
- Never trust a client callback result for rewards, money, inventory, ownership, permissions or anti-abuse decisions.
- Name callbacks explicitly (`resource_name:getItemData`), not generic dispatch. Events for fire-and-forget changes, callbacks for request/response.

## Waits And Streaming

- `lib.waitFor` for short dependency/state waits with a timeout; avoid `lib.waitFor(..., false)` unless an infinite wait truly cannot hang gameplay forever.
- `lib.requestModel` / `lib.requestAnimDict` when ox_lib is already available, releasing streamed assets after use where the native requires it (`SetModelAsNoLongerNeeded`, `RemoveAnimDict`).
- Never hide invalid models, dicts or assets behind silent retry loops.

## Interface

- `lib.notify` for user feedback; set `id` on notifications that can repeat quickly so they do not flood the screen.
- Register static context menus once, open with `lib.showContext`; do not re-register menus that do not depend on changing state.
- `onSelect` for local UI behavior, explicit server events/callbacks for server work. `serverEvent` and event-driven menu args are untrusted once they reach the server.
- `lib.progressBar` / `lib.progressCircle` for deliberate timed actions: check the completion/cancel result before applying effects, and keep effects server-authoritative when rewards, items, money, ownership or saved state are involved.
- TextUI is a toggle: show on enter/available, hide on exit/unavailable, never every tick.

## Zones

- `lib.zones.sphere`, `lib.zones.box` or `lib.zones.poly` for client interaction areas; store the handles and call `zone:remove()` on resource stop or when the zone stops being valid.
- Keep `inside` handlers light: no database calls, heavy scans or repeated server events in loops.
- `debug = true` only while placing or diagnosing zones.
- Server-side zones have no player `onEnter`, `onExit` or `inside` handlers: design server validation separately, and verify player distance/server position before applying important server-side effects from a zone interaction.

## Cache And Helpers

- `cache.ped`, `cache.vehicle` and similar where the project already relies on ox_lib cache and it improves clarity; re-read across spawn, death or vehicle changes wherever stale state would break behavior.
- Keep domain data in project-local indexes rather than pushing unrelated state into ox_lib helpers; use helpers where they cut real code, not to make simple Lua harder to scan.

## Cleanup

- Hide open context menus, TextUI and progress UI if the resource stops while they may be active.
- Remove zones, keybinds, timers, local props, blips and callbacks owned by the resource.
- Clear NUI/focus state even when ox_lib UI sits beside custom NUI, and per-player callback/throttle state on `playerDropped`.

## Review Questions

- ox_lib already a dependency, or added here for too little value?
- Callback payloads validated and rate-limited like server events?
- Any client callback result affecting authority?
- Zones removed and UI hidden on resource stop?
- Context menu registered once instead of rebuilt every tick/open?
- Progress cancellation still applying rewards or saved state?
