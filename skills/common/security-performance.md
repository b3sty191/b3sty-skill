# Security And Performance Rules

For RedM/FiveM resources touching player input, server state, entities, database writes, callbacks, or loops.

## Contents

This file: Priority, Event Trust Boundary, Server Authority, Server Event Validation, Network Exposure, Commands/Exports/Public Interfaces, Required Event Pattern, Throttle And Cooldown, Callback Safety, Client Requests, Atomic State Changes And Replay Protection, Database And Persistence, Identifier Trust.

Split files - open only what the task touches. Headings are unchanged, so an "above"/"below" pointer to a section not here resolves to the file listed:

- `skills/common/give-value-hardening.md` -> Give-Value Event Hardening, ACE Permissions And Admin Authority, Abuse Handling.
- `skills/common/client-input-validation.md` -> Sync Safety, NUI Callback Hardening, Entity And Net ID Validation, Built-in Client Events, Position And Interaction Checks.
- `skills/common/server-hardening.md` -> Config, Convars, And Secrets, Logging And Secrets, Server Hardening And Operations (convar checklist, operator access, HTTP handlers, database and supply chain, The Resource Sandbox).
- `skills/common/performance.md` -> Performance Rules, Cleanup, Anti-Overengineering.
- `skills/common/review-questions.md` -> Review Questions.

## Priority

- **The client is always hostile; the server is the only authority.** A modded client can fire any registered net event with arbitrary arguments; every value from a client is attacker-controlled until proven otherwise.
- Security and performance are core requirements, not cleanup tasks.
- b3sty style (direct, readable, hardcode-friendly) is fine, never at the cost of validation or runtime cost.
- Checks stay direct and local - no framework or generic layer around them.

## Event Trust Boundary

