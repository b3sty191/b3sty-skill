# Security And Performance Rules

Use these rules for RedM/FiveM resources where player input, server state, entities, database writes, callbacks, or loops are involved.

## Contents

- Priority
- Server Authority
- Event Trust Boundary
- Server Event Validation
- Network Exposure
- Commands, Exports, And Public Interfaces
- ACE Permissions And Admin Authority
- Required Event Pattern
- Give-Value Event Hardening
- Throttle And Cooldown
- Callback Safety
- Sync Safety
- Client Requests
- NUI Callback Hardening
- Entity And Net ID Validation
- Built-in Client Events
- Position And Interaction Checks
- Atomic State Changes And Replay Protection
- Database And Persistence
- Config, Convars, And Secrets
- Identifier Trust
- Abuse Handling
- Logging And Secrets
- Server Hardening And Operations
- Performance Rules
- Cleanup
- Anti-Overengineering
- Review Questions

## Priority

- **The client is always hostile; the server is the only authority.** Every section below assumes a modded client can fire any registered net event with arbitrary arguments, and that any value received from a client is attacker-controlled until proven otherwise.
- Security and performance are core requirements, not cleanup tasks.
- Keep the b3sty style: direct, readable, hardcode-friendly code is fine, but do not sacrifice validation or runtime cost.
- Keep security/performance checks direct and local; do not build a framework or generic layer around them.

## Event Trust Boundary

