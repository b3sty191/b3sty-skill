# NUI Rules

For in-game browser UI (NUI): HTML/CSS/JS (React, Svelte, Vue, plain JS), `SendNUIMessage`, `RegisterNUICallback`, `SetNuiFocus`, or a `ui_page` in the manifest.

NUI is client-local and never authoritative. Treat the Lua<->browser bridge as one more untrusted boundary; the server stays the source of truth (`skills/common/security-performance.md`).

## Contents

Bridge Overview, Manifest, Lua To Browser, Browser To Lua, Focus And Input, Message Contracts, Validation, Frontend Hygiene, Performance, Security, Lifecycle And Cleanup, Debugging, Review Questions.

## Bridge Overview

- NUI runs in CEF (Chromium Embedded Framework): no Lua globals, no game natives, no server; every value crosses as JSON.
- Message-based, not calls - Lua cannot read a DOM value, the browser cannot call a native; both send messages and react.
- The browser exists only while the resource's `ui_page` is loaded and reachable; messages sent before it is ready are lost unless queued.
- NUI is UX and display, never security: whatever it forwards is re-validated server-side.

## Manifest

- Declare the entry point and every asset the browser loads:
  ```lua
  ui_page 'web/dist/index.html'

  files {
      'web/dist/index.html',
      'web/dist/index.css',
      'web/dist/index.js',
      'web/dist/assets/**/*',
      'web/fonts/*',
  }
  ```
- A file missing from `files` is a silent blank or 404 UI: list HTML, CSS, JS, fonts, images, nested globs explicitly.
- Build framework output to a stable path such as `web/dist/`, shipping no source or build tooling; never load `ui_page` resources on the server.

## Lua To Browser

- `SendNUIMessage(table)` JSON-encodes and posts to the browser `window` `message` event, read with `window.addEventListener("message", e => ...)`:
  ```lua
  SendNUIMessage({ action = "open", items = items, title = "Shop" })
  ```
- One stable top-level key names the message (`action`, `type`, `event`), not a payload the UI pattern-matches blindly. Send one open/update message and let the UI hold its own state between updates; never resend full data per frame.
- JSON drops functions, userdata, CfxLua vectors (`vector3` etc.) and cyclic tables: convert vectors to `{ x = v.x, y = v.y, z = v.z }`. Entity handles are client-local integers meaningless in the browser - send display data or a server-issued ID. Plain numbers, strings, booleans, arrays, tables only.

## Browser To Lua

