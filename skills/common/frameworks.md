# Framework Integration Rules

Use when a resource integrates a player framework: ESX, QBCore, Qbox (FiveM) or VORP, RSG (RedM). b3sty resources stay framework-free by default (`skills/fivem/rules.md` / `skills/redm/rules.md` -> Resource Defaults); add framework code only when the project already runs one.

Framework APIs change between versions: the shapes below match current mainstream releases, so confirm each call against the installed source and record verified differences in `memory/`. VORP depth (inventory export signatures, callbacks, state bags, traps) is in `skills/redm/vorp.md`.

## Defaults

- Every framework call lives behind a small bridge (`bridge/server.lua`, `bridge/client.lua`): gameplay code calls `Bridge.RemoveMoney(...)`, never `xPlayer`/`Player.Functions`. This is the "small local adapter" from the game rules files, not a framework of its own.
- Only the server bridge touches money, items, jobs or saved character data; the client bridge reads display data (name, job label) and listens to lifecycle events.
- Fetch the player object inside each server call; never cache it across yields or keep it after `playerDropped`.
- Client-side framework data (`ESX.PlayerData`, `QBCore.Functions.GetPlayerData()`, VORP client character cache) is display-only: every money/item/job/permission decision re-reads server state.
- Key saved per-character data by the framework's character ID, not `license`/`license2`: one license can own several characters.

## Core Objects And Player Lookup

| Framework | Core object (server) | Player lookup | Character ID |
|---|---|---|---|
| ESX Legacy | `exports.es_extended:getSharedObject()` | `ESX.GetPlayerFromId(source)` | `xPlayer.identifier` |
| QBCore | `exports['qb-core']:GetCoreObject()` | `QBCore.Functions.GetPlayer(source)` | `Player.PlayerData.citizenid` |
| Qbox | none needed | `exports.qbx_core:GetPlayer(source)` | `player.PlayerData.citizenid` |
| VORP | `exports.vorp_core:GetCore()` | `Core.getUser(source).getUsedCharacter` | `character.charIdentifier` |
| RSG | `exports['rsg-core']:GetCoreObject()` | `RSGCore.Functions.GetPlayer(source)` | `Player.PlayerData.citizenid` |

- Every lookup returns `nil` for a connected player whose character is not loaded yet (character select, spawn screen): nil-check before indexing. VORP differs - `getUser` returns `nil` only for an unknown source, and `getUsedCharacter` is an empty table `{}` until a character is selected, so check `character.charIdentifier`.
- Qbox ships a `qb-core` compatibility layer, so `GetResourceState('qb-core')` can look started on a Qbox server: detect `qbx_core` first.
- RSG is a QBCore fork: same `PlayerData`/`Functions` shape with `RSGCore` names. Qbox player objects also expose `PlayerData` and `Functions`.
- VORP `getUsedCharacter` is a field, not a method: `user.getUsedCharacter`, no call parentheses.

## Money

- Check the balance and debit in the same synchronous block with no yield between (no `Wait`, `.await`, callback or yielding export). CfxLua runs one handler at a time, so check-then-debit without a yield cannot race another event.
- Do not trust the framework's remove call to refuse an overdraft:
  - ESX `xPlayer.removeMoney(amount, reason)` / `removeAccountMoney(account, amount, reason)`: check `getMoney()` / `getAccount(name).money` first.
  - QBCore/Qbox/RSG `Functions.RemoveMoney(type, amount, reason)` returns `false` on refusal, but only types in `DontAllowMinus` are protected from going negative (defaults: QBCore/Qbox `cash`, `crypto`; RSG `cash`, `gold`, `bloodmoney`). `bank` can go below zero (down to `Config.Money.MinusLimit`, default `-5000`, in QBCore/RSG; unlimited in Qbox). Check `PlayerData.money[type]` first and still honor the return value.
  - VORP `character.removeCurrency(0, amount)` (`0` money, `1` gold, `2` role token) subtracts without any check and returns nothing: check `character.money` / `character.gold` first.
- Pass a reason string on every add/remove that accepts one - it feeds the framework's money logs - and keep your own audit log too (`skills/common/server-hardening.md` -> Logging And Secrets).
- The give-value checklist (validation, throttle, in-flight lock, server-side price) still applies: `skills/common/give-value-hardening.md` -> Give-Value Event Hardening.

## Items

- Use the inventory the server actually runs; frameworks differ (ESX built-in or ox_inventory, QBCore qb-inventory or ox_inventory, Qbox ox_inventory, VORP vorp_inventory, RSG rsg-inventory).
- Check capacity, take payment, grant, and refund a failed grant in the same path. With ox_inventory: `exports.ox_inventory:CanCarryItem(source, name, count)` then `exports.ox_inventory:AddItem(source, name, count)`, which returns `false` plus a reason on failure.
- Item names come from server config or the framework item list, never the client payload: look the name up in your own index first.

## Jobs And Permissions

- Read job and grade from the server player object: ESX `xPlayer.job.name` / `xPlayer.job.grade`, QBCore/Qbox/RSG `PlayerData.job.name` / `PlayerData.job.grade.level` / `PlayerData.job.onduty`, VORP `character.job` / `character.jobGrade`.
- Check on-duty state where the framework has it: an off-duty officer must not pass a police-only check.
- Staff/admin actions use ACE (`IsPlayerAceAllowed`), not framework groups alone, unless the project standardizes on framework groups: `skills/common/give-value-hardening.md` -> ACE Permissions And Admin Authority.

## Lifecycle Events

| Framework | Character loaded (server) | Character loaded (client) | Unloaded / logout |
|---|---|---|---|
| ESX | `esx:playerLoaded` (`playerId, xPlayer, isNew`) | `esx:playerLoaded` (`playerData, isNew, skin`; plain data table, not an xPlayer object) | server `esx:playerDropped` (`playerId, reason`) |
| QBCore / Qbox | `QBCore:Server:PlayerLoaded` (`Player`) | `QBCore:Client:OnPlayerLoaded` | server `QBCore:Server:OnPlayerUnload` (`source`), client `QBCore:Client:OnPlayerUnload` |
| VORP | `vorp:SelectedCharacter` (`source, character`) | `vorp:SelectedCharacter` (`charId`) | `playerDropped` |
| RSG | `RSGCore:Server:PlayerLoaded` (`Player`) | `RSGCore:Client:OnPlayerLoaded` | `RSGCore:Server:OnPlayerUnload` / `RSGCore:Client:OnPlayerUnload` |

- Framework server lifecycle events are server-local: listen with `AddEventHandler`, never `RegisterNetEvent`, which would let any client fake a "character loaded" call.
- Character switch (multicharacter logout) is not `playerDropped`: clear per-character state on the unload event too.
- A resource restart does not replay "loaded" events. On `onResourceStart` for your own resource, initialize every already-loaded player (ESX `ESX.GetExtendedPlayers()`, QBCore `QBCore.Functions.GetQBPlayers()`, Qbox `exports.qbx_core:GetQBPlayers()`, RSG `RSGCore.Functions.GetRSGPlayers()`; VORP: loop `GetPlayers()` and skip users whose `getUsedCharacter.charIdentifier` is `nil`).

## ESX Legacy Known Pitfalls

Holes in stock ESX Legacy 1.15.2 - check them against the installed version before trusting a stock path (verified: fork-vs-upstream source diff; 1.16 fixes noted):

