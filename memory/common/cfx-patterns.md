# Cfx Patterns

Track reusable FXServer/CfxLua implementation patterns here. These apply to both RedM and FiveM unless noted.

## Contents

- Table Controller Pattern
- Index Map Pattern
- State Bag Render Pattern
- Local Attached Prop Pattern
- Event Naming Pattern
- Cleanup Pattern
- Simple Resource Pattern
- Config Split Pattern
- Player Persistence Pattern
- Template

## Table Controller Pattern

- Pattern: keep resource state and methods in one local table.
- Use when: a resource needs shared indexes, active entities, cached data, or lifecycle methods.
- Example:
  ```lua
  local Controller = {
      ["Visible"] = "all",
      ["Players"] = {},
  }

  function Controller:Initialize()
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
  local Controller = {}

  function Controller:BuildObjectIndex(objects)
      self.ObjectsIndex = {}
      self.ObjectsIndexKey = {}

      for objectName in pairs(objects) do
          table.insert(self.ObjectsIndex, objectName)
      end

      table.sort(self.ObjectsIndex)

      for index, objectName in ipairs(self.ObjectsIndex) do
          self.ObjectsIndexKey[objectName] = index
      end
  end
  ```
- Notes: useful for inventory items, object attachers, clothing sets, and other editable data maps.
- Notes: in hot paths, direct lookup is preferred over repeated `for` scans.

## State Bag Render Pattern

- Pattern: server changes `Player(source).state`, client listens and renders local entities.
- Use when: clients need to see visual state for nearby or known players.
- Example: server sets `Player(source).state:set("attach", attach, true)`, client uses `AddStateBagChangeHandler("attach", ...)`.
- Notes: keep validation and important state changes server-side.
- Notes: this pattern is compatible with `setr sv_stateBagStrictMode true` because the replicated state write happens on the server and clients only render from state.

## Local Attached Prop Pattern

- Pattern: server validates the item/action and syncs a small attach state; each client creates local non-networked props and attaches them to the relevant ped.
- Use when: props are cosmetic, attached, preview-only, or otherwise render-only.
- Avoid when: the prop is a shared gameplay entity such as a pickup, storage object, placed world object, blocker, or persistent owned object.
- Example:
  ```lua
  -- Server: after validation
  Player(source).state:set("attach", {
      ["1"] = true,
  }, true)

  -- Client: render from state
  local Controller = {}

  function Controller:RenderAttachState(player, attachState)
      -- CreateObject(model, x, y, z, false, false, false)
      -- AttachEntityToEntity(object, GetPlayerPed(player), boneIndex, ...)
  end

  AddStateBagChangeHandler("attach", nil, function(bagName, _, attachState)
      local player = GetPlayerFromStateBagName(bagName)
      if player == 0 or type(attachState) ~= "table" then return end

      Controller:RenderAttachState(player, attachState)
  end)
  ```
- Notes: local attached props need cleanup on state removal, player stream-out/drop, and resource stop.
- Notes: a light reattach loop is acceptable for tracked props because attached objects can detach, stream out, or be deleted by the game.
- Notes: never use a client-created local prop handle as proof of ownership, reward eligibility, or saved state.
- Notes: do not set replicated attach state from the client when strict state bag mode is enabled; send a validated server request and let the server update the state bag.

## Event Naming Pattern

- Pattern: name events with the resource prefix and the side that handles the event.
- Rule: every custom event is `resource_name:server:action` or `resource_name:client:action` (see `skills/common/resource-structure.md` -> Events).
- Concrete shape used in b3sty resources:
  ```lua
  RegisterNetEvent("resource_name:server:add", function(itemName, state)
      -- handled on server
  end)

  RegisterNetEvent("resource_name:client:playerDropped", function(playerId)
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
  local locationsConfig = require("configs.locations")
  local itemsConfig = require("configs.items")
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
  local Controller = {
      ["PlayerData"] = {},
      ["PlayerDirty"] = {},
      ["PlayerSaving"] = {},
  }

  function Controller:SavePlayer(source)
      if self.PlayerSaving[source] then return end

      local data = self.PlayerData[source]
      if not data then return end

      self.PlayerSaving[source] = true
      self.PlayerDirty[source] = nil

      MySQL.async.execute("UPDATE players SET data = ? WHERE identifier = ?", {
          json.encode(data), data.identifier,
      }, function()
          self.PlayerSaving[source] = nil
      end)
  end

  function Controller:ClearPlayer(source)
      self.PlayerData[source] = nil
      self.PlayerDirty[source] = nil
      self.PlayerSaving[source] = nil
  end

  -- Spread autosave: save at most 10 dirty players per 60s pass, then yield.
  CreateThread(function()
      while true do
          Wait(60 * 1000)
          local saved = 0

          for source in pairs(Controller.PlayerDirty) do
              if saved >= 10 then break end
              Controller:SavePlayer(source)
              saved += 1
          end
      end
  end)

  -- Force-save on leave (primary save point).
  AddEventHandler("playerDropped", function()
      local source = source

      if source then
          Controller:SavePlayer(source)
          Controller:ClearPlayer(source)
      end
  end)

  -- Force-save all dirty players when this resource stops (covers restart/stop).
  AddEventHandler("onResourceStop", function(resourceName)
      if resourceName ~= GetCurrentResourceName() then return end

      for source in pairs(Controller.PlayerDirty) do
          Controller:SavePlayer(source)
      end
  end)

  -- Gameplay code marks a player dirty inline wherever state changes:
  --   Controller.PlayerDirty[source] = true
  ```
- Notes: interval is a trade-off - shorter = less data loss but more DB load; 60-120s is a sane default.
- Notes: `Controller:SavePlayer` is kept as a method because it is used in three places (real duplication); dirty marking is inlined because it is one line.
- Notes: async queries are mandatory here - sync DB calls block the single FXServer Lua thread.

## Template

Copy this block when adding a new entry, then fill it in. Leave it blank intentionally - it is a skeleton for future patterns, not a real pattern.

- Pattern:
- Use when:
- Avoid when:
- Example:
- Notes:
