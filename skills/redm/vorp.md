# VORP Rules

Use when a RedM resource runs on VORP (`vorp_core`, `vorp_inventory`). Cross-framework shapes and the bridge stay in `skills/common/frameworks.md`; this file is the VORP depth.

Verified against VORPCORE source, 2026-11-24: `vorp_core-lua` v3.4 (`312466f`), `vorp_inventory-lua` v4.5 (`0f8f6d5`), `vorp_lib` v0.5 (`690bd2e`). Re-check signatures against the installed version; record differences in `memory/redm/`.

## Start Order

- `ensure oxmysql`, then `vorp_core`, then `vorp_inventory`, then your resource: both VORP manifests load `@oxmysql/lib/MySQL.lua`, and `vorp_inventory` loads `@vorp_core/client/dataview.lua`.
- ox_lib is not in VORP's chain. Use it only when the server already runs it (`skills/common/ox-lib.md`).
- `vorp_lib` (v0.5) says breaking changes may occur until v1.0: treat it as unstable and pin the version you build against.

## Users And Characters

- `local Core = exports.vorp_core:GetCore()` once at the top of the server file.
- `Core.getUser(source)` returns `nil` for a missing source or a player with no VORP user. VORP keys users by the `steam:` identifier (`GetPlayerIdentifierByType(source, 'steam')`), so a player connected without Steam never has one. Nil-check every call.
- `user.getUsedCharacter` is a field, not a method, and is `{}` until a character is selected: check `character.charIdentifier`.
- It is a **snapshot**. Fields (`money`, `gold`, `rol`, `job`, `jobGrade`, `group`) are copied when `getUser` runs; methods (`addCurrency`, `removeCurrency`, ...) change the live character but do not refresh that snapshot. Re-read `Core.getUser(source).getUsedCharacter` immediately before a check; never reuse a character table across a yield or a later event.
- Admin and job decisions read the server character (`character.group`, `character.job`), never the client.

## Money

`character.addCurrency(type, amount)` and `character.removeCurrency(type, amount)` take type `0` money, `1` gold, `2` rol. Neither validates anything: no balance check, no sign check (a negative amount to `addCurrency` subtracts), an unknown type silently does nothing, and nothing is returned. Validate the amount and check a fresh balance in the same non-yielding block, then mutate (`skills/common/give-value-hardening.md` -> Give-value event checklist).

```lua
local Core = exports.vorp_core:GetCore()

local function TakeMoney(source, price)
    if type(price) ~= "number" or price <= 0 or price ~= math.floor(price) then return false end
    local user = Core.getUser(source)
    if not user then return false end
    local character = user.getUsedCharacter -- fresh snapshot, read right before the check
    if not character.charIdentifier or character.money < price then return false end
    character.removeCurrency(0, price) -- no check of its own, returns nothing
    return true
end
```

## Callbacks

- `Core.Callback.Register(name, function(source, cb, ...) cb(result) end)` is callback-style: returning a value does not answer the client, and a path that never calls `cb` leaves the client waiting.
- Every registered server callback is client-callable: the net event `vorp:TriggerServerCallback` dispatches any registered name a client sends. Validate it like a `:server:` event (`skills/common/security-performance.md` -> Event Trust Boundary).
- Registering a name again replaces the earlier handler without a warning, across resources too. Prefix names with your resource.
- On the server, `Core.Callback.TriggerAwait(name, source, ...)` asks that client; its answer is client-controlled data.
- On a VORP + ox_lib server, `lib.callback` is return-style instead (`skills/common/ox-lib.md` -> Callbacks). Pick one style per resource and never register one name in both.

## Notifications And State Bags

- Server `Core.NotifyTip(source, text, duration)`, `Core.NotifyLeft(source, title, subtitle, dict, icon, duration, color)`, `NotifyRightTip`, `NotifyObjective`, and the rest are `TriggerClientEvent` wrappers over the RDR3 UI feed; `lib.notify` is ox_lib's NUI toast. Use what the server already uses; do not add ox_lib only for notifications.
- On character select VORP sets replicated player state bags `IsInSession` and `Character` (`Group`, `FirstName`, `LastName`, `Job`, `JobLabel`, `Grade`, `Money`, `Gold`, `Rol`, `CharId`, ...) and refreshes `Money`/`Gold`/`Rol` on currency changes. Every client can read every player's bag, VORP's own client reads other players' names from it. Display only: server decisions read the character, never `Player(source).state.Character`.
- Lifecycle: server `AddEventHandler("vorp:SelectedCharacter", function(source, character) end)` (a server-local event; `character` is a snapshot), client `RegisterNetEvent("vorp:SelectedCharacter", function(charId) end)`. Restart re-init is in `skills/common/frameworks.md` -> Lifecycle Events.

