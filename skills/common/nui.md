# NUI Rules

Use this file when a RedM/FiveM resource has an in-game browser UI (NUI): HTML/CSS/JS (React, Svelte, Vue, or plain JS), `SendNUIMessage`, `RegisterNUICallback`, `SetNuiFocus`, or a `ui_page` in the manifest.

NUI is client-local only. It never carries authority. Treat the Lua<->browser bridge as a one more untrusted boundary and keep the server as the source of truth (see `skills/common/security-performance.md`).

## Contents

- Bridge Overview
- Manifest
- Lua To Browser
- Browser To Lua
- Focus And Input
- Message Contracts
- Validation
- Frontend Hygiene
- Performance
- Security
- Lifecycle And Cleanup
- Debugging
- Review Questions

## Bridge Overview

- NUI runs in CEF (Chromium Embedded Framework). The browser has no access to Lua globals, game natives, or the server. Every value crosses the bridge as JSON.
- The bridge is message-based, not a function call. Lua cannot read a DOM value directly and the browser cannot call a native; both sides must send messages and react.
- The browser only exists while the resource's `ui_page` is loaded and reachable. Messages sent before the page is ready are lost unless you queue them.
- NUI is client-side. Any data the client sends onward to the server must be re-validated there. NUI itself is UX and display, never security.

## Manifest

- Declare the UI entry point and every asset the browser loads:
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
- A missing file in `files` is a silent blank or 404 UI. List HTML, CSS, JS, fonts, images, and any nested asset globs explicitly.
- Keep the built UI in a stable path such as `web/dist/`. Build the framework output into that path; do not ship source/build tooling in the resource.
- Keep NUI code client-side; never load `ui_page` resources on the server.

## Lua To Browser

- `SendNUIMessage(table)` JSON-encodes the table and posts it to the browser's `window` `message` event:
  ```lua
  SendNUIMessage({ action = "open", items = items, title = "Shop" })
  ```
- The browser listens with `window.addEventListener("message", e => ...)`.
- Use one stable top-level key that names the message (`action`, `type`, or `event`), not an arbitrary payload the UI must pattern-match blindly.
- Do not send updated full data every frame. Send one open/update message and let the UI render its own state between updates.
- Functions, metatables, userdata (vectors, handles), and cyclic tables do not survive JSON. Send plain data: numbers, strings, booleans, arrays, plain tables.

## Browser To Lua

- The browser calls back into Lua with `fetch` against the resource URL:
  ```js
  const res = await fetch(`https://${GetParentResourceName()}/selectItem`, {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=UTF-8" },
      body: JSON.stringify({ item: name }),
  });
  const data = await res.json();
  ```
- `GetParentResourceName()` returns the resource name from inside the browser; use it so the resource stays rename-safe.
- Lua registers the handler with `RegisterNUICallback(name, cb)` (the `RegisterNuiCallback` alias is equivalent):
  ```lua
  RegisterNUICallback("selectItem", function(data, cb)
      -- validate data, do client-side UX, then forward to a :server: event
      cb({ ok = true })
  end)
  ```
- The `cb` argument sends the response that resolves the browser `fetch`. Call `cb` exactly once per request. Forgetting it leaves the browser promise pending; calling it twice is undefined.
- Always pass an explicit response object (for example `cb({ ok = true })`) even when there is no useful return value, so the browser promise resolves cleanly.

## Focus And Input

- `SetNuiFocus(hasFocus, hasInput)` controls cursor/game-input:
  - `hasFocus = true` shows the cursor and lets it interact with the UI.
  - `hasInput = true` lets mouse movement still reach the game while the UI is open. Most menus want `SetNuiFocus(true, false)`.
- `SetNuiFocusKeepInput(true)` keeps keyboard input flowing to the game while NUI has focus (for HUDs or chat-style overlays). Re-enable game input with `SetNuiFocusKeepInput(false)` on close.
- Treat focus as a toggle: set focus on open, clear it on close. Never call `SetNuiFocus(true, true)` every frame.
- A stuck cursor after the UI closes is almost always a missing `SetNuiFocus(false, false)` on the close path.

## Message Contracts

- Keep a single source of truth for the message names and shapes on the Lua side, and mirror them in the browser with a small typed module.
- Version the payload when the shape changes (`{ v = 2, action = "open", ... }`) so an older built UI can reject shapes it does not understand instead of rendering garbage.
- Send only the fields the UI needs. Do not push full player data, full inventory, prices the client should not know, or server-only config to the UI (see Security).

## Validation

- Treat every `RegisterNUICallback` payload as untrusted, same as a `:client:` event: the browser can be devtooled or scripted.
- Validate `type(...)` and bounds for fields that drive client behavior or that get forwarded to the server.
- For actions forwarded to the server, do the authoritative validation server-side and treat the NUI path as a UX hint.
- Never grant money, items, permissions, or access from a NUI callback alone. Forward a validated `:server:` event and let the server decide.
- The recipient of any value is still `source` (resolved server-side); never let a NUI payload pick a target player.

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
    TriggerServerEvent("shop:buy", { Item = itemName, Amount = amount })
    cb({ ok = true })
end)
```

