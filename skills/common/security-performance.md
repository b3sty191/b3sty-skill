# Security And Performance Rules

Use these rules for RedM/FiveM resources where player input, server state, entities, database writes, callbacks, or loops are involved.

## Contents

This file: Priority, Event Trust Boundary, Server Authority, Server Event Validation, Network Exposure, Commands/Exports/Public Interfaces, Required Event Pattern, Throttle And Cooldown, Callback Safety, Client Requests, Atomic State Changes And Replay Protection, Database And Persistence, Identifier Trust.

Split files - open only the ones the task touches. Headings are unchanged, so an "above"/"below" pointer to a section that is not in this file resolves to the file listed here.

- `skills/common/give-value-hardening.md` -> Give-Value Event Hardening, ACE Permissions And Admin Authority, Abuse Handling.
- `skills/common/client-input-validation.md` -> Sync Safety, NUI Callback Hardening, Entity And Net ID Validation, Built-in Client Events, Position And Interaction Checks.
- `skills/common/server-hardening.md` -> Config, Convars, And Secrets, Logging And Secrets, Server Hardening And Operations (convar checklist, operator access, HTTP handlers, database and supply chain, The Resource Sandbox).
- `skills/common/performance.md` -> Performance Rules, Cleanup, Anti-Overengineering.
- `skills/common/review-questions.md` -> Review Questions.

## Priority

- **The client is always hostile; the server is the only authority.** Every section below assumes a modded client can fire any registered net event with arbitrary arguments, and that any value received from a client is attacker-controlled until proven otherwise.
- Security and performance are core requirements, not cleanup tasks.
- Keep the b3sty style: direct, readable, hardcode-friendly code is fine, but do not sacrifice validation or runtime cost.
- Keep security/performance checks direct and local; do not build a framework or generic layer around them.

## Event Trust Boundary

