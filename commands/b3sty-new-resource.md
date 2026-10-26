---
description: Scaffold a new RedM/FiveM Lua resource that follows the b3sty rules from the first commit - fxmanifest, config, client/server controllers, prefixed events with server validation, cleanup, and optional framework bridge, NUI, and oxmysql pieces. Use when asked to create, start, scaffold, or bootstrap a new FiveM or RedM resource or script.
argument-hint: [resource name and what it does]
---

# b3sty New Resource

Target: $ARGUMENTS

Create a new RedM/FiveM resource skeleton that already satisfies the b3sty rules. Paths under `skills/` and `memory/` below are relative to the b3sty-skill root (the folder holding the main `SKILL.md`; with the plugin install, the plugin root).

## 1. Decide The Shape

Infer from the request and the surrounding server repo; ask only for what cannot be inferred:

- **Resource name** - lowercase with underscores; it prefixes every event (`name:server:action`).
- **Game** - `gta5`, `rdr3`, or both.
- **Framework** - none (default), or the one the server already runs (ESX, QBCore, Qbox, VORP, RSG).
- **NUI** - only if the feature needs a browser UI.
- **Database** - only if state must survive a restart.
- **ox_lib** - only if the server already runs it (`skills/common/ox-lib.md`).

Default to the smallest shape: no framework, no NUI, no database.

## 2. Files

Follow `skills/common/resource-structure.md` -> Resource Structure and `skills/common/fxserver.md` -> Typical Layout:

```text
resource_name/
    fxmanifest.lua
    config.lua
    core/client.lua
    core/server.lua
    bridge/server.lua       -- only with a framework
    html/index.html         -- only with NUI
    sql/install.sql         -- only with a database
```

### fxmanifest.lua

```lua
fx_version 'cerulean'
games { 'gta5' }            -- { 'rdr3' } or { 'rdr3', 'gta5' }
lua54 'yes'

-- rdr3_warning 'I acknowledge that this is a prerelease build of RedM, and I am aware my resources *will* become incompatible once RedM ships.'

shared_scripts {
    'config.lua',
}

client_scripts {
    'core/client.lua',
}

server_scripts {
    -- '@oxmysql/lib/MySQL.lua',
    -- 'bridge/server.lua',
    'core/server.lua',
}
```

- Keep `rdr3_warning` only when `rdr3` is in `games`.
- With NUI add `ui_page 'html/index.html'` and list every asset in `files` (`skills/common/nui.md`).
- With oxmysql, uncomment its loader line and add `dependency 'oxmysql'`.

### core/server.lua

```lua
local Controller = {
    ["ActionThrottle"] = {},
}

function Controller:IsThrottled(source, key, limit)
    local now = GetGameTimer()
    local throttle = self.ActionThrottle[source]

    if not throttle then
        throttle = {}
        self.ActionThrottle[source] = throttle
    end

    if now - (throttle[key] or 0) < limit then
        return true
    end

    throttle[key] = now
    return false
end

RegisterNetEvent("resource_name:server:action", function(payload)
    local source = source
    if type(source) ~= "number" or source <= 0 then return end
    if type(payload) ~= "table" then return end
    if Controller:IsThrottled(source, "action", 500) then return end

    -- validate every payload field, then decide the outcome server-side
end)

AddEventHandler("playerDropped", function()
    local source = source
    Controller.ActionThrottle[source] = nil
end)

AddEventHandler("onResourceStop", function(resourceName)
    if resourceName ~= GetCurrentResourceName() then return end
    -- delete server-created entities, flush dirty saves without yielding
end)
```

### core/client.lua

```lua
local Controller = {}

function Controller:Start()
    CreateThread(function()
        while true do
            local sleep = 1000
            -- lower sleep only while the player is near/active; never a constant Wait(0)
            Wait(sleep)
        end
    end)
end

AddEventHandler("onResourceStop", function(resourceName)
    if resourceName ~= GetCurrentResourceName() then return end
    -- delete local props, blips, zones; SetNuiFocus(false, false) if NUI is used
end)

Controller:Start()
```

- Replace `resource_name` with the real name everywhere.
- Add a framework bridge only from `skills/common/frameworks.md` -> Bridge Pattern, trimmed to the functions this resource uses.
- Put valuable actions (money, items, rewards) through `skills/common/security-performance.md` -> Give-Value Event Hardening from the start.
- For persisted state, follow `skills/common/database.md` and the persistence shape in `memory/common/cfx-patterns.md`.

## 3. Check Before Handing Over

- Every custom event is `resource_name:server:*` or `resource_name:client:*`, and every server handler validates `source` and its payload.
- No client-trusted price, amount, reward, or permission.
- Every entity, blip, zone, timer, NUI focus, and per-player table has a cleanup path on `playerDropped` and `onResourceStop`.
- No constant `Wait(0)` loop.
- The manifest lists only files that exist, and `games` matches the natives used.

Tell the user the `ensure resource_name` line to add to `server.cfg` (after its framework and oxmysql), and the in-game steps to confirm it starts cleanly.
