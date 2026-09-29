# Framework Integration Rules

Use this file when a RedM/FiveM resource integrates with a player framework: ESX, QBCore, Qbox (FiveM) or VORP, RSG (RedM). b3sty resources stay framework-free by default (`skills/fivem/rules.md` / `skills/redm/rules.md` -> Resource Defaults); add framework code only when the project already runs one.

Framework APIs change between versions. The shapes below match current mainstream releases; confirm each call against the installed framework's source before relying on it, and record verified differences in `memory/`.

## Defaults

- Keep every framework call behind a small bridge (`bridge/server.lua`, `bridge/client.lua`) so gameplay code calls `Bridge.RemoveMoney(...)`, never `xPlayer`/`Player.Functions` directly. This is the "small local adapter" from the game rules files, not a framework of its own.
- Only the server bridge may touch money, items, jobs, or saved character data. The client bridge only reads display data (name, job label) and listens to lifecycle events.
- Fetch the player object inside each server call; do not cache player objects across yields or keep them after `playerDropped`.
- Treat client-side framework data (`ESX.PlayerData`, `QBCore.Functions.GetPlayerData()`, VORP client character cache) as display-only. Every decision about money, items, jobs, or permissions re-reads server-side state.
- Key saved per-character data by the framework's character ID, not by `license`/`license2`: one license can own several characters.

## Core Objects And Player Lookup

| Framework | Core object (server) | Player lookup | Character ID |
|---|---|---|---|
| ESX Legacy | `exports.es_extended:getSharedObject()` | `ESX.GetPlayerFromId(source)` | `xPlayer.identifier` |
| QBCore | `exports['qb-core']:GetCoreObject()` | `QBCore.Functions.GetPlayer(source)` | `Player.PlayerData.citizenid` |
| Qbox | none needed | `exports.qbx_core:GetPlayer(source)` | `player.PlayerData.citizenid` |
| VORP | `exports.vorp_core:GetCore()` | `Core.getUser(source).getUsedCharacter` | `character.charIdentifier` |
| RSG | `exports['rsg-core']:GetCoreObject()` | `RSGCore.Functions.GetPlayer(source)` | `Player.PlayerData.citizenid` |

- Every lookup returns `nil` for a connected player whose character is not loaded yet (character select, spawn screen). Nil-check before indexing. VORP is the exception: `getUser` returns `nil` only for an unknown source, and `getUsedCharacter` is an empty table `{}` until a character is selected, so check `character.charIdentifier` instead.
- Qbox ships a `qb-core` compatibility layer, so `GetResourceState('qb-core')` can look started on a Qbox server. Detect `qbx_core` first.
- RSG is a QBCore fork: same `PlayerData`/`Functions` shape with `RSGCore` names. Qbox player objects also expose `PlayerData` and `Functions`.
- VORP `getUsedCharacter` is a field, not a method: `user.getUsedCharacter`, no call parentheses.

## Money

- Check the balance and debit in the same synchronous block with no yield in between (no `Wait`, `.await`, callback, or export that yields). CfxLua runs one handler at a time, so check-then-debit without a yield cannot race another event.
- Do not trust the framework's remove call to refuse an overdraft:
  - ESX `xPlayer.removeMoney(amount, reason)` / `removeAccountMoney(account, amount, reason)`: check `getMoney()` / `getAccount(name).money` first.
  - QBCore/Qbox/RSG `Functions.RemoveMoney(type, amount, reason)` returns `false` on refusal, but only the types in `DontAllowMinus` are protected from going negative (defaults: QBCore/Qbox `cash`, `crypto`; RSG `cash`, `gold`, `bloodmoney`). `bank` can go below zero (down to `Config.Money.MinusLimit`, default `-5000`, in QBCore/RSG; unlimited in Qbox). Check `PlayerData.money[type]` first and still honor the return value.
  - VORP `character.removeCurrency(0, amount)` (`0` money, `1` gold, `2` role token) subtracts without any check and returns nothing: check `character.money` / `character.gold` first.
- Pass a reason string on every add/remove where the framework accepts one; it feeds the framework's own money logs. Keep your resource's audit log as well (`skills/common/security-performance.md` -> Logging And Secrets).
- The full give-value checklist (validation, throttle, in-flight lock, server-side price) still applies: `skills/common/security-performance.md` -> Give-Value Event Hardening.

## Items

- Use the inventory the server actually runs; frameworks differ (ESX built-in or ox_inventory, QBCore qb-inventory or ox_inventory, Qbox ox_inventory, VORP vorp_inventory, RSG rsg-inventory).
- Check capacity before taking payment, then grant, and handle a failed grant by refunding in the same code path. With ox_inventory: `exports.ox_inventory:CanCarryItem(source, name, count)` then `exports.ox_inventory:AddItem(source, name, count)`, which returns `false` plus a reason on failure.
- Item names come from server config or the framework item list, never from the client payload directly; look the name up in your own index first.

## Jobs And Permissions

