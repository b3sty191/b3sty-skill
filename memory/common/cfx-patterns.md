# Cfx Patterns

Track reusable FXServer/CfxLua implementation patterns here. These apply to both RedM and FiveM unless noted.

## Table Controller Pattern

- Pattern: keep resource state and methods in one local table.
- Use when: a resource needs shared indexes, active entities, cached data, or lifecycle methods.
- Example:
  ```lua
  local Attacher = {
      ["Visible"] = "all",
      ["Players"] = {}
  }

  function Attacher:Initialize()
      self.ObjectsIndex = {}
  end
  ```
- Notes: this keeps the flow direct without creating a large framework around a small resource.

## Index Map Pattern

- Pattern: build a sorted list plus a reverse lookup table.
- Use when: synced state should store small indexes instead of long object names.
- Also use when: code repeatedly loops through a list to find one entry by name, ID, hash, category, or source.
- Example:
  ```lua
  self.ObjectsIndex = {}
  self.ObjectsIndexKey = {}

  for name in pairs(objects) do
      table.insert(self.ObjectsIndex, name)
  end

  table.sort(self.ObjectsIndex)

  for index, name in ipairs(self.ObjectsIndex) do
      self.ObjectsIndexKey[name] = index
  end
  ```
- Notes: useful for inventory items, object attachers, clothing sets, and other editable data maps.
- Notes: in hot paths, direct lookup is preferred over repeated `for` scans.

## State Bag Render Pattern

- Pattern: server changes `Player(source).state`, client listens and renders local entities.
- Use when: clients need to see visual state for nearby or known players.
- Example: server sets `LocalPlayer:set("attach", attach, true)`, client uses `AddStateBagChangeHandler("attach", ...)`.
- Notes: keep validation and important state changes server-side.

## Event Naming Pattern

- Pattern: name events with the resource prefix and the side that handles the event.
- Rule: every custom event is `resource_name:server:action` or `resource_name:client:action` (see `skills/common/resource-structure.md` -> Events).
- Concrete shape used in b3sty resources:
  ```lua
  RegisterNetEvent("resource_name:server:add", function(item, state)
      -- handled on server
  end)

  RegisterNetEvent("resource_name:client:playerDropped", function(player)
      -- handled on client
  end)
  ```

## Cleanup Pattern

- Pattern: delete local entities on `onResourceStop`, player drop, and disabled state.
- Use when: the resource creates objects, blips, zones, peds, vehicles, or temporary handles.
- Notes: guard deletes with `DoesEntityExist`. Full cleanup scope (blips, zones, NUI focus, timers, callbacks, throttles, caches, local state) is in `skills/common/security-performance.md` -> Cleanup.

## Simple Resource Pattern

- Pattern: keep small resources direct instead of creating framework-style layers.
- Use when: a resource has one clear domain and only a few client/server files.
- Avoid when: the same validation, cleanup, or indexing pattern is repeated enough to justify a helper.
- Notes: b3sty style prefers readable local flow over generic architecture.

## Config Split Pattern

- Pattern: keep simple shared values in `config.lua` and move large datasets into `configs/*.lua`.
- Use when: a resource has many positions, zones, objects, categories, shops, rewards, or other long lists.
- Example:
  ```lua
  local locations = require("configs.locations")
  local items = require("configs.items")
  ```
- Notes: full rules in `skills/common/style.md` -> Config Splitting and `skills/common/fxserver.md`.

## Player Persistence Pattern

- Pattern: keep player state in RAM, dirty-track changes, spread autosave over time, and force-save on leave/stop.
- Use when: a resource owns saved player data (money, inventory, jobs, stats) and must not block the main thread or lose much data on crash.
- Rule: full persistence rules (dirty tracking, debounce, parameterized SQL, no per-tick writes) are in `skills/common/security-performance.md` -> Database And Persistence.
- Concrete shape:
  ```lua
  -- RAM cache + dirty tracking + spread autosave + force-save on exit.
  -- Async so it never blocks the main thread; never lose more than the autosave interval on crash.
  local PlayerData = {}    -- [source] = loaded state
  local PlayerDirty = {}   -- [source] = true when changed since last save
  local PlayerSaving = {}  -- [source] = true while a save is in flight (dedupe)

  -- Used by the autosave loop, playerDropped, and onResourceStop, so it stays a function.
  local function SavePlayer(source)
      if PlayerSaving[source] then return end          -- a save is already running
      local data = PlayerData[source]
      if not data then return end

      PlayerSaving[source] = true
      PlayerDirty[source] = nil

      MySQL.async.execute("UPDATE players SET data = ? WHERE identifier = ?", {
          json.encode(data), data.identifier,
      }, function()
          PlayerSaving[source] = nil
      end)
  end

  -- Spread autosave: save at most 10 dirty players per 60s pass, then yield.
  CreateThread(function()
      while true do
          Wait(60 * 1000)
          local saved = 0
          for source in pairs(PlayerDirty) do
              if saved >= 10 then break end
              SavePlayer(source)
              saved += 1
          end
      end
  end)

  -- Force-save on leave (primary save point).
  AddEventHandler("playerDropped", function()
      local src = source
      if src then
          SavePlayer(src)
          PlayerData[src] = nil
          PlayerDirty[src] = nil
          PlayerSaving[src] = nil
      end
  end)

  -- Force-save all dirty players when this resource stops (covers restart/stop).
  AddEventHandler("onResourceStop", function(resourceName)
      if resourceName ~= GetCurrentResourceName() then return end
      for source in pairs(PlayerDirty) do
          SavePlayer(source)
      end
  end)

  -- Gameplay code marks a player dirty inline wherever state changes:
  --   PlayerDirty[source] = true
  ```
- Notes: interval is a trade-off - shorter = less data loss but more DB load; 60-120s is a sane default.
- Notes: `SavePlayer` is kept as a function because it is used in three places (real duplication); dirty marking is inlined because it is one line.
- Notes: async queries are mandatory here - sync DB calls block the single FXServer Lua thread.

## Template

Copy this block when adding a new entry, then fill it in. Leave it blank intentionally - it is a skeleton for future patterns, not a real pattern.

- Pattern:
- Use when:
- Avoid when:
- Example:
- Notes:
