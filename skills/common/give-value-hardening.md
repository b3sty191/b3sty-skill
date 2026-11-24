# Give-Value And Admin Grant Hardening

Any handler that grants, removes, transfers, prices, or pays something of value, plus the admin path that does the same. Core event-security rules and the index of every section named "above"/"below": `skills/common/security-performance.md` -> Contents.

## Give-Value Event Hardening

The highest-frequency exploit class on CFX servers: shop buys, payouts, crafting, quest rewards, drops, trades, admin grants. A client event may **request** an action; it must never specify the amount, the item, the price, or the recipient of anything of value - the server decides all of those from server-held state. (Principles: [Secure your events](https://docs.fivem.net/docs/developers/server-security/).)

### Vulnerable

```lua
-- BAD: client controls both the item and the price; recipient defaults to source but is never re-checked
RegisterNetEvent("shop:server:buy", function(item, price)
    local player = Framework.GetPlayer(source)
    player.removeMoney(price)     -- client-chosen price can be NEGATIVE -> money goes UP
    player.addItem(item)          -- client-chosen item, no catalog/ownership check, fixed count of 1
end)
```

A mod menu fires `TriggerServerEvent("shop:server:buy", "weapon_rpg", -1000000)` and gains money plus the item. Negative price or quantity is a classic dupe.

### Give-value event checklist

Apply in order to every handler that grants, removes, transfers, prices, or pays anything of value; the code below marks the steps.

1. **Identity = `source`, never the payload.** Reject a non-numeric/empty `source` (server-originated) or `source <= 0`, and any payload field claiming to be the recipient. A normal player must not grant items to an arbitrary ID; only an ACE-gated admin grant may target another player (see ACE Permissions And Admin Authority).
2. **Server-authoritative catalog.** Items, prices, weights, stack limits, and craft recipes live in server config/DB. The client sends at most an item key/id; the server maps it to real data and rejects unknown keys. Never accept `price` from the client.
3. **Validate every field before touching value.** Type, range, and existence checks on the item key and quantity first; reject missing/extra fields as hostile.
4. **Quantity is a positive, bounded integer.** Reject `nil`, `NaN`, `0`, negatives, floats, and values above a sane max: `local amount = tonumber(x); if not amount or amount ~= amount or amount % 1 ~= 0 or amount <= 0 or amount > MAX then return end`. A negative amount in a transfer/remove path is a dupe.
5. **Affordability from fresh server state.** Re-read balance/inventory at the moment of the transaction, never a value cached from an earlier request. Reject if `balance < price * amount`.
6. **Debit + grant atomically.** Check-then-mutate must not be interruptible by the same player spamming the event: a per-source in-flight lock that is always released (even on error), or a conditional DB debit checked for exactly 1 affected row in the same transaction as the grant (variant (b) below). Never `Wait()` between check and mutation with shared state exposed. One source of truth for money/inventory - the framework's RAM cache or the database, never both.
7. **Rate-limit + idempotency.** Throttle per source. For one-shot grants (quest reward, daily claim), record server-side that it was claimed and reject repeats; never rely on the client not re-firing.
8. **Admin grants are ACE-gated (`IsPlayerAceAllowed`) and logged.** No client-side "admin" flag, no spoofable identifier (see ACE Permissions And Admin Authority).

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

-- (5)+(6) the locked section. Pick ONE source of truth for money/inventory, never both.

-- (a) Framework/RAM-authoritative (the usual ESX/QBCore/VORP case): mutate through the
-- framework API and let it persist. No SQL, no yield between check and mutation.
function Controller:Purchase(player, entry, itemName, amount)
    local cost = entry.price * amount
    if player.getMoney() < cost then return end                   -- (5) current server-held balance
    if not player.canCarryItem(itemName, amount) then return end  -- reject before debiting
    player.removeMoney(cost)
    player.addItem(itemName, amount)
end

-- (b) DB-authoritative: only when no framework RAM copy of money/inventory is saved back over
-- these columns. The conditional debit IS the affordability check; returning false (0 rows =
-- cannot afford) or any SQL error rolls back both (oxmysql startTransaction, experimental).
function Controller:PurchaseSql(player, entry, itemName, amount)
    local cost = entry.price * amount

    local committed = MySQL.startTransaction(function(query)
        local res = query("UPDATE characters SET money = money - ? WHERE owner = ? AND money >= ?",
            { cost, player.identifier, cost })
        if not res or res.affectedRows ~= 1 then return false end
        query("INSERT INTO inventory (owner, item, count) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE count = count + ?",
            { player.identifier, itemName, amount, amount })
    end)
    if not committed then return end

    -- the transaction yielded, so the player may have dropped: refresh any framework copy by
    -- identifier (not `source`), never by writing back a RAM snapshot taken before the yield
    Framework.RefreshPlayer(player.identifier)                   -- placeholder: re-read money/inventory from DB
end

RegisterNetEvent("shop:server:buy", function(payload)
    local source = source
    if type(source) ~= "number" or source <= 0 then return end   -- "" = server-side TriggerEvent
    if type(payload) ~= "table" then return end
    if Controller:IsThrottled(source, "buy", 250) then return end  -- (7)

    -- (3) field validation first
    local itemName = payload["Item"]
    local amount = tonumber(payload["Amount"])
    if type(itemName) ~= "string" or itemName == "" then return end
    if not amount or amount ~= amount then return end            -- non-numeric / NaN
    if amount % 1 ~= 0 then return end                           -- reject non-integers
    if amount <= 0 or amount > MAX_PER_PURCHASE then return end  -- (4) positive bounded int

    local entry = Controller.Catalog[itemName]                   -- (2) server catalog
    if not entry or not entry.purchasable then return end

    local player = Framework.GetPlayer(source)                   -- (1) identity = source
    if not player then return end

    -- (6) in-flight lock so a flood cannot interleave check/mutate. pcall guarantees the release:
    -- one error (nil price, framework throw, rejected .await) would otherwise lock this player
    -- out of buying until reconnect.
    if Controller.InFlight[source] then return end
    Controller.InFlight[source] = true
    local okRun, err = pcall(Controller.Purchase, Controller, player, entry, itemName, amount)  -- or PurchaseSql
    Controller.InFlight[source] = nil
    if not okRun then
        print(("shop:server:buy failed for %s: %s"):format(source, err))
    end
end)

AddEventHandler("playerDropped", function()
    local source = source
    if source then
        Controller.Throttle[source] = nil
        Controller.InFlight[source] = nil
    end
end)
```

- An oxmysql `MySQL.transaction` rolls back only on an SQL error ([oxmysql transaction](https://overextended.dev/docs/oxmysql/Functions/transaction)): a conditional `UPDATE ... AND money >= ?` matching 0 rows still commits the rest and returns `true`. Gate the grant on the debit affecting exactly 1 row inside the same transaction, as variant (b) does (see `skills/common/database.md` -> Query Safety). `?` placeholders are mandatory; see Database And Persistence.
- Never debit in SQL and again in a RAM-cached framework: a drop-time or autosave write of stale RAM overwrites the committed debit (and a framework that saves inventory from RAM can overwrite or double-apply the SQL grant). Use variant (a) whenever the framework caches money/inventory in RAM; see `memory/common/cfx-patterns.md` -> Player Persistence Pattern.
- Every `.await` yields: the player may have dropped by the time it resumes, so re-validate anything keyed by `source` (`DoesPlayerExist(source)`, or the framework's `GetPlayer(source)`). Server IDs are reused only after the 16-bit ID counter wraps, so a stale ID hitting a *different* player inside one yield is practically impossible; the real reuse risk is a per-`source` table never cleared on `playerDropped` on a long-running server. For valuable mutations, key post-yield work by the pre-yield identifier (compared against the current one), not the source number. See `skills/common/runtime.md` -> The `source` Variable.
- The locked section runs inside `pcall` so the in-flight lock is always released; `pcall` is yield-safe in CFX Lua 5.4, so `.await` inside it works.

Related: Atomic State Changes And Replay Protection below, ACE Permissions And Admin Authority above, and economy-specific dupe notes in `skills/common/networking.md` -> Creating Networked Entities (loot/pickup ownership).

## ACE Permissions And Admin Authority

- Gate admin/sensitive actions behind FiveM's built-in ACL, never client-side flags or spoofable identifiers. `add_ace [principal] [object] [allow|deny]` grants a permission object; `add_principal [child] [parent]` makes an identifier inherit a group (e.g. `add_principal identifier.license:... group.admin`). ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/))
- Check access server-side with `IsPlayerAceAllowed(player, object)` (CFX native `0xDEDAE23D`, server API set), which resolves direct and inherited permissions. ([IsPlayerAceAllowed](https://docs.fivem.net/natives/?_0xDEDAE23D))
- Never gate by a client-side "am I admin" check, a client-sent `group`/`rank` field, or a `job` value the client can report freely: display hints, not authority (see Server Authority).
- Any "give money/item/perm to player X" command or export must be ACE-gated on the invoking `source`, resolve the target `source` server-side, and log who granted what to whom.
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

    local targetPlayer = Framework.GetPlayer(target)
    if not targetPlayer then return end                   -- connected, but character not loaded yet

    targetPlayer.addItem(itemName, amount)
    -- audit trail: server IDs are reused, so log identifiers alongside them
    print(("admin %s (%s) gave %sx %s to %s (%s)"):format(
        source, GetPlayerIdentifierByType(source, "license") or "?",
        amount, itemName,
        target, GetPlayerIdentifierByType(target, "license") or "?"))
end, false)
```

- Do not use `GetPlayerIdentifiers(target)` as an existence check: it returns a table (truthy even when empty) for invalid IDs. Use `GetPlayerName(target)` or `DoesPlayerExist(target)` to confirm the target is a real connected player.
- Polling `IsPlayerAceAllowed` for every player on a tight timer has caused crashes (citizenfx/fivem#2547); check it on the action path, not in a per-player loop.

## Abuse Handling

- Reject and log invalid input; usually do not auto-punish for it.
- Log security-sensitive rejections with source, event/interface name, reason, and bounded key fields. Rate-limit or batch abuse logs so logging is not itself a spam path.
- Track repeated invalid calls per player/action when abuse response matters: counters, backoff, temporary ignore windows, or staff-visible alerts before escalating to kicks or bans.
- Keep an append-only audit trail for value mutations: event name, actor `source` + identifier, target, item, amount, and balance after. Dupe response is a reconstruction problem - without a trail you cannot tell who to roll back or by how much.
- Add server-side sanity envelopes for the economy: alert when a player's money/item delta per time window exceeds a plausible ceiling. Envelopes catch the exploit you did not predict; alerts come before punishment.