- `esx:spawnVehicle` server callback is callable by any client: add an admin check and a throttle.
- `esx:updateWeaponAmmo` accepts increases: accept decreases only.
- `esx:giveInventoryItem` allows target == source, which races into a dupe: reject self-transfer.
- Items with `can_remove = 0` are only hidden in the UI: enforce the flag in the give/drop net handlers.
- Negative counts are not normalised: clamp every count to a positive integer server-side.
- Commands registered with no permission are open to every `user` in 1.15.2: default them to admin.
- `ESX.RefreshItems` clears `ESX.Items` before the SELECT returns, so a player joining in that window loads an empty inventory and it gets saved over the real one (fixed in 1.16): build the new table aside and swap it in with one assignment.
- `xPlayer.removeWeapon` walks the component list with `ipairs` while removing from it, so every second component survives: iterate a copy, or backwards.
- `/refreshjobs` swaps `ESX.Jobs`, but online clients keep the old labels and salaries until relog: push the new job data to clients.
- Pickups are broadcast to `-1` across every routing bucket in 1.15.2: send them per bucket.

## Bridge Pattern

Detect once at load, fail loudly if nothing matches, expose a few narrow functions that return explicit success values.

```lua
-- bridge/server.lua (first entry in server_scripts)
Bridge = {}

if GetResourceState("qbx_core") == "started" then
    Bridge.Name = "qb"
    Bridge.GetPlayer = function(source) return exports.qbx_core:GetPlayer(source) end
elseif GetResourceState("qb-core") == "started" or GetResourceState("rsg-core") == "started" then
    -- RSG is a QBCore fork: same Functions shape, different resource name.
    local core = GetResourceState("qb-core") == "started" and exports["qb-core"]:GetCoreObject()
        or exports["rsg-core"]:GetCoreObject()
    Bridge.Name = "qb"
    Bridge.GetPlayer = function(source) return core.Functions.GetPlayer(source) end
elseif GetResourceState("es_extended") == "started" then
    local ESX = exports.es_extended:getSharedObject()
    Bridge.Name = "esx"
    Bridge.GetPlayer = function(source) return ESX.GetPlayerFromId(source) end
elseif GetResourceState("vorp_core") == "started" then
    local Core = exports.vorp_core:GetCore()
    Bridge.Name = "vorp"
    Bridge.GetPlayer = function(source)
        local user = Core.getUser(source)
        local character = user and user.getUsedCharacter
        return character and character.charIdentifier and character or nil
    end
else
    error(("%s: no supported framework started - check server.cfg ensure order"):format(GetCurrentResourceName()))
end

-- Cash only. No yield between the balance check and the debit.
function Bridge.RemoveCash(source, amount, reason)
    local player = Bridge.GetPlayer(source)
    if not player then return false end

    if Bridge.Name == "qb" then
        if player.PlayerData.money.cash < amount then return false end
        return player.Functions.RemoveMoney("cash", amount, reason)
    elseif Bridge.Name == "esx" then
        if player.getMoney() < amount then return false end
        player.removeMoney(amount, reason)
        return true
    end

    if player.money < amount then return false end   -- VORP
    player.removeCurrency(0, amount)
    return true
end

function Bridge.GetCharId(source)
    local player = Bridge.GetPlayer(source)
    if not player then return nil end

    if Bridge.Name == "qb" then return player.PlayerData.citizenid end
    if Bridge.Name == "esx" then return player.identifier end
    return player.charIdentifier
end
```

- The core-object lookups run at load time, so the framework must be started first: put this resource later in `server.cfg`, or add a `dependency` line when it supports only one framework. Restarting the framework stops every dependent and does not start them again (`skills/common/runtime.md` -> Resource Lifecycle); see Exports And Stale References there for resources that outlive a provider restart.
- `Bridge` is a resource-scoped global for other server files in the same resource, not visible to other resources.
- Add only the functions this resource needs (`RemoveCash`, `AddItem`, `HasJob`); mirroring the whole framework API is overengineering (`skills/common/performance.md` -> Anti-Overengineering). Character IDs come from the table above.

## Review Questions

- Any gameplay file calling a framework API directly instead of the bridge?
- Every framework lookup nil-checked for players who have not loaded a character?
- Balance checked before every debit, no yield between check and debit, remove call's result honored?
- Framework lifecycle events registered with `AddEventHandler` only?
- Per-character state cleared on unload/character switch, not only on `playerDropped`?
- A restart of this resource re-initializing players who are already loaded?
- Saved data keyed by character ID rather than license?
