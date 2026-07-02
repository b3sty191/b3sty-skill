# ox_lib Rules

Use this file only when a RedM/FiveM resource already depends on ox_lib or the task explicitly accepts adding ox_lib. b3sty resources do not assume ox_lib by default.

## Defaults

- Keep ox_lib integration direct; do not wrap every `lib.*` call in another local framework.
- Prefer official ox_lib modules over hand-rolled equivalents when the resource already depends on ox_lib.
- Do not add ox_lib just for one notification, one print helper, or one tiny utility.
- Keep authoritative gameplay checks server-side even when ox_lib handles UI, callbacks, zones, or progress.
- Use resource-prefixed names for callbacks, menus, events, and keys.

## Manifest

- Declare the dependency when the resource cannot run without ox_lib:
  ```lua
  dependency 'ox_lib'
  ```
- Load ox_lib before scripts that use `lib`, `cache`, or locale helpers:
  ```lua
  shared_scripts {
      '@ox_lib/init.lua',
      'config.lua',
  }
  ```
- Keep ox_lib imports out of standalone Lua tooling and non-Cfx scripts.
- If using locale files, include them under `files` and initialize locale once.
- Do not mix ox_lib-required code into files that are meant to run without that dependency.

## Callbacks

- Treat `lib.callback.register` handlers as public input boundaries.
- Server callback handlers receive `source` as the first argument; validate it and the rest of the payload.
- Client-to-server calls use `lib.callback.await(name, delay, ...)`; the second argument is a delay or `false`, not a player ID.
- Server-to-client calls use `lib.callback.await(name, playerId, ...)`; only use them for client-observable data.
- Never trust data returned by a client callback for rewards, money, inventory, ownership, permissions, or anti-abuse decisions.
- Rate-limit callback entry points that can be spammed from client UI or loops.
- Keep callback names explicit, for example `resource_name:getItemData`, not generic dispatch names.
- Use events for fire-and-forget state changes and callbacks for request/response flows.

## Waits And Streaming

- Use `lib.waitFor` for short dependency/state waits with a timeout.
- Avoid `lib.waitFor(..., false)` unless an infinite wait is truly safe and cannot hang gameplay forever.
- Use ox_lib streaming helpers such as `lib.requestModel` and `lib.requestAnimDict` when ox_lib is already available.
- Release streamed assets after use when the native requires cleanup, such as `SetModelAsNoLongerNeeded` or `RemoveAnimDict`.
- Do not hide invalid models, dicts, or assets behind silent retry loops.

## Interface

- Use `lib.notify` for user feedback when the resource already depends on ox_lib.
- Use `id` on notifications that can repeat quickly so they do not flood the screen.
- Register static context menus once, then open them with `lib.showContext`.
- Avoid constantly re-registering context menus that do not depend on changing state.
- Prefer `onSelect` callbacks for local UI behavior and explicit server events/callbacks for server work.
- Treat `serverEvent` and event-driven context menu args as untrusted once they reach the server.
- Use `lib.progressBar` or `lib.progressCircle` for deliberate timed actions, and check the returned completion/cancel result before applying effects.
- Keep progress completion effects server-authoritative when rewards, items, money, ownership, or saved state are involved.
- Use TextUI as a toggle: show on enter/available state, hide on exit/unavailable state. Do not call show every tick.

## Zones

- Use `lib.zones.sphere`, `lib.zones.box`, or `lib.zones.poly` for client interaction areas when ox_lib is present.
- Store zone handles and call `zone:remove()` on resource stop or when the zone is no longer valid.
- Keep `inside` handlers light; avoid database calls, heavy scans, or repeated server events from inside loops.
- Use `debug = true` only while placing or diagnosing zones.
- Server-side zones do not provide player `onEnter`, `onExit`, or `inside` trigger handlers; design server validation separately.
- Validate player distance/server position before applying important server-side effects from a zone interaction.

## Cache And Helpers

- Use `cache.ped`, `cache.vehicle`, and similar values when the project already relies on ox_lib cache and it improves clarity.
- Be careful with cached values across spawn/death/vehicle changes; re-read when stale state would break behavior.
- Prefer project-local indexes for domain data instead of pushing unrelated state into ox_lib helpers.
- Use ox_lib helpers where they reduce real code, not to make simple Lua harder to scan.

## Cleanup

- Hide open context menus, TextUI, and progress UI if the resource stops while they may be active.
- Remove zones, keybinds, timers, local props, blips, and callbacks owned by the resource.
- Clear NUI/focus state even when ox_lib UI is used beside custom NUI.
- Clean per-player callback/throttle state on `playerDropped`.

## Review Questions

- Is ox_lib already a dependency, or did this change add one for too little value?
- Are callback payloads validated and rate-limited like server events?
- Does any client callback result affect authority?
- Are zones removed and UI hidden on resource stop?
- Is a context menu registered once instead of rebuilt every tick/open?
- Does progress cancellation avoid applying rewards or saved state?