- Read job and grade from the server player object: ESX `xPlayer.job.name` / `xPlayer.job.grade`, QBCore/Qbox/RSG `PlayerData.job.name` / `PlayerData.job.grade.level` / `PlayerData.job.onduty`, VORP `character.job` / `character.jobGrade`.
- Check on-duty state where the framework has it; an off-duty officer should not pass a police-only check.
- Staff/admin actions use ACE (`IsPlayerAceAllowed`), not framework groups alone, unless the project already standardizes on framework groups: `skills/common/security-performance.md` -> ACE Permissions And Admin Authority.

## Lifecycle Events

| Framework | Character loaded (server) | Character loaded (client) | Unloaded / logout |
|---|---|---|---|
| ESX | `esx:playerLoaded` (`playerId, xPlayer, isNew`) | `esx:playerLoaded` (`playerData, isNew, skin`; plain data table, not an xPlayer object) | server `esx:playerDropped` (`playerId, reason`) |
| QBCore / Qbox | `QBCore:Server:PlayerLoaded` (`Player`) | `QBCore:Client:OnPlayerLoaded` | server `QBCore:Server:OnPlayerUnload` (`source`), client `QBCore:Client:OnPlayerUnload` |
| VORP | `vorp:SelectedCharacter` (`source, character`) | `vorp:SelectedCharacter` (`charId`) | `playerDropped` |
| RSG | `RSGCore:Server:PlayerLoaded` (`Player`) | `RSGCore:Client:OnPlayerLoaded` | `RSGCore:Server:OnPlayerUnload` / `RSGCore:Client:OnPlayerUnload` |

- Framework server lifecycle events are server-local. Listen with `AddEventHandler`, never `RegisterNetEvent`: registering them as net events lets any client fake a "character loaded" call into your handler.
- Character switch (multicharacter logout) is not `playerDropped`. Clear per-character state on the unload event as well as on `playerDropped`.
- A restart of your resource does not replay "loaded" events. On `onResourceStart` for your own resource, initialize every already-loaded player (ESX `ESX.GetExtendedPlayers()`, QBCore `QBCore.Functions.GetQBPlayers()`, Qbox `exports.qbx_core:GetQBPlayers()`, RSG `RSGCore.Functions.GetRSGPlayers()`; for VORP loop `GetPlayers()` and skip users whose `getUsedCharacter.charIdentifier` is `nil`).

## Bridge Pattern

Detect once at load, fail loudly if nothing matches, and expose a few narrow functions that return explicit success values.

```lua
-- bridge/server.lua (first entry in server_scripts)
Bridge = {}

if GetResourceState("qbx_core") == "started" then
    Bridge.Name = "qb"
    Bridge.GetPlayer = function(source) return exports.qbx_core:GetPlayer(source) end
elseif GetResourceState("qb-core") == "started" then
    local QBCore = exports["qb-core"]:GetCoreObject()
    Bridge.Name = "qb"
    Bridge.GetPlayer = function(source) return QBCore.Functions.GetPlayer(source) end
elseif GetResourceState("rsg-core") == "started" then
    local RSGCore = exports["rsg-core"]:GetCoreObject()
    Bridge.Name = "qb"
    Bridge.GetPlayer = function(source) return RSGCore.Functions.GetPlayer(source) end
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

function Bridge.GetCharId(source)
    local player = Bridge.GetPlayer(source)
    if not player then return nil end

    if Bridge.Name == "qb" then return player.PlayerData.citizenid end
    if Bridge.Name == "esx" then return player.identifier end
    return player.charIdentifier
end

-- Cash only. No yield between the balance check and the debit.
function Bridge.RemoveCash(source, amount, reason)
    local player = Bridge.GetPlayer(source)
    if not player then return false end

    if Bridge.Name == "qb" then
        if player.PlayerData.money.cash < amount then return false end
        return player.Functions.RemoveMoney("cash", amount, reason)
    end

    if Bridge.Name == "esx" then
        if player.getMoney() < amount then return false end
        player.removeMoney(amount, reason)
        return true
    end

    if player.money < amount then return false end
    player.removeCurrency(0, amount)
    return true
end
```

- The core-object lookups run at load time, so the framework must be started before this resource: put it earlier in `server.cfg`, or add a `dependency` line when the resource supports only one framework. A framework restart restarts dependents; see `skills/common/runtime.md` -> Exports And Stale References for resources that outlive a provider restart.
- `Bridge` is a resource-scoped global so other server files in the same resource can call it; it is not visible to other resources.
- Add only the functions this resource needs (`RemoveCash`, `AddItem`, `HasJob`). A bridge that mirrors the whole framework API is overengineering (`skills/common/security-performance.md` -> Anti-Overengineering).

## Review Questions

- Does any gameplay file call a framework API directly instead of the bridge?
- Is every framework lookup nil-checked for players who have not loaded a character?
- Is the balance checked before every debit, with no yield between check and debit, and is the remove call's result honored?
- Are framework lifecycle events registered with `AddEventHandler` only?
- Is per-character state cleared on unload/character switch, not only on `playerDropped`?
- Does a restart of this resource re-initialize players who are already loaded?
- Is saved data keyed by character ID rather than license?
