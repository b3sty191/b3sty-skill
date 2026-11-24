# ox Ecosystem Rules

Use for overextended resources beyond the `lib` runtime: **ox_inventory** (items, stashes, shops) and **ox_target** (interaction zones). `lib` itself (callbacks, `lib.zones`, notify, context menus) is in `skills/common/ox-lib.md`; which inventory a framework runs is in `skills/common/frameworks.md` -> Items; give-value security still applies on top (`skills/common/give-value-hardening.md` -> Give-Value Event Hardening).

API shapes change between versions: confirm against the installed version's source before relying on an export or hook payload, and record verified differences in `memory/`.

## ox_inventory Is Server-Authoritative - Use Its Exports

- ox_inventory owns server item state. Never mutate inventory with your own table or a parallel framework item call - go through its exports so its validation, weight and persistence run:
  - `exports.ox_inventory:CanCarryItem(inv, name, count)` - capacity, before payment or before starting the action.
  - `exports.ox_inventory:AddItem(inv, name, count, metadata, slot)` - returns success plus a reason; honor a `false`.
  - `exports.ox_inventory:RemoveItem(inv, name, count, metadata, slot)`.
  - `exports.ox_inventory:GetItem(inv, name, metadata, returnsCount)` - the real server-side count; never a client-reported amount.
- Capacity-check, take payment, grant, refund in the same path if the grant fails: `CanCarryItem` false before `AddItem` is what stops money leaving with no item arriving.
- Item names come from the server item list or your config, never the client payload - look the name up in your own index first.
- `exports.ox_inventory:SetMetadata(inv, slot, metadata)` **replaces** the whole metadata table, no merge: read the slot (`GetSlot`), mutate it, write the full table back. A partial table wipes durability, charges and the rest.
- Items stack only when name **and** metadata match: volatile metadata (positions, timestamps, per-use counters) makes every write a new non-stacking slot and floods the inventory. Keep metadata small and stable, changing values elsewhere.

## Hooks Are The Anti-Dupe Boundary

ox_inventory fires server-side hooks around the actions a cheater abuses: the sanctioned place to reject a move before it happens, instead of policing inventory from outside.

- `exports.ox_inventory:registerHook(event, cb, options)` returns a `hookId`; hooks are cleared for your resource on `onResourceStop`. Events: `swapItems`, `buyItem`, `craftItem`, `createItem`, `usingItem`, `openInventory`, `openShop`.
- The callback gets the action payload (for `swapItems`: `source`, `fromInventory`, `fromSlot`, `fromType`, `toInventory`, `toSlot`, `toType`, `count`, `action`). **Return `false` to cancel the action** - that blocks a disallowed move, a cross-inventory dupe, an out-of-range transfer. Narrow which calls fire it with `options` (`itemFilter`, `inventoryFilter`) so the hook stays cheap.
- The hook runs server-side with real inventory state, so it enforces what a client cannot be trusted with: distance between the two inventories, whether this player may open that stash, job/gang gating on a shop, a per-item transfer cap.

```lua
-- Block moving a flagged item into any container the player does not own.
local hookId = exports.ox_inventory:registerHook("swapItems", function(payload)
    if payload.toType ~= "container" then return end
    if not PlayerOwnsContainer(payload.source, payload.toInventory) then
        return false   -- cancels the move
    end
end, {
    itemFilter = { marked_cash = true },
})
```

## Stashes And Shops Are Registered Server-Side

- Register stashes and shops on the server (`RegisterStash`, `RegisterShop`, or the `data/shops.lua` / `data/stashes.lua` definitions), never from a client request: a client that can ask the server to create or open an arbitrary stash id reaches another player's or another job's storage.
- Gate access with the stash's `groups`/`jobs` plus a server-side distance and ownership check in a hook; the client only showing the UI is not a gate.
- Shop prices and stock live server-side in the shop definition. A `buyItem` hook is where dynamic pricing or purchase limits go - never trust a price or quantity from the client.

## ox_target Is Client-Side UX - Re-Validate On The Server

ox_target draws the interaction and decides locally whether an option shows; all of it runs on the attacker's machine.

- `canInteract`, `onSelect`, `distance` and `event`/`serverEvent` all evaluate client-side. `canInteract` returning false only hides the option; it is not a security control.
- Any server effect a target option triggers (`serverEvent`, callback) re-validates server-side: distance to the entity/coords, ownership or job, cooldown, and that the entity or net ID is real (`skills/common/client-input-validation.md` -> Entity And Net ID Validation). Treat a target `serverEvent` exactly like any `:server:` event (`skills/common/security-performance.md` -> Event Trust Boundary).
- Add and remove options by a stable name so a restart leaves no duplicate or orphaned interaction; remove them on `onResourceStop`.
- Keep `canInteract`/`onSelect` cheap - they run during targeting: no server round-trips, no heavy scans.

## Review Questions

- Item state mutated through ox_inventory exports, or written in parallel somewhere?
- Capacity checked before payment, failed grant refunded in the same path?
- Dupe- or access-sensitive action enforced in a `registerHook` returning `false`, not policed after the fact?
- Stashes and shops registered server-side with group/distance gating, not opened from a client-supplied id?
- Every ox_target `serverEvent`/callback re-checking distance, ownership and the entity server-side?