## Frontend Hygiene

- Use one bridge module in the framework that owns `window.addEventListener("message")` and the `fetch` helper, so message names live in one place.
- Queue messages received before the framework is mounted, then flush on mount, so an early `SendNUIMessage` is not lost.
- Build the framework to a static bundle in `web/dist`; do not expect a dev server at runtime.
- Keep the bundle small and framework-light where it fits the resource style. b3sty prefers direct, readable UI code over heavy client frameworks when the UI is small.
- Avoid infinite render loops from message handlers that immediately post back to Lua; debounce rapid updates.

## Performance

- Send messages on state change, not on every frame or every UI tick.
- Debounce rapid client state into a single update message (for example, a search box) instead of sending per keystroke.
- Keep payloads small; send deltas for large lists instead of re-sending the whole dataset.
- Avoid polling Lua from the browser on a timer; use Lua-initiated messages or a single request/response.

## Security

- NUI is client-local and client-editable. It is display and UX, not authority.
- Never round-trip authority through NUI. The UI must not decide money, items, permissions, or access; it only requests them. A `cb({ ok = true })` is a display signal, not a grant.
- Never grant money/items/permissions directly from a NUI response. Grants happen server-side.
- Never send webhook URLs, API tokens, server secrets, admin flags, hidden reward logic, or full economy data to the UI.
- Do not let the UI drive trust: a "you are admin" flag in the UI means nothing. Permission is checked server-side with ACE.
- A NUI callback that forwards a valuable action must go through the same server validation as the matching `:server:` event.
- Full hardening rules and the give-value checklist are in `skills/common/security-performance.md` -> NUI Callback Hardening and Give-Value Event Hardening.

## Lifecycle And Cleanup

- Clear NUI focus (`SetNuiFocus(false, false)`) on UI close, player drop, and resource stop.
- Send a teardown message (for example `{ action = "close" }`) so the framework can unmount and stop timers/listeners.
- Remove client event handlers, threads, and local state created to feed the UI on resource stop.
- If the UI is hidden but persistent, prefer hide over destroy for fast re-open; still stop per-frame work while hidden.

## Debugging

- Use the browser devtools console and network tab for JS errors and failed `fetch` calls. Lua logs cannot see a JS exception.
- Confirm `ui_page` and every referenced file are present in `fxmanifest.lua` `files` when the UI is blank or assets 404.
- Confirm the browser `fetch` URL matches the `RegisterNUICallback` name exactly.
- Confirm `cb` is called once and returns JSON-encodable data.
- Confirm `GetParentResourceName()` resolves to the running resource name.
- See `skills/common/debugging.md` -> NUI Debugging for the full flow.

## Review Questions

- Is the server still the source of truth for everything the UI can affect?
- Is every `RegisterNUICallback` payload validated before it drives behavior or is forwarded to the server?
- Is focus cleared on close, drop, and stop?
- Does every callback call `cb` exactly once with JSON-encodable data?
- Are all UI files listed in `files`, and is `ui_page` correct?
- Are messages sent on change, not every frame?
- Is anything secret or authoritative leaking into the UI payload?