- The browser calls back with `fetch` on the resource URL; `GetParentResourceName()` names the resource inside the browser, keeping it rename-safe:
  ```js
  const res = await fetch(`https://${GetParentResourceName()}/selectItem`, {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=UTF-8" },
      body: JSON.stringify({ item: name }),
  });
  const data = await res.json();
  ```
- Lua handles it with `RegisterNUICallback(name, cb)` (alias `RegisterNuiCallback`):
  ```lua
  RegisterNUICallback("selectItem", function(data, cb)
      -- validate data, do client-side UX, then forward to a :server: event
      cb({ ok = true })
  end)
  ```
- `cb` resolves that `fetch`: call it exactly once per request, always with an explicit object (`cb({ ok = true })`) even when there is nothing to return, so the promise resolves cleanly. Forgetting it times the request out and rejects the `fetch` with an error (wrap `fetch` in try/catch in the bridge helper); calling it twice is undefined.

## Focus And Input

- `SetNuiFocus(hasFocus, hasCursor)`: `hasFocus = true` gives the page input focus, `hasCursor = true` shows the cursor. Clickable menu: `SetNuiFocus(true, true)`; text prompt: `SetNuiFocus(true, false)` - keyboard focus, no cursor.
- `SetNuiFocusKeepInput(true)` keeps keyboard and mouse controls reaching the game while NUI has focus (HUDs, chat-style overlays); block unwanted ones with `DisableControlAction` each frame. Call `SetNuiFocusKeepInput(false)` on close to restore the default (focused NUI captures input), or the next focused UI leaks input to the game.
- Focus is a toggle: set on open, clear on close, never every frame. `SetNuiFocus(false, false)` returns input to the game; a stuck cursor after close is almost always a missing one there.

## Message Contracts

- One source of truth for message names and shapes on the Lua side, mirrored by a small typed module in the browser.
- Version the payload when the shape changes (`{ v = 2, action = "open", ... }`), so an older built UI rejects what it does not understand instead of rendering garbage.
- Send only fields the UI needs - never full player data, full inventory, prices the client should not know, or server-only config (see Security).

## Validation

- Every `RegisterNUICallback` payload is untrusted, as hostile as a client-triggered `:server:` event: the browser can be devtooled or scripted.
- Check `type(...)` and bounds for fields that drive client behavior or get forwarded; forwarded actions get authoritative validation server-side, the NUI path is a UX hint.
- Never grant money, items, permissions, or access from a NUI callback - forward a validated `:server:` event and let the server decide. The recipient is still `source` resolved server-side; a NUI payload never picks a target player.

```lua
-- hardened: validate schema, forward a single server request, cb() is a display signal only
RegisterNUICallback("buyItem", function(data, cb)
    if type(data) ~= "table" then cb({ ok = false }) return end

    local itemName = data.item
    local amount = tonumber(data.amount)
    if type(itemName) ~= "string" or itemName == "" then cb({ ok = false }) return end
    if not amount or amount ~= amount then cb({ ok = false }) return end
    amount = math.floor(amount)
    if amount <= 0 or amount > 100 then cb({ ok = false }) return end

    -- the server re-derives identity, catalog, price, and affordability; cb is NOT the grant
    TriggerServerEvent("shop:server:buy", { Item = itemName, Amount = amount })
    cb({ ok = true })
end)
```

## Frontend Hygiene

- One bridge module owns `window.addEventListener("message")` and the `fetch` helper, keeping message names in one place.
- Queue messages arriving before mount and flush on mount, so an early `SendNUIMessage` is not lost.
- Build to a static bundle in `web/dist`; no dev server at runtime. Keep it small and framework-light where it fits: b3sty prefers direct, readable UI code over heavy frameworks for small UIs.
- Avoid render loops from handlers that post straight back to Lua; debounce rapid updates.

## Performance

- Send on state change, not every frame or UI tick; debounce rapid client state (a search box) into one update instead of one per keystroke.
- Keep payloads small - deltas for large lists, not the whole dataset.
- No timer polling of Lua from the browser; use Lua-initiated messages or a single request/response.

## Security

- NUI is client-local and client-editable: display and UX, not authority.
- **XSS**: any string another player can influence (player names, chat, notes, item labels, shop names) is an XSS payload on the victim's screen. Framework interpolation (React/Svelte `{value}`, Vue `{{ value }}`) escapes it as text; `innerHTML`, `insertAdjacentHTML`, `document.write`, `{@html}`, `v-html` are the sinks that execute it. Never feed player-controlled data to a raw-HTML sink; if rich text is unavoidable, sanitize with a vetted library and a strict allowlist.
- XSS in CEF is not "just UI": injected script can call every `RegisterNUICallback` as the victim player, so a rendering sink is full compromise of that player's client-side surface.
- Validate the scheme of dynamic `href`/`src` (`https:`/`nui:` only); a `javascript:` URL executes on click. Build `nui://` asset paths from a restricted character set so a crafted name cannot traverse (`../`) out of the folder.
- Bound player-controlled string length before rendering; one giant value can freeze or break the HUD.
- Ship all JS/CSS in the local bundle, never loading remote scripts at runtime - a compromised CDN becomes code in every player's NUI. Remote image URLs from data are a tracking/bandwidth vector: allowlist hosts or proxy them, with an `onerror` fallback.
- Never round-trip authority through NUI: the UI requests money, items, permissions, access, never decides or grants them - `cb({ ok = true })` is a display signal. A "you are admin" flag in the UI means nothing; permission is checked server-side with ACE, and a callback forwarding a valuable action takes the same server validation as the matching `:server:` event.
- Never send webhook URLs, API tokens, server secrets, admin flags, hidden reward logic, or full economy data to the UI.
- Full hardening and the give-value checklist: `skills/common/client-input-validation.md` -> NUI Callback Hardening and `skills/common/give-value-hardening.md` -> Give-Value Event Hardening.

## Lifecycle And Cleanup

- Clear NUI focus (`SetNuiFocus(false, false)`) on UI close, player drop, and resource stop.
- Send a teardown message (`{ action = "close" }`) so the framework unmounts and stops timers/listeners; on resource stop remove the handlers, threads, and local state that fed the UI.
- A hidden-but-persistent UI prefers hide over destroy for fast re-open, but still stops per-frame work while hidden.

## Debugging

- Browser devtools console and network tab show JS errors and failed `fetch` calls; Lua logs cannot see a JS exception.
- Blank UI or 404 assets: check `ui_page` and every referenced file in `fxmanifest.lua` `files`.
- Failed or hanging `fetch`: the URL matches the `RegisterNUICallback` name exactly, `cb` is called once with JSON-encodable data, and `GetParentResourceName()` resolves to the running resource name.
- Full flow: `skills/common/debugging.md` -> NUI Debugging.

## Review Questions

- Server still the source of truth for everything the UI affects, with nothing secret or authoritative in the payload?
- Every `RegisterNUICallback` payload validated before it drives behavior or is forwarded, and `cb` called exactly once with JSON-encodable data?
- Focus cleared on close, drop, and stop?
- All UI files in `files`, `ui_page` correct?
- Messages sent on change, not every frame?
- Player-controlled string reaching a raw-HTML sink (`innerHTML`, `{@html}`, `v-html`) or an unvalidated dynamic `href`/`src`?
- All scripts/styles shipped locally, no runtime remote loads?
