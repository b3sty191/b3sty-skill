# ox Ecosystem Rules

Use this file when a FiveM/RedM resource integrates with overextended resources
beyond the `lib` runtime: **ox_inventory** (items, stashes, shops) and
**ox_target** (interaction zones). For the `lib` API itself (callbacks,
`lib.zones`, notify, context menus) use `skills/common/ox-lib.md`. For which
inventory a framework runs, see `skills/common/frameworks.md` -> Items. The
give-value security rules still apply on top of everything here
(`skills/common/security-performance.md` -> Give-Value Event Hardening).

API shapes change between ox_inventory/ox_target versions; confirm against the
installed version's source before relying on an export or a hook payload, and
record verified differences in `memory/`.

## ox_inventory Is Server-Authoritative - Use Its Exports

- ox_inventory owns item state on the server. Never mutate a player's inventory
  by writing your own table or a framework item call in parallel; go through its
  server exports so its own validation, weight, and persistence run:
  - `exports.ox_inventory:CanCarryItem(inv, name, count)` - check capacity
    before you take payment or start an action.
  - `exports.ox_inventory:AddItem(inv, name, count, metadata, slot)` - returns
    success plus a reason; honor a `false`.
  - `exports.ox_inventory:RemoveItem(inv, name, count, metadata, slot)`.
  - `exports.ox_inventory:GetItem(inv, name, metadata, returnsCount)` - read the
    real count server-side; never trust a client-reported amount.
- Capacity-check, then take payment, then grant; refund in the same path if the
  grant fails. `CanCarryItem` false before `AddItem` avoids money leaving the
  player with no item arriving.
- Item names come from the server item list or your config, never from the
  client payload directly - look the name up in your own index first.

## Hooks Are The Anti-Dupe Boundary

ox_inventory fires server-side hooks around the actions a cheater abuses. A hook
is the sanctioned place to reject a move before it happens - register one
instead of trying to police inventory from outside.

- Register with `exports.ox_inventory:registerHook(event, cb, options)`; it
  returns a `hookId`, and hooks are cleared for your resource on
  `onResourceStop`. The events are `swapItems`, `buyItem`, `craftItem`,
  `createItem`, `usingItem`, `openInventory`, and `openShop`.
- The callback receives a payload describing the action (for `swapItems`:
  `source`, `fromInventory`, `fromSlot`, `fromType`, `toInventory`, `toSlot`,
  `toType`, `count`, `action`). **Return `false` to cancel the action** - that
  is how you block a disallowed move, a cross-inventory dupe, or an out-of-range
  transfer. Narrow which calls fire your hook with `options` (for example
  `itemFilter`, `inventoryFilter`) so the hook stays cheap.
- The hook runs on the server with the real inventory state, so it is the place
  to enforce rules a client cannot be trusted with: distance between the two
  inventories, whether this player may open that stash, job/gang gating on a
  shop, a per-item transfer cap.

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

- Register stashes and shops on the server (`RegisterStash`, `RegisterShop` /
  the `data/shops.lua` and `data/stashes.lua` definitions), not from a client
  request. A client that can ask the server to create or open an arbitrary
  stash id can reach another player's or another job's storage.
- Gate access with the stash's `groups`/`jobs` and with a server-side distance
  and ownership check in a hook; do not rely on the client only showing the UI.
- Shop prices and stock live in the shop definition, server-side. A `buyItem`
  hook is where you add dynamic pricing or purchase limits - never trust a price
  or quantity from the client.

## ox_target Is Client-Side UX - Re-Validate On The Server

ox_target draws the interaction and decides locally whether an option shows.
Everything it runs is on the attacker's machine.

- Option fields `canInteract`, `onSelect`, `distance`, and `event`/`serverEvent`
  all evaluate client-side. `canInteract` returning false only hides the
  option; it is not a security control.
- Any server effect a target option triggers (a `serverEvent`, a callback)
  must re-validate on the server: the player's distance to the entity/coords,
  ownership or job, cooldown, and that the entity or net ID is real
  (`skills/common/security-performance.md` -> Entity And Net ID Validation).
  Treat a
  target `serverEvent` exactly like any `:server:` event
  (`skills/common/security-performance.md` -> Event Trust Boundary).
- Add and remove options by a stable name so a resource restart does not leave
  duplicate or orphaned interactions; remove them on `onResourceStop`.
- Keep `canInteract`/`onSelect` cheap - they run during targeting; no server
  round-trips or heavy scans inside them.

## Review Questions

- Does the resource mutate ox_inventory through its exports, or does it write
  item state in parallel somewhere?
- Is capacity checked before payment, and is a failed grant refunded in the same
  path?
- Is a dupe- or access-sensitive action enforced in a `registerHook` that
  returns `false`, rather than policed after the fact?
- Are stashes and shops registered server-side with group/distance gating, not
  opened from a client-supplied id?
- Does every ox_target `serverEvent`/callback re-check distance, ownership, and
  the entity server-side, instead of trusting that the option was shown?