- `RegisterNetEvent` marks an event as network-callable. Any client can trigger it with `TriggerServerEvent(name, ...)` and arbitrary arguments, whether or not your UI is the intended caller. Treat every registered net event as a public, attacker-callable endpoint. ([RegisterNetEvent](https://docs.fivem.net/docs/scripting-reference/runtimes/lua/functions/RegisterNetEvent/), [Secure your events](https://docs.fivem.net/docs/developers/server-security/))
- `RegisterServerEvent` is the deprecated form and does the same thing; use `RegisterNetEvent` in new code. ([cfx-server-data PR #204](https://github.com/citizenfx/cfx-server-data/pull/204))
- `AddEventHandler` is same-context only (client-to-client or server-to-server) and is not network-reachable from the opposing side. Use it for internal logic that must not be callable by clients. ([Secure your events](https://docs.fivem.net/docs/developers/server-security/))
- `RegisterNetEvent` does not block same-context execution. Server-originated net events arrive with `source == 65535`; reject that source in handlers that must only run when a real client triggered them. ([Secure your events](https://docs.fivem.net/docs/developers/server-security/))
- Always read identity from the implicit `source` (capture `local source = source` before any yield). Never trust a player ID, target, or identifier field from the payload. See `skills/common/runtime.md` -> The `source` Variable and Identifier Trust below.
- Validate `source` (`source > 0` and a real player), then `type(...)` and bounds for every field, before doing work.

### Naive vs hardened handler

Vulnerable - the client controls the recipient, the item, and the amount:

```lua
-- BAD: client controls who gets what, and how much
RegisterNetEvent("shop:buy", function(item, price)
    local src = source
    local player = Framework.GetPlayer(src)
    player.addMoney(-price)       -- client-chosen "price" can be negative
    player.addItem(item)          -- client-chosen item; no catalog check
end)
```

- The vulnerable version is a direct dupe: a client passes a negative `price` (money goes up) or an item it should never receive.
- The hardened shape: identity from `source` only, item/price resolved from a server-side catalog, quantity clamped to a positive bounded integer, affordability read from server-held balance at transaction time, and the debit+grant made atomic. The full, race-safe version - the canonical pattern from CFX's own [Secure your events](https://docs.fivem.net/docs/developers/server-security/) guide - is in Give-Value Event Hardening below; use that as the template instead of re-deriving it per resource.



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
- Normalize numbers with `tonumber`, `math.floor`, and explicit min/max bounds.
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

## ACE Permissions And Admin Authority

- Gate admin/sensitive actions behind FiveM's built-in ACL, not client-side flags or spoofable identifiers. `add_ace [principal] [object] [allow|deny]` grants a permission object; `add_principal [child] [parent]` makes an identifier inherit a group (e.g. `add_principal identifier.license:... group.admin`). ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/))
- Check access server-side with `IsPlayerAceAllowed(player, object)` (CFX native `0xDEDAE23D`, server API set), which resolves direct and inherited permissions. ([IsPlayerAceAllowed](https://docs.fivem.net/natives/?_0xDEDAE23D))
- Never gate by a client-side "am I admin" check, a client-sent `group`/`rank` field, or a `job` value the client can report freely. These are display hints, not authority (see Server Authority).
- Any "give money/item/perm to player X" command or export must be ACE-gated on the invoking `source`, must resolve the target `source` server-side, and must log who granted what to whom.
- Principals include `group.*` (e.g. `group.admin`), `identifier.license:...` / `identifier.steam:...`, `resource.<name>`, and `builtin.everyone`. Prefer grouping under `group.*` and assigning identifiers to groups.
- Test permission grants with `test_ace` (server console) before relying on them in code.

```lua
-- admin grant: ACE-gated on the caller, target resolved server-side, logged
RegisterCommand("giveitem", function(source, args)
    if source == 0 then return end                       -- block console rcon for this example
    if not IsPlayerAceAllowed(source, "command.giveitem") then return end

    local target = tonumber(args[1])                      -- server ID, validated below
    local itemName = args[2]
    local amount = math.floor(tonumber(args[3]) or 0)
    if not target or target <= 0 then return end
    if not GetPlayerName(target) then return end          -- target must be a real player
    if not itemName or amount <= 0 or amount > 1000 then return end

    local entry = Controller.Catalog[itemName]
    if not entry then return end

    Framework.GetPlayer(target):addItem(itemName, amount)
    print(("admin %s gave %sx %s to %s"):format(source, amount, itemName, target))
end, false)
```

- Do not use `GetPlayerIdentifiers(target)` as an existence check: it returns a table (truthy even when empty) for invalid IDs. Use `GetPlayerName(target)` or `DoesPlayerExist(target)` to confirm the target is a real connected player.
- Note: polling `IsPlayerAceAllowed` for every player on a tight timer has caused crashes (citizenfx/fivem#2547); check it on the action path, not in a per-player loop.

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
    if not source or source <= 0 then return end
    if type(payload) ~= "table" then return end

    if Controller:IsActionThrottled(source, "action", 500) then return end

    local itemName = payload["Item"]
    local amount = tonumber(payload["Amount"])

    if type(itemName) ~= "string" or itemName == "" then return end
    if not amount or amount ~= amount then return end

    amount = math.floor(amount)
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

## Give-Value Event Hardening

This is the highest-frequency exploit class in CFX servers: shop buys, payouts, crafting, quest rewards, drops, trades, admin grants. A client event may **request** an action; it must never specify the amount, the item, the price, or the recipient of anything of value. The server decides all of those from server-held state. (Canonical pattern: [Secure your events](https://docs.fivem.net/docs/developers/server-security/).)

### Vulnerable

```lua
-- BAD: client controls both the item and the price; recipient defaults to source but is never re-checked
RegisterNetEvent("shop:buy", function(item, price)
    local player = Framework.GetPlayer(source)
    player.removeMoney(price)     -- client-chosen price can be NEGATIVE -> money goes UP
    player.addItem(item)          -- client-chosen item, no catalog/ownership check, fixed count of 1
end)
```

A mod menu fires `TriggerServerEvent("shop:buy", "weapon_rpg", -1000000)` and gains money plus the item. Negative price or quantity is a classic dupe.

### Hardened, in order

1. **Identity = `source`, never the payload.** Reject `source <= 0`, `source == 65535` (server-originated), and any payload field that claims to be the recipient. A normal player must not grant items to an arbitrary ID; only an ACE-gated admin grant may target another player (see ACE Permissions And Admin Authority).
2. **Server-authoritative catalog.** Items, prices, weights, stack limits, and craft recipes live in server config/DB. The client sends at most an item key/id; the server maps it to real data and rejects unknown keys. Never accept `price` from the client.
3. **Validate every field before touching value.** Type, range, and existence checks on the item key and quantity first. Reject missing/extra fields as hostile.
4. **Quantity is a positive, bounded integer.** Reject `nil`, `NaN`, `0`, negatives, floats, and values above a sane max (`amount = math.floor(tonumber(x)); if not amount or amount ~= amount or amount <= 0 or amount > MAX then return end`). A negative amount in a transfer/remove path is a dupe.
5. **Affordability from fresh server state.** Re-read balance/inventory at the moment of the transaction, not a value cached from an earlier request. Reject if `balance < price * amount`.
6. **Debit + grant atomically.** The check-then-mutate must not be interruptible by the same player spamming the event. Use a per-source in-flight lock, or one atomic DB transaction; do not `Wait()` between the check and the mutation with shared state exposed.
7. **Rate-limit + idempotency.** Throttle per source. For one-shot grants (quest reward, daily claim), record server-side that it was claimed and reject repeats; never rely on the client not re-firing.
8. **Admin grants are ACE-gated and logged.** No client-side "admin" flag, no spoofable identifier (see ACE Permissions And Admin Authority).

```lua
local MAX_PER_PURCHASE = 100

local Controller = {
    ["Catalog"] = Items,            -- server-side: itemName -> { price, stack, purchasable }
    ["Throttle"] = {},
    ["InFlight"] = {},              -- per-source in-flight guard against spam-dupes
}

function Controller:IsThrottled(source, key, limit)
    local now = GetGameTimer()
    local t = self.Throttle[source]
    if not t then t = {}; self.Throttle[source] = t end
    if now - (t[key] or 0) < limit then return true end
    t[key] = now
    return false
end

RegisterNetEvent("shop:buy", function(payload)
    local source = source
    if not source or source <= 0 or source == 65535 then return end
    if type(payload) ~= "table" then return end
    if Controller:IsThrottled(source, "buy", 250) then return end

    -- (3) field validation first
    local itemName = payload["Item"]
    local amount = tonumber(payload["Amount"])
    if type(itemName) ~= "string" or itemName == "" then return end
    if not amount or amount ~= amount then return end          -- NaN
    amount = math.floor(amount)
    if amount <= 0 or amount > MAX_PER_PURCHASE then return end  -- (4) positive bounded int

    -- (2) server catalog; reject unknown / unpurchasable
    local entry = Controller.Catalog[itemName]
    if not entry or not entry.purchasable then return end

    local player = Framework.GetPlayer(source)                 -- (1) identity = source
    if not player then return end

    -- (6) atomic: hold an in-flight lock so a flood cannot interleave check/mutate
    if Controller.InFlight[source] then return end
    Controller.InFlight[source] = true

    -- (5) affordability against the current server-held balance
    local cost = entry.price * amount
    if player.getMoney() < cost then
        Controller.InFlight[source] = nil
        return
    end

    -- DB-backed economy: one atomic transaction commits debit + grant, or neither
    local ok = MySQL.transaction.await({
        { query = "UPDATE characters SET money = money - ? WHERE owner = ? AND money >= ?",
          values = { cost, player.identifier, cost } },
        { query = "INSERT INTO inventory (owner, item, count) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE count = count + ?",
          values = { player.identifier, itemName, amount, amount } },
    })                                                          -- returns false if either fails (oxmysql transaction)
    if not ok then
        Controller.InFlight[source] = nil
        return                                                  -- keep state consistent, do not grant in RAM
    end

    -- the await yielded: the player may have dropped, and server IDs are recycled,
    -- so `source` can already belong to a different player. Re-resolve and compare
    -- identity before touching RAM; the DB commit above is correct either way.
    local current = Framework.GetPlayer(source)
    if current and current.identifier == player.identifier then
        current.setMoney(current.getMoney() - cost)
        current.addItem(itemName, amount)
    end
    Controller.InFlight[source] = nil
end)

AddEventHandler("playerDropped", function()
    local source = source
    if source then
        Controller.Throttle[source] = nil
        Controller.InFlight[source] = nil
    end
end)
```

- `MySQL.transaction.await` runs the queries in one transaction and commits only if all succeed; a `false` return means rolled back - treat it as a rejected mutation ([oxmysql transaction](https://overextended.dev/docs/oxmysql/Functions/transaction)). `?` placeholders are mandatory; see Database And Persistence and `skills/common/database.md`.
- Every `.await` is a yield. After it resumes, re-validate the player before applying RAM state: FXServer recycles server IDs, so a `source` captured before the yield can point at a *different* player after a drop + reconnect. Compare a pre-yield identifier against the current one, never just the source number. See `skills/common/runtime.md` -> The `source` Variable.
- The `UPDATE ... AND money >= ?` conditional acts as a server-side lock: if two buy requests race, only the one that still satisfies the balance commits.

### Give-value event checklist

Apply to every handler that grants, removes, transfers, prices, or pays anything of value:

1. Identity = `source` only; reject `0`/`65535` and any payload recipient.
2. Item/price/limits = server catalog, never the payload.
3. Quantity = positive bounded integer; reject 0/negative/float/NaN.
4. Afford check against a freshly read server-held balance.
5. Debit + grant atomic; per-source in-flight lock or single transaction.
6. Rate-limited; one-shot grants tracked server-side (idempotent).
7. Admin grants ACE-gated (`IsPlayerAceAllowed`) and logged.

Related: Atomic State Changes And Replay Protection below, ACE Permissions And Admin Authority above, and economy-specific dupe notes in `skills/common/networking.md` -> Creating Networked Entities (loot/pickup ownership).

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

## Sync Safety

- State bags are fine for visual state, but important state must be changed server-side.
- Prefer enabling `setr sv_stateBagStrictMode true` in server config when the target artifact supports it.
- With strict state bag mode enabled, only the server can modify networked entity and player state bags; clients should request changes through validated server events/callbacks.
- Client-side non-replicated entity state is still local client state and must not be used as authoritative replicated state.
- Clients may still read state bags and react with `AddStateBagChangeHandler`.
- Audit dependencies before enabling strict mode because resources that set replicated state from the client must be moved server-side.
- For custom sync events, prefer sequence numbers to reject old packets.
- When spoofing would matter for client-side local sync, add a per-player sync secret/signature and reject messages with invalid signatures.
- Treat client-held sync secrets as tamper resistance only, not real server-side security.
- The server must never trust a client action just because it includes a client-visible secret/signature.
- Keep sync payloads small; do not send full player data when only one field changed.
- Do not send secrets, tokens, webhooks, or private config to clients.

## Client Requests

- NUI callbacks and client events must be treated as untrusted input.
- Client-side checks are only UX; they are not security.
- If a client sends coordinates, entity IDs, weapon data, or status values, the server must validate them against server-side state or reasonable bounds.
- For position snapshots, compare against server position, snapshot age, and a distance threshold before accepting.

## NUI Callback Hardening

- A `RegisterNUICallback` handler receives fully untrusted input. The browser can be devtooled or scripted, so a NUI callback is exactly as hostile as any client `:server:` event. Validate the schema (type, range, existence) before the payload drives behavior or is forwarded to the server. Full bridge mechanics in `skills/common/nui.md`.
- Never round-trip authority through NUI. The UI must not be the thing that decides money, items, permissions, or access - it only requests them. Forward valuable actions to a validated `:server:` event and let the server decide.
- Never grant money/items/permissions directly from a NUI response. A `cb({ success = true })` is a display signal, not a grant. Grants happen server-side (see Give-Value Event Hardening).
- The recipient of any value is still `source`; do not let a NUI payload pick a target player.
- Treat a NUI callback like the naive handler in Event Trust Boundary: same field validation, same bounds, same throttle.

## Entity And Net ID Validation

- Treat client-provided entity handles, net IDs, vehicle IDs, object IDs, and ped IDs as untrusted.
- Validate that the entity exists before using it.
- Validate entity type, model, owner, routing bucket, health/alive state, and distance when those fields matter to the action.
- Prefer checking against a server-owned spawned entity registry or server-side state instead of accepting arbitrary world entities.
- Do not trust a client claim that an entity belongs to them, is nearby, is empty, is damaged, or is eligible for a reward.
- For destructive or valuable actions, reject entities that are not server-created, not in the expected registry, or not owned/controlled by the expected player.
- Entity ownership migrates between clients; treat a recovered owner (`NetworkGetEntityOwner`) as momentary, not permanent. Spawn requests, loot/pickup claims, and ownership migration are attack surfaces - validate against a server-side registry before trusting entity state. See `skills/common/networking.md` -> Entity Ownership and Creating Networked Entities.

## Built-in Client Events

The game/OneSync routes client->server events that attackers use as free exploit surfaces. Treat every one as attacker-callable with attacker-chosen fields. ([server-events](https://docs.fivem.net/docs/scripting-reference/events/server-events/), [Secure your events](https://docs.fivem.net/docs/developers/server-security/))

- Documented core events: `weaponDamageEvent(sender, data)`, `startProjectileEvent(sender, data)`, `ptFxEvent(sender, data)`, `removeAllWeaponsEvent(sender, data)` (full fields in the [server-events reference](https://docs.fivem.net/docs/scripting-reference/events/server-events/)). `data.weaponType` on `weaponDamageEvent` has carried incorrect hashes (citizenfx/fivem#3827) - validate against server-side weapon/entity state, not the field alone.
- `explosionEvent` is interceptable server-side with OneSync: register `AddEventHandler('explosionEvent', function(sender, ev) ...)` and inspect `ev` (`explosionType`, `posX/Y/Z`, `damageScale`, `ownerNetId`, ...). `CancelEvent()` here stops the server from routing the explosion to other clients - the documented mitigation. ([cookbook](https://docs.fivem.net/docs/cookbook/2019/08/19/onesync-intercepting-game-events-such-as-explosions/))
- `CancelEvent()` does not stop other handlers for the same event, and for some game events (e.g. `weaponDamageEvent`, see citizenfx/fivem#2395) cancellation does not reliably sync to clients. Do not rely on cancel as your only control for damage that may already have applied; validate the outcome server-side.
- `sender` is the reporting player. Never let `sender`-controlled fields (weapon hash, damage amount, target entity, owner net ID) grant money, items, kills, or eligibility.
- Prefer the built-in server controls over hand-rolled filters for networked-event abuse: `sv_filterRequestControl` (blocks `REQUEST_CONTROL_EVENT` routing - the main entity-control/explosion-by-proxy vector), `sv_enableNetworkedPhoneExplosions` (off by default), `sv_enableNetworkedSounds`, `sv_enableNetworkedScriptEntityStates`, and `block_net_game_event "EVENT_NAME"` for a specific net game event. ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/))
- Bound and rate-limit per `sender` (particles, projectiles, explosions). Reject, cancel, or log; do not auto-punish a player on a single unverified event.

```lua
-- intercept explosions; rate-limit per sender; cancel routing of bad explosions
local lastExplosion = {}

AddEventHandler("explosionEvent", function(sender, ev)
    if not sender or sender <= 0 then return end
    local now = GetGameTimer()
    if now - (lastExplosion[sender] or 0) < 250 then     -- flood: stop relaying
        CancelEvent()
        return
    end
    lastExplosion[sender] = now

    if ev.damageScale > 1.0 then                          -- server rule, not the client's claim
        CancelEvent()
    end
end)

AddEventHandler("playerDropped", function()
    lastExplosion[source] = nil                           -- per-player tables always clean up on drop
end)
```

- Full OneSync context (ownership, routing buckets, `entityCreating`/`CancelEvent` to reject entity creation) is in `skills/common/networking.md` -> Built-in Client Events and Entity Lifecycle Events.

## Position And Interaction Checks

- Treat client coordinates as hints; never use them alone to award money, items, progress, or access.
- For shops, crafting, rewards, gathering, storage, doors, and interactions, compare the player's server-side position to server-side config coordinates.
- Use explicit max-distance checks and reject requests outside the allowed radius.
- For delayed interactions, check that the player is still valid, alive when required, and near the target before applying the result.
- When accepting position snapshots, reject stale snapshots and movement that exceeds reasonable distance or speed thresholds.

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
- For multi-step valuable writes, wrap the parameterized statements in one `MySQL.transaction.await({ ... })` so they commit together or not at all ([oxmysql transaction](https://overextended.dev/docs/oxmysql/Functions/transaction)). Full SQL rules and the API shape are in `skills/common/database.md`.

## Config, Convars, And Secrets

- Treat shared and client config as public data. Anything reachable by a client is public - clients can read `config.lua`, `ui_page` bundles, state bags, and networked tables.
- Do not put webhook URLs, API keys, DB connection strings, admin secrets, or hidden reward logic in shared/client files.
- Convar exposure by command ([convars reference](https://docs.fivem.net/docs/scripting-reference/convars/)):
  - `set name value` - standard convar, server-side only; clients cannot read it.
  - `setr name value` - server replicated; readable by clients via `GetConvar`, changeable only server-side. Anything in `setr` is public to clients.
  - `sets name "value"` - server information; exposed publicly in `info.json` and the server list. Never use `sets` for anything sensitive.
- Store secrets (DB strings, tokens, webhooks) in server-only `set` convars (or env), read once with `GetConvar`/`GetConvarInt`, never in `setr`/`sets`/shared/client files. See `skills/common/runtime.md` -> Convars.
- Keep authoritative prices, rewards, drop rates, permission gates, and item mutation rules in server config or validate them again server-side.
- Validate server events and exports even when they are intended for another local resource.
- Do not assume another resource is trusted just because it runs on the same server; validate public/shared interfaces at the boundary.
- For internal cross-resource APIs, prefer explicit exports with narrow params over generic event payloads that can trigger arbitrary behavior.

## Identifier Trust

- Player identity is only reliable server-side, from `GetPlayerIdentifiers(source)` ([GetPlayerIdentifiers](https://docs.fivem.net/docs/scripting-reference/runtimes/lua/functions/GetPlayerIdentifiers/)) or `GetPlayerIdentifierByType`. A client-reported identifier is attacker input, not identity.
- Identifier types returned: `steam` (hex), `discord` (int), `xbl` (int), `live` (Microsoft PUID), `license`/`license2` (ROS hash - `license2` can equal `license` for Steam users), `fivem` (Cfx user id), `ip` (IPv4 string).
- Do not trust a single identifier type in isolation. Ban/whitelist on the strongest available identifier(s) (commonly `license`), and treat `ip` as the weakest (shared NAT, rotates). Tune trust with `sv_authMinTrust` (1-5, how spoof-resistant) and `sv_authMaxVariance` (1-5, how stable per provider) ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/)).
- Run ban/whitelist lookups during `playerConnecting` using the `deferrals` API (defer, do async checks, call `done()` exactly once), not after the player is in-game.
- The recipient/target of a value is always `source` resolved to its identifiers server-side; never a payload field (see Event Trust Boundary and Give-Value Event Hardening).



## Abuse Handling

- Invalid input should usually be rejected and logged, not automatically punished.
- Log security-sensitive rejections with source, event/interface name, reason, and bounded key fields.
- Track repeated invalid calls per player/action when abuse response matters.
- Use counters, backoff, temporary ignore windows, or staff-visible alerts before escalating to kicks or bans.
- Do not let rejection logging become a spam path; rate-limit or batch abuse logs.
- Keep an append-only audit trail for value mutations: event name, actor `source` + identifier, target, item, amount, and balance after. Dupe response is a reconstruction problem - without a trail you cannot tell who to roll back or by how much.
- Add server-side sanity envelopes for the economy: alert when a player's money/item delta per time window exceeds a plausible ceiling. Envelopes catch the exploit you did not predict; alerts come before punishment.

## Logging And Secrets

- Log rejected security-sensitive actions with enough context to debug, but do not log secrets.
- Redact fields whose names include `password`, `secret`, `token`, `apikey`, `authorization`, `bearer`, `cookie`, `webhook`, or `licensekey`.
- Bound log payload depth, string length, item count, and key count.
- Queue and batch logs instead of sending a request per event.
- Cap queue size and drop or compact safely when the queue is too large.
- Store real tokens and webhook keys in server-only `set` convars (not `setr`/`sets`), never in client/shared files. See Config, Convars, And Secrets above.

## Server Hardening And Operations

Resource-level validation cannot compensate for a soft server platform. These are `server.cfg`/operator-level controls; they complement, never replace, the per-event rules above. ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/))

### Convar checklist

- `sv_scriptHookAllowed 0` - keep ScriptHook-style client plugins blocked (default off; never enable on a public server).
- `sv_pureLevel 1` (or `2`) - reject clients running modified game files; `2` is strictest. Test against your player base before enforcing.
- `sv_requestParanoia 1..3` - stricter handling of malicious client network requests; raise gradually and watch for false kicks.
- `sv_endpointPrivacy true` - hide player IPs from other clients (blocks player deanonymization/DDoS targeting).
- Leave `rcon_password` unset (rcon disabled) unless genuinely needed; if used, a long unique password never reused anywhere.
- `set onesync on` - required for the server-side entity gates used above (`entityCreating`, ownership, routing buckets).
- Verify the convars covered elsewhere in this file are actually set: `setr sv_stateBagStrictMode true` (Sync Safety), `sv_filterRequestControl` (Entity And Net ID Validation / `skills/common/networking.md`), `sv_enableNetworkedPhoneExplosions`/`sv_enableNetworkedSounds`/`sv_enableNetworkedScriptEntityStates` (Built-in Client Events), `sv_authMinTrust`/`sv_authMaxVariance` (Identifier Trust).

### Operator access

- Run a recent FXServer artifact; old artifacts carry known, already-patched security issues.
- Do not expose the txAdmin port (default `40120`) to the whole internet; firewall it to admin IPs, use a strong unique password, and keep txAdmin updated.
- Keep `server.cfg` out of public git - it holds the license key, DB string, and admin identifiers. Commit a placeholder `server.cfg.example`, and `exec` a `.gitignore`d `secrets.cfg` for real values. A committed secret is compromised the moment it is pushed: rotate it first, then purge history.

### HTTP handlers

- `SetHttpHandler` exposes an HTTP endpoint on the server's public port (`http://host:30120/<resource>/...`) - unauthenticated and internet-reachable by default. Treat it exactly like a public net event: allowlist method + path, bound the body size before parsing, require a server-held token for anything privileged, rate-limit per caller, and respond 404 to everything else.
- Do not leak stack traces, file paths, or config values in HTTP error responses.
- Prefer not exposing HTTP at all when events/exports can carry the traffic.

### Database and supply chain

- Run the game database as a dedicated MySQL user with grants limited to the game schema (no `SUPER`/`FILE`/`GRANT`, never root), reachable only from the server host or a private network.
- Treat third-party resources as untrusted code you are about to run with full server trust. Red flags: obfuscated/encrypted Lua, `PerformHttpRequest` to unknown domains, remote loaders (`load(...)`/`assert(load(...))` on fetched strings), `os.execute`/`io.popen` on the server, giant base64 blobs. "Leaked"/cracked scripts are a known backdoor vector - do not run them.
- Prefer resources whose source you can read; a resource that must hide its code is itself a risk signal on a server you own.

## Performance Rules

- Prefer RAM/cache/indexes over repeated CPU work only for hot paths or expensive repeated work.
- FXServer performance is often limited by single-core CPU time, but RAM is not free and bad caches can create leaks or GC pressure.
- Precompute and cache indexes, normalized config, lookup maps, encoded data, and reusable results when the saved CPU cost is worth the memory.
- Do not cache cold-path data or values that are cheaper to recompute.
- Every cache must have an owner, a reason to exist, and a cleanup path.
- Do not recompute or rescan data every tick just to save a small amount of memory.
- Avoid `Wait(0)` unless the logic must run every frame.
- Use staged/adaptive waits:
  - Far or idle state: `Wait(1000)` or more.
  - Nearby polling: `Wait(500)`.
  - Active checks: `Wait(100)` or more.
  - Frame controls/draw calls only: `Wait(0)`.
- Prefer event/state-bag driven updates over always-running loops.
- Do not scan all players, all entities, or all pending requests every tick unless the list is small and the interval is long.
- Cache repeated natives and table lookups in locals inside loops.
- Avoid repeated `PlayerPedId()`, `GetEntityCoords()`, `GetPlayerPed(...)`, and large table scans when a local cached value is enough.
- Build reverse indexes for large config lists:
  - `Items["INDEX"][name] = index`
  - `Jobs["INDEX"][name] = index`
  - `Weapons["INDEX"][name] = index`
- Use O(1) maps for hot lookup paths instead of repeated linear scans.
- If code repeatedly uses `for` loops to find one entry by name, ID, category, hash, or source, build an index once and read it directly.
- Prefer direct indexed lookup like `Items["INDEX"][itemName]` over scanning the whole item list in hot paths.
- Require only config modules used by the current script; do not eager-load large config files into scripts that do not need them.
- Keep hot-loop payloads and state-bag data small.
- Clear RAM caches when they are tied to player/resource lifetime so memory does not grow forever.

## Cleanup

- Clean entities, objects, peds, vehicles, blips, zones, NUI focus, timers, callback entries, throttle tables, queue entries, state bags, local state, and player caches on player drop or resource stop.
- Guard entity cleanup with `DoesEntityExist`.
- Increment timer IDs or use cancellation guards when delayed timers may outlive the player/resource state they were created for.
- If a loop processes many players, wrap per-player work defensively so one bad player state cannot stop the whole loop.

## Anti-Overengineering

- Do not build a new framework, class system, event dispatcher, or generic module loader for a small resource.
- Keep security checks and performance caches direct and local unless the same pattern is reused enough to justify a helper.
- Prefer one clear validation block over a generic validator that hides what the event accepts.
- Prefer one clear cleanup function over many tiny cleanup abstractions when the resource is small.

## Review Questions

- What can a malicious client fake in this feature?
- Which server-side checks reject fake values?
- Is this network event actually meant to be public, or should it be a local function (`AddEventHandler`)?
- Does the handler reject `source == 65535` / `source <= 0` when only a real client may trigger it?
- Does the recipient of any value come from `source`, never from a payload field?
- Do commands, exports, callbacks, and NUI callbacks validate the same things as server events?
- Is every value resolved from server-held state (catalog, balance, permissions), not the payload?
- Does this give-value event pass the give-value checklist (identity, catalog, bounded quantity, fresh afford check, atomic debit+grant, idempotency, ACE-gated admin path)?
- Are admin/sensitive actions gated by `IsPlayerAceAllowed`, not by a client-side flag or a client-reported job/identifier?
- Does this event need a throttle or cooldown? Could an unthrottled handler be a DoS or dupe vector?
- Does this valuable action need a request ID, in-flight flag, transaction, or duplicate-claim check?
- Does this callback/event clean up pending state on disconnect?
- Are client-provided coords, entity IDs, net IDs, jobs, permissions, and ownership claims verified server-side?
- Is entity ownership rechecked against a server registry (ownership migrates)?
- Are built-in client events (`weaponDamageEvent`, `explosionEvent`, and friends) intercepted/validated, and are the networked-event convars set where abuse matters?
- Is any broadcast `TriggerClientEvent(name, -1)` justified, or should it be scoped/targeted?
- Is every SQL query parameterized (`?`/`@name`)? Any client value concatenated into SQL or an identifier?
- Are client strings and tables bounded (length, key count, depth) before they are decoded, iterated, stored, or logged?
- Does any `SetHttpHandler` endpoint exist, and does it authenticate, bound, and rate-limit like a public event?
- Do valuable mutations write an audit trail that could reconstruct a dupe after the fact?
- Are the platform hardening convars set (`sv_scriptHookAllowed 0`, `sv_pureLevel`, `sv_requestParanoia`, `sv_endpointPrivacy`, rcon off), and are third-party resources vetted before install?
- Are secrets in server-only `set` convars (never `setr`/`sets`/shared/client)?
- Does identity come from `GetPlayerIdentifiers(source)` on the server, and are bans/whitelist checked in `playerConnecting` deferrals?
- Are prices, rewards, drop rates, and permission gates kept out of shared/client config or revalidated server-side?
- Can another resource call this interface with bad input?
- Is any secret or webhook visible to the client?
- Is this loop always necessary, or can it be event-driven?
- Is any hot path scanning a large table repeatedly?
- Can this data be indexed once and read O(1)?
- Are database writes debounced and dirty-tracked?
- Are log payloads bounded and redacted?