Principles: [Secure your events](https://docs.fivem.net/docs/developers/server-security/).

- `RegisterNetEvent` makes an event network-callable: any client can `TriggerServerEvent(name, ...)` it with arbitrary arguments, whatever the intended caller. Every registered net event is a public, attacker-callable endpoint. ([RegisterNetEvent](https://docs.fivem.net/docs/scripting-reference/runtimes/lua/functions/RegisterNetEvent/))
- `RegisterServerEvent` is the deprecated form of the same thing; use `RegisterNetEvent` in new code. ([cfx-server-data PR #204](https://github.com/citizenfx/cfx-server-data/pull/204))
- `AddEventHandler` is same-context only (client-to-client, server-to-server), unreachable from the opposing side: use it for logic clients must not be able to call.
- `RegisterNetEvent` does not block same-context execution: a server-side `TriggerEvent` reaches the handler with `source == ""` (empty string) ([scheduler.lua](https://github.com/citizenfx/fivem/blob/master/data/shared/citizen/scripting/lua/scheduler.lua)), client-triggered events always carry a numeric `source`. Guard client-only handlers with `if type(source) ~= "number" or source <= 0 then return end`. (*Client-side* handlers see `source == 65535` for server-sent events; there use `if source ~= 65535 then return end` to accept only those.)
- Identity is the implicit `source` (capture `local source = source` before any yield), never a player ID, target, or identifier field from the payload. See `skills/common/runtime.md` -> The `source` Variable and Identifier Trust below.
- The naive shop handler - `function(item, price)` doing `player.addMoney(-price)` then `player.addItem(item)` - is a direct dupe: the client picks the recipient, the item (no catalog check), and a negative `price` that *raises* its money. The hardened, race-safe template (identity from `source`, item/price from a server-side catalog, quantity a clamped positive integer, affordability from the server-held balance at transaction time, atomic debit+grant) is in Give-Value Event Hardening; use it instead of re-deriving it per resource.

## Server Authority

- The server owns money, items, jobs, groups, permissions, ownership, rewards, cooldowns, and saved player data; read jobs, groups, licenses, ownership, balances, inventory, and permission state from server-side framework/state only.
- Client-provided permission, job, group, ownership, balance, and inventory values are display hints and must not decide access.
- Client code may request an action, render UI, play effects, attach objects, or apply optimistic local state; the server validates and accepts or rejects, and optimistic client state must roll back on rejection.

## Server Event Validation

Every custom `:server:` event checks all of this before doing work:

- `source`: a number, `> 0`, a real player, whenever the event depends on one.
- Types: `type(...)` of every field used. Reject unexpected types instead of coercing - a table where a string was expected ends the handler, it does not get `tostring`-ed into something usable.
- Numbers: `tonumber` plus explicit min/max bounds; reject `NaN`, negatives, and non-integer quantities (`x % 1 ~= 0`) instead of flooring them.
- Strings: bounded (`#s <= N` length cap) before comparing, storing, logging, or writing to the database; reject empty strings and invalid keys.
- Names: item/action/job/weapon/config keys resolved against server-side config or indexes; unknown item, job, weapon, or config name = reject.
- Values: never a client-provided price, reward amount, inventory count, permission group, job, target ownership, or cooldown state.
- Tables: msgpack allows huge and deeply nested payloads, so cap key count and nesting depth before iterating, `json.encode`-ing, forwarding, or storing one, and reject oversized payloads instead of silently truncating. `pcall` any `json.decode` of a client string; a decode failure is hostile input.

## Network Exposure

- `RegisterNetEvent` only for handlers clients or other resources may call; internal server logic stays in local functions or non-networked handlers called from validated network handlers.
- No generic public dispatchers that call arbitrary actions, functions, exports, or config keys from a client-provided string.
- Avoid `TriggerClientEvent(name, -1)` broadcasts for targeted or frequent data: send to one player or a server-computed recipient set, and prefer state bags for replicated visible state. Full OneSync mechanics in `skills/common/networking.md`.
- A handler meant only for another server resource: document that contract and still validate the payload at the boundary.
- `SetHttpHandler` endpoints are public internet-reachable input, not resource-internal plumbing; harden them like net events (see Server Hardening And Operations below).

## Commands, Exports, And Public Interfaces

- Commands, exports, framework callbacks, and NUI callbacks are public input boundaries: validate command args, callback payloads, export params, and any `source` argument before doing work, and never let them bypass the validation of the matching server event.
- Server commands touching players, money, inventory, jobs, permissions, entities, or saved state check permission server-side.
- A public export taking a player `source` verifies it is a real player allowed to perform the action.

## Required Event Pattern

```lua
local Controller = {
    ["ActionThrottle"] = {},
    ["ItemIndex"] = Items["INDEX"],
    ["ItemList"] = Items["LIST"],
}

function Controller:IsActionThrottled(source, key, limit)
    local now = GetGameTimer()
    local throttle = self.ActionThrottle[source]
    if not throttle then throttle = {}; self.ActionThrottle[source] = throttle end
    if now - (throttle[key] or 0) < limit then return true end
    throttle[key] = now
    return false
end

RegisterNetEvent("resource_name:server:action", function(payload)
    local source = source
    if type(source) ~= "number" or source <= 0 then return end   -- "" = server-side TriggerEvent
    if type(payload) ~= "table" then return end
    if Controller:IsActionThrottled(source, "action", 500) then return end

    local itemName = payload["Item"]
    local amount = tonumber(payload["Amount"])
    if type(itemName) ~= "string" or itemName == "" then return end
    if not amount or amount ~= amount then return end            -- non-numeric / NaN
    if amount % 1 ~= 0 then return end                           -- reject non-integers
    if amount <= 0 or amount > 100 then return end               -- positive, bounded

    local itemIndex = Controller.ItemIndex[itemName]
    local itemData = itemIndex and Controller.ItemList[itemIndex]
    if not itemData then return end

    -- permission, ownership, cooldown, and action checks go here
end)

AddEventHandler("playerDropped", function()
    local source = source
    if source then Controller.ActionThrottle[source] = nil end
end)
```

## Throttle And Cooldown

- Throttle server-side every event that can be spammed: per-player tables for general actions, per-player per-key when one event updates several keys. Clean them on `playerDropped`.
- Typical floors: `50ms` only for low-cost coalesced state updates expected to be frequent; `250-500ms` for normal public server events and deliberate player actions such as item use; `1000ms+` for heavy rewards, crafting, database, or webhook actions.

## Callback Safety

- Validate callback names and IDs; rate-limit per player and callback name.
- Store pending callbacks by ID plus a reverse index (`pendingByTarget[source][id] = true`) so cleanup is O(1) per player instead of scanning all pending callbacks.
- Verify a callback response comes from the original target player.
- Expire stale pending callbacks on a timer; clear a player's on `playerDropped`.
- `pcall` callback handlers when third-party handlers can throw.

## Client Requests

- NUI callbacks and client events are untrusted input; client-side checks are UX only, never security.
- Client-sent coordinates, entity IDs, weapon data, and status values are validated against server-side state or reasonable bounds; position snapshots additionally against server position, snapshot age, and a distance threshold.

## Atomic State Changes And Replay Protection

- Check and mutate valuable state in one server-side flow for purchases, crafting, rewards, item transfers, payments, and ownership changes. Never check a balance, inventory item, or cooldown and then delay before mutating unless the state is reserved or rechecked.
- Use whatever fits the resource: framework API, database transaction, conditional update, lock, or per-player in-flight flag.
- Reward, claim, crafting, payment, and transfer actions that can be replayed need request IDs, claim state, or server-side in-flight markers. Cooldowns reduce spam but are not enough for high-value actions: reject duplicate requests before granting rewards or writing saved state.
- Make retry behavior explicit so a failed request cannot grant twice and a successful one is recognized if the client retries.
- Classic dupe patterns to refuse by design: check-balance -> `Wait` -> mutate (a flood lands multiple debits/grants); grant in RAM before the DB commit, then lose the race; accept a negative amount in a transfer; trust a client-reported count. The concrete race-safe flow is in Give-Value Event Hardening above.

## Database And Persistence

- Parameterized SQL only; never concatenate player input into SQL (see SQL Injection below).
- Track dirty fields for large player data, saving only changed JSON fields when possible.
- Debounce autosaves instead of writing on every small mutation, use retry windows for failed saves, never write to the database every tick or every client update, and force-save dirty player state on resource stop or player drop.
- Never decide *whether* to save a player from a client-sent lifecycle flag (`spawned` / `esx:onPlayerSpawn`): a modified client that never sends it is never saved while its trade partner is, which is a dupe. Save every loaded player, substituting only the ped-derived fields (position, health, armour) with the loaded values until the spawn event arrives or a server grace period (60 s) passes - that also stops a client freezing its health by withholding the event. (verified: offline regression test with a never-spawning player)
- `memory/common/cfx-patterns.md` -> Player Persistence Pattern has a concrete RAM-cache + spread-autosave + force-save shape.

### SQL Injection

oxmysql binds `?` (or `@name`) parameters safely; the engine never treats a bound value as SQL. Concatenating a string into the query lets a single quote break out and run arbitrary SQL. ([oxmysql](https://overextended.dev/docs/oxmysql))

```lua
-- BAD: a player sends item = "x'; DROP TABLE inventory; --"
RegisterNetEvent("shop:log", function(item)
    local src = source
    MySQL.query("INSERT INTO logs (item) VALUES ('" .. item .. "')")   -- SQL injection
end)
```

```lua
-- GOOD: bounded string, then a bound ? placeholder; item is data, never SQL
RegisterNetEvent("shop:log", function(item)
    local src = source
    if type(item) ~= "string" or item == "" or #item > 64 then return end
    MySQL.insert.await("INSERT INTO logs (item) VALUES (?)", { item })
end)
```

- Same rule for dynamic table/column/identifier names: bind values with `?`/`@name`, and pick any dynamic identifier from a server-side allowlist - never splice client input into the SQL text.
- Wrap multi-step valuable writes in one `MySQL.transaction.await({ ... })` so they commit together or not at all ([oxmysql transaction](https://overextended.dev/docs/oxmysql/Functions/transaction)). A transaction rolls back only on an SQL error: a conditional `UPDATE` matching 0 rows does not abort it, so check the debit's affected row count before granting (see Give-Value Event Hardening). Full SQL rules and API shape in `skills/common/database.md`.

## Identifier Trust

- Identity is reliable only server-side, from `GetPlayerIdentifiers(source)` ([GetPlayerIdentifiers](https://docs.fivem.net/docs/scripting-reference/runtimes/lua/functions/GetPlayerIdentifiers/)) or `GetPlayerIdentifierByType`. A client-reported identifier is attacker input, not identity.
- Types returned: `steam` (hex), `discord` (int), `license`/`license2` (ROS hash - `license2` can equal `license` for Steam users), `fivem` (Cfx user id), `ip` (IPv4 string). `xbl:` and `live:` were retired in April 2026 (Cfx deprecation notice; the client dropped Xbox identities in citizenfx/fivem `b145ad1`) - never key data on them. From 2026-06-24 the Account Security Update gives some players a new `license:`/`license2:`; a player can set an older linked identity back as default (Cfx support). Store every identifier a player connects with next to your account key, so a changed license can be matched through `steam`/`discord`/`fivem` and migrated instead of creating a fresh account.
- Never trust one identifier type in isolation. Ban/whitelist on the strongest available (prefer `license2`, else `license`; for bans store every returned identifier plus `GetPlayerToken` hardware tokens rather than a single type) and treat `ip` as the weakest (shared NAT, rotates). Keep an existing DB key scheme stable when migrating to `license2`.
- Of the connect-time trust convars ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/)), only `sv_authMaxVariance` (1-5, default 5) has an effect: FXServer compares it against the lowest variance among a player's identifiers (`license`/`steam` = 1, `ip` = 5), so any value below 5 rejects players with no `license`/`steam` identifier. `sv_authMinTrust` is effectively a no-op, because the always-present `ip:` identifier reports trust 5. See `skills/common/runtime.md` -> Players And Identifiers.
- Run ban/whitelist lookups during `playerConnecting` through the `deferrals` API (defer, do async checks, call `done()` exactly once), not after the player is in-game.
- The recipient/target of a value is always `source` resolved to its identifiers server-side, never a payload field (see Event Trust Boundary and Give-Value Event Hardening).