## Inventory Exports

Every `vorp_inventory` export takes an optional callback and also returns its result, so passing `nil` for `cb` and using the return value works (VORP's own `vorp_core` does this). Argument positions differ per export - never guess:

| Export | Arguments (v4.5) | Result |
|---|---|---|
| `getItemCount` | `(source, cb, itemName, metadata, percentage)` | count |
| `getItem` | `(source, itemName, cb, metadata, percentage)` | item or `nil` |
| `canCarryItem` | `(source, itemName, amount, cb)` | boolean |
| `canCarryItems` | `(source, amount, cb)` | boolean (slot capacity) |
| `addItem` | `(source, name, amount, metadata, cb, allow, degradation, percentage)` | boolean |
| `subItem` | `(source, name, amount, metadata, cb, allow, percentage)` | boolean |
| `subItemById` (alias `subItemID`) | `(source, id, cb, allow, amount)` | boolean |
| `canCarryWeapons` | `(source, amount, cb, weaponName)` | boolean |
| `createWeapon` | `(source, weaponName, ammo, components, comps, cb, ...)` | weapon or `nil` |
| `addBullets` | `(source, bulletType, amount, cb)` | boolean |
| `registerUsableItem` | `(name, cb, resourceName)` | - |

- `subItemById` replaced `subItemID` in v4.0 (the old name still works); v4.0 also added the `percentage` (decay) arguments.
- Export names are case-sensitive: `BlackListCustomAny` with a capital B. A wrong case throws `No such export`, which aborts the handler that called it.

## Inventory Traps

- `addItem` does not check capacity. Call `canCarryItem` (and `canCarryItems` for slots) before taking payment; honor a `false` from `addItem` (unknown item, no user, `amount <= 0`) and refund in the same path.
- `addItem` can yield (a database insert for a new stack). Keep the per-source in-flight lock from the give-value checklist around the whole buy, not just the money step.
- `addItem` and `subItem` compare `amount <= 0`: a string amount throws. Validate type, integer, and a cap first.
- `subItem` **with metadata** does not check the count: it removes what the matching stack holds, down to 0, and still returns `true`. Read `getItemCount(source, nil, name, metadata)` first and require at least the amount. Without metadata it returns `false` when the total is short.
- `createWeapon` does not check carry weight: call `canCarryWeapons(source, 1, nil, weaponName)` first, as `vorp_core`'s own give-weapon command does.

## Usable Items And Context Menus

- `registerUsableItem(name, cb, GetCurrentResourceName())`: the item must exist in the items table with usable set, or the callback never runs. A second registration of the same name, from any resource, silently replaces the first (a warning prints about 15 seconds after start).
- The callback gets `{ source = source, item = { id, name, count, metadata, ... } }` after VORP confirms the player holds that item id. It does not consume the item: remove it yourself with `subItemById(source, data.item.id, nil, false, 1)`, after the effect succeeds.
- `addAllowedContextMenuEvent(eventName, GetCurrentResourceName())` whitelists only the event **name**. VORP then fires it server-locally as `TriggerEvent(name, source, arguments, itemId)` with `arguments` and `itemId` taken from the client. Register the handler with `AddEventHandler`, take the player from its first parameter (the implicit `source` is not the player here), re-check the player holds `itemId`, and validate `arguments`.

## Give-Value Mapping

- Money, gold, rol: `addCurrency` / `removeCurrency` have no checks - the full give-value checklist applies.
- Items: `canCarryItem` -> take payment -> `addItem` -> check the result -> refund on `false`.
- Weapons and ammo: `canCarryWeapons` -> `createWeapon`; `addBullets` with a server-chosen type and amount.
- Horses and wagons: spawn only from a server-validated request where the server picks the model and position; never from a client event that carries a model or coords (`skills/common/client-input-validation.md` -> Entity And Net ID Validation, `skills/common/networking.md` -> Creating Networked Entities).

## Review Questions

- Is every `getUser` nil-checked, and every character re-read right before its check?
- Does every currency call validate the amount and check a fresh balance first?
- Are inventory exports called with the exact argument order, and is every result checked?
- Is capacity checked before payment, and metadata `subItem` preceded by a count check?
- Are VORP server callbacks validated as client-callable, with resource-prefixed names?
- Do context-menu handlers re-verify the item and validate the client's arguments?