- `RegisterNetEvent` marks an event as network-callable. Any client can trigger it with `TriggerServerEvent(name, ...)` and arbitrary arguments, whether or not your UI is the intended caller. Treat every registered net event as a public, attacker-callable endpoint. ([RegisterNetEvent](https://docs.fivem.net/docs/scripting-reference/runtimes/lua/functions/RegisterNetEvent/), [Secure your events](https://docs.fivem.net/docs/developers/server-security/))
- `RegisterServerEvent` is the deprecated form and does the same thing; use `RegisterNetEvent` in new code. ([cfx-server-data PR #204](https://github.com/citizenfx/cfx-server-data/pull/204))
- `AddEventHandler` is same-context only (client-to-client or server-to-server) and is not network-reachable from the opposing side. Use it for internal logic that must not be callable by clients. ([Secure your events](https://docs.fivem.net/docs/developers/server-security/))
- `RegisterNetEvent` does not block same-context execution. On the server, a same-context `TriggerEvent` reaches a `RegisterNetEvent` handler with `source == ""` (empty string) ([scheduler.lua](https://github.com/citizenfx/fivem/blob/master/data/shared/citizen/scripting/lua/scheduler.lua)). Client-triggered events always carry a numeric `source`. Guard with `if type(source) ~= "number" or source <= 0 then return end` in handlers that must only run when a real client triggered them. (`65535` is the `source` that *client-side* handlers see for events sent by the server; use `if source ~= 65535 then return end` there to accept only server-sent events.) ([Secure your events](https://docs.fivem.net/docs/developers/server-security/))
- Always read identity from the implicit `source` (capture `local source = source` before any yield). Never trust a player ID, target, or identifier field from the payload. See `skills/common/runtime.md` -> The `source` Variable and Identifier Trust below.
- Validate `source` (a number, `> 0`, and a real player), then `type(...)` and bounds for every field, before doing work.

### Naive vs hardened handler

Vulnerable - the client controls the recipient, the item, and the amount:

```lua
-- BAD: client controls who gets what, and how much
RegisterNetEvent("shop:server:buy", function(item, price)
    local src = source
    local player = Framework.GetPlayer(src)
    player.addMoney(-price)       -- client-chosen "price" can be negative
    player.addItem(item)          -- client-chosen item; no catalog check
end)
```

- The vulnerable version is a direct dupe: a client passes a negative `price` (money goes up) or an item it should never receive.
- The hardened shape: identity from `source` only, item/price resolved from a server-side catalog, quantity clamped to a positive bounded integer, affordability read from server-held balance at transaction time, and the debit+grant made atomic. The full, race-safe version is in Give-Value Event Hardening below (it builds on the server-authority principles in CFX's [Secure your events](https://docs.fivem.net/docs/developers/server-security/) guide); use that as the template instead of re-deriving it per resource.



## Server Authority

- The server must be the source of truth for money, items, jobs, groups, permissions, ownership, rewards, cooldowns, and saved player data.
- Read jobs, groups, licenses, ownership, balances, inventory, and permission state from server-side framework/state only.
- Client code may request an action, render UI, play effects, attach objects, or apply optimistic local state.
- Client-provided permission, job, group, ownership, balance, or inventory values are display hints only and must not decide access.
- Server code must validate and either accept or reject the requested action.
- If client code applies optimistic state, it must support rollback when the server rejects the request.

## Server Event Validation

- Every custom `:server:` event must validate its payload before doing work.
- Validate `source` when the event depends on a real player.
- Validate `type(...)` for every field used by the event.
- Normalize numbers with `tonumber` and explicit min/max bounds; reject non-integer quantities (`x % 1 ~= 0`) instead of flooring them.
- Reject `NaN`, negative values, empty strings, invalid keys, unknown items, unknown jobs, unknown weapons, and unknown config names.
- Check requested item/action names against server-side config or indexes.
- Never trust client-provided price, reward amount, inventory count, permission group, job, target ownership, or cooldown state.
- Bound every client string (`#s <= N` length cap) before comparing, storing, logging, or writing it to the database.
- A hostile client can send huge or deeply nested tables (msgpack allows it). Cap key count and nesting depth before iterating, `json.encode`-ing, forwarding, or storing a payload table; reject oversized payloads, do not truncate them silently.
- Wrap `json.decode` of client-supplied strings in `pcall` and treat a decode failure as hostile input.
- Reject unexpected types instead of coercing them: a table where a string was expected ends the handler, it does not get `tostring`-ed into something usable.

## Network Exposure

- Use `RegisterNetEvent` only for handlers that clients or other resources are allowed to call.
- Treat every networked `:server:` event as client-callable, even when the current UI is the only intended caller.
- Keep internal server logic in local functions or non-networked handlers, then call it from validated network handlers.
- Do not create generic public dispatchers that call arbitrary actions, functions, exports, or config keys from a client-provided string.
- Avoid `TriggerClientEvent(name, -1)` broadcasts for targeted or frequent data. Send to a single player or a server-computed recipient set, and prefer state bags for replicated visible state. Full OneSync mechanics in `skills/common/networking.md`.
- If a handler is intended only for another server resource, document that contract and still validate the payload at the boundary.
- `SetHttpHandler` endpoints are public internet-reachable input, not resource-internal plumbing; harden them like net events (see Server Hardening And Operations below).

## Commands, Exports, And Public Interfaces

- Treat commands, exports, framework callbacks, and NUI callbacks as public input boundaries.
- Validate command args, callback payloads, export params, and any `source` argument before doing work.
- Server commands that affect players, money, inventory, jobs, permissions, entities, or saved state must check permission server-side.
- Public exports that accept a player `source` must verify that the source is a real player and is allowed to perform the action.
- Do not let an export or callback bypass the validation required for the matching server event.

## Required Event Pattern

```lua
local Controller = {
    ["ActionThrottle"] = {},
    ["ItemIndex"] = Items["INDEX"],
    ["ItemList"] = Items["LIST"],
}

function Controller:IsActionThrottled(source, key, limit)
    local now = GetGameTimer()
    local actionThrottle = self.ActionThrottle[source]

    if not actionThrottle then
        actionThrottle = {}
        self.ActionThrottle[source] = actionThrottle
    end

    if now - (actionThrottle[key] or 0) < limit then
        return true
    end

    actionThrottle[key] = now
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
    if not amount or amount ~= amount then return end

    if amount % 1 ~= 0 then return end
    if amount <= 0 or amount > 100 then return end

    local itemIndex = Controller.ItemIndex[itemName]
    local itemData = itemIndex and Controller.ItemList[itemIndex]
    if not itemData then return end

    -- permission, ownership, cooldown, and action checks go here
end)

AddEventHandler("playerDropped", function()
    local source = source

    if source then
        Controller.ActionThrottle[source] = nil
    end
end)
```

## Throttle And Cooldown

- Add server-side throttles for events that can be spammed.
- Use per-player throttle tables for general actions.
- Use per-player per-key throttles when one event updates multiple keys.
- Clean throttle/cooldown tables on `playerDropped`.
- Typical floors:
  - `50ms` only for low-cost, coalesced state updates that are expected to happen frequently.
  - `250-500ms` for normal public server events and deliberate player actions such as item use.
  - `1000ms+` for heavy rewards, crafting, database, or webhook actions.

## Callback Safety

- Validate callback names and IDs.
- Rate-limit callback requests per player and callback name.
- Store pending callbacks by ID.
- Also store a reverse index such as `pendingByTarget[source][id] = true` so cleanup is O(1) per player instead of scanning all pending callbacks.
- When receiving a client callback response, verify that the response comes from the original target player.
- Expire stale pending callbacks on a timer.
- Clear pending callbacks for a player on `playerDropped`.
- Run callback handlers with `pcall` when third-party handlers can throw.

## Client Requests

- NUI callbacks and client events must be treated as untrusted input.
- Client-side checks are only UX; they are not security.
- If a client sends coordinates, entity IDs, weapon data, or status values, the server must validate them against server-side state or reasonable bounds.
- For position snapshots, compare against server position, snapshot age, and a distance threshold before accepting.

## Atomic State Changes And Replay Protection

- Check and mutate valuable state in one server-side flow for purchases, crafting, rewards, item transfers, payments, and ownership changes.
- Do not check a balance, inventory item, or cooldown, then delay before applying the mutation unless the state is reserved or rechecked.
- Use the framework, database transaction, conditional update, lock, or per-player in-flight flag that best fits the resource.
- Add request IDs, claim state, or server-side in-flight markers for reward, claim, crafting, payment, and transfer actions that can be replayed.
- Cooldowns reduce spam but are not enough for high-value actions; reject duplicate requests before granting rewards or writing saved state.
- Make retry behavior explicit so a failed request cannot grant twice and a successful request can be recognized if the client retries.
- Classic dupe patterns to refuse by design: check-balance -> `Wait` -> mutate (a flood lands multiple debits/grants); grant in RAM before the DB commit then lose the race; accept a negative amount in a transfer; trusting a client-reported count. The concrete race-safe flow is in Give-Value Event Hardening above.

## Database And Persistence

- Use parameterized SQL queries only. Never concatenate player input into SQL (see SQL Injection below).
- Track dirty fields for large player data.
- Save only changed JSON fields when possible.
- Debounce autosaves instead of saving on every small mutation.
- Use retry windows for failed saves.
- On resource stop or player drop, force-save dirty player state.
- Do not run a database write every tick or every client update.
- Never decide *whether* to save a player from a client-sent lifecycle flag (`spawned` / `esx:onPlayerSpawn`): a modified client that never sends it is never saved while its trade partner is, which is a dupe. Save every loaded player, and only substitute the ped-derived fields (position, health, armour) with the loaded values until the spawn event arrives or a server grace period (60 s) passes - that also stops a client freezing its health by withholding the event. (verified: offline regression test with a never-spawning player)
- See `memory/common/cfx-patterns.md` -> Player Persistence Pattern for a concrete RAM-cache + spread-autosave + force-save shape.

### SQL Injection

oxmysql binds parameters safely with `?` (or `@name` named placeholders); the database engine never treats a bound value as SQL. Concatenating a string into the query lets a single quote break out and run arbitrary SQL. ([oxmysql](https://overextended.dev/docs/oxmysql))

Vulnerable - the item name is spliced into the query:

```lua
-- BAD: a player sends item = "x'; DROP TABLE inventory; --"
RegisterNetEvent("shop:log", function(item)
    local src = source
    MySQL.query("INSERT INTO logs (item) VALUES ('" .. item .. "')")  -- SQL injection
end)
```

Safe - the value is bound, not concatenated:

```lua
-- GOOD: the ? placeholder is bound by the engine; item is data, never SQL
RegisterNetEvent("shop:log", function(item)
    local src = source
    if type(item) ~= "string" or item == "" or #item > 64 then return end
    MySQL.insert.await("INSERT INTO logs (item) VALUES (?)", { item })
end)
```

- The same rule applies to dynamic table/column/identifier names: bind values with `?`/`@name`, and for any dynamic identifier choose from a server-side allowlist - never splice client input into the SQL text.
- For multi-step valuable writes, wrap the parameterized statements in one `MySQL.transaction.await({ ... })` so they commit together or not at all ([oxmysql transaction](https://overextended.dev/docs/oxmysql/Functions/transaction)). A transaction only rolls back on an SQL error: a conditional `UPDATE` that matches 0 rows does not abort it, so check the debit's affected row count before granting (see Give-Value Event Hardening). Full SQL rules and the API shape are in `skills/common/database.md`.

## Identifier Trust

- Player identity is only reliable server-side, from `GetPlayerIdentifiers(source)` ([GetPlayerIdentifiers](https://docs.fivem.net/docs/scripting-reference/runtimes/lua/functions/GetPlayerIdentifiers/)) or `GetPlayerIdentifierByType`. A client-reported identifier is attacker input, not identity.
- Identifier types returned: `steam` (hex), `discord` (int), `xbl` (int), `live` (Microsoft PUID), `license`/`license2` (ROS hash - `license2` can equal `license` for Steam users), `fivem` (Cfx user id), `ip` (IPv4 string).
- Do not trust a single identifier type in isolation. Ban/whitelist on the strongest available identifiers (prefer `license2` when present, else `license`; for bans, store every returned identifier plus `GetPlayerToken` hardware tokens rather than a single type), and treat `ip` as the weakest (shared NAT, rotates). Keep an existing DB key scheme stable when migrating to `license2`.
- Of the connect-time trust convars ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/)), only `sv_authMaxVariance` (1-5, default 5) has an effect: FXServer compares it against the lowest variance among a player's identifiers (`license`/`steam` = 1, `ip` = 5), so any value below 5 rejects players with no `license`/`steam` identifier. `sv_authMinTrust` is effectively a no-op, because the always-present `ip:` identifier reports trust 5. See `skills/common/runtime.md` -> Players And Identifiers.
- Run ban/whitelist lookups during `playerConnecting` using the `deferrals` API (defer, do async checks, call `done()` exactly once), not after the player is in-game.
- The recipient/target of a value is always `source` resolved to its identifiers server-side; never a payload field (see Event Trust Boundary and Give-Value Event Hardening).

