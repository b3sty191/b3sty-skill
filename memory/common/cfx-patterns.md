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
  local Controller = {
      ["AttachedProps"] = {},   -- [bagName] = { object, ... }
  }

  function Controller:ClearAttachState(bagName)
      local props = self.AttachedProps[bagName]
      if not props then return end

      for i = 1, #props do
          if DoesEntityExist(props[i]) then
              DeleteEntity(props[i])
          end
      end

      self.AttachedProps[bagName] = nil
  end

  function Controller:RenderAttachState(bagName, player, attachState)
      self:ClearAttachState(bagName)
      -- CreateObject(model, x, y, z, false, false, false)
      -- AttachEntityToEntity(object, GetPlayerPed(player), boneIndex, ...)
      -- Track each object in self.AttachedProps[bagName] so cleanup can find it.
  end

  AddStateBagChangeHandler("attach", nil, function(bagName, _, attachState)
      -- Cleared key: remove props by bag name, even if the player no longer resolves.
      if type(attachState) ~= "table" then
          Controller:ClearAttachState(bagName)
          return
      end

      local player = GetPlayerFromStateBagName(bagName)
      if player == 0 then return end

      Controller:RenderAttachState(bagName, player, attachState)
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
- Notes: plain CfxLua `require` cannot load resource files (fails with "module 'configs.locations' not found"). This shape needs `@ox_lib/init.lua` in the manifest; without ox_lib use the cached `loadConfig` loader in `skills/common/style.md` -> Lua Style. Client-read configs must be listed in `files` either way.
- Notes: full rules in `skills/common/style.md` -> Config Splitting and `skills/common/fxserver.md`.

## Player Persistence Pattern

- Pattern: keep player state in RAM, dirty-track changes, spread autosave over time, and force-save on leave/stop.
- Use when: a resource owns saved player data (money, inventory, jobs, stats) and must not block the main thread or lose much data on crash.
- Rule: full persistence rules (dirty tracking, debounce, parameterized SQL, no per-tick writes) are in `skills/common/security-performance.md` -> Database And Persistence.
- Concrete shape:
  ```lua
  -- RAM cache + dirty tracking + spread autosave + force-save on exit.
  -- Non-blocking (`.await` only suspends the calling thread); never lose more than the autosave interval on crash.
  local SAVE_QUERY = "UPDATE players SET data = ? WHERE identifier = ?"
  local MAX_SAVE_FAILS = 5

  local Controller = {
      ["PlayerData"] = {},
      ["PlayerDirty"] = {},
      ["PlayerSaving"] = {},
      ["PlayerSaveFails"] = {},
  }

  -- Call from a thread: it awaits the write. `force` skips the in-flight guard (final save on leave).
  function Controller:SavePlayer(source, force)
      if self.PlayerSaving[source] and not force then return end

      local data = self.PlayerData[source]
      if not data then return end

      self.PlayerSaving[source] = true
      self.PlayerDirty[source] = nil

      -- pcall + .await: with default oxmysql settings a callback-style query that errors
      -- never runs its callback, so the failure path below would be unreachable.
      local ok, affectedRows = pcall(MySQL.update.await, SAVE_QUERY, {
          json.encode(data), data.identifier,
      })
      self.PlayerSaving[source] = nil

      if ok and affectedRows and affectedRows > 0 then
          self.PlayerSaveFails[source] = nil
          return
      end

      -- Query error, or 0 rows (no row for this identifier; `0` is truthy in Lua, so check it explicitly).
      print(("[%s] player save failed for %s: %s"):format(
          GetCurrentResourceName(), tostring(data.identifier),
          ok and "0 rows updated" or tostring(affectedRows):match("([^\n]*)$"):sub(1, 120)
      ))

      if not self.PlayerData[source] then return end   -- player already cleared

      local fails = (self.PlayerSaveFails[source] or 0) + 1
      self.PlayerSaveFails[source] = fails

      if fails < MAX_SAVE_FAILS then
          self.PlayerDirty[source] = true   -- capped retry on the next autosave pass
      end
  end

  function Controller:ClearPlayer(source)
      self.PlayerData[source] = nil
      self.PlayerDirty[source] = nil
      self.PlayerSaving[source] = nil
      self.PlayerSaveFails[source] = nil
  end

  -- Spread autosave: snapshot the dirty set, then save one player at a time with a small
  -- yield between players so one pass never stalls the main thread and the backlog cannot
  -- grow unbounded. Never mutate/iterate PlayerDirty across a yield without a snapshot.
  CreateThread(function()
      while true do
          Wait(60 * 1000)

          local dirty = {}
          for source in pairs(Controller.PlayerDirty) do
              dirty[#dirty + 1] = source
          end

          for i = 1, #dirty do
              Controller:SavePlayer(dirty[i])
              Wait(50)
          end
      end
  end)

  -- Final save on leave (primary save point). Always issued: wait (bounded) for an
  -- in-flight autosave so its older snapshot cannot commit last, then force-save and clear.
  AddEventHandler("playerDropped", function()
      local source = source
      if not Controller.PlayerData[source] then return end

      CreateThread(function()
          local waited = 0
          while Controller.PlayerSaving[source] and waited < 10000 do
              Wait(100)
              waited = waited + 100
          end

          Controller:SavePlayer(source, true)
          Controller:ClearPlayer(source)
      end)
  end)

  -- Force-save all dirty players when this resource stops (covers restart/stop).
  -- Never yield here: the resource is torn down at the first yield, so an awaited loop
  -- writes at most one player. Dispatch one non-awaited batch; oxmysql finishes it.
  AddEventHandler("onResourceStop", function(resourceName)
      if resourceName ~= GetCurrentResourceName() then return end

      local batch = {}
      for source in pairs(Controller.PlayerDirty) do
          local data = Controller.PlayerData[source]

          if data then
              batch[#batch + 1] = { json.encode(data), data.identifier }
          end
      end

      if #batch > 0 then
          MySQL.prepare(SAVE_QUERY, batch)
      end
  end)

  -- Gameplay code marks a player dirty inline wherever state changes:
  --   Controller.PlayerDirty[source] = true
  ```
- Notes: interval is a trade-off - shorter = less data loss but more DB load; 60-120s is a sane default.
- Notes: `Controller:SavePlayer` is kept as a method because the autosave loop and `playerDropped` share its write, failure, and retry logic (real duplication); `onResourceStop` cannot yield, so it batches its own non-awaited write with the shared `SAVE_QUERY`. Dirty marking is inlined because it is one line.
- Notes: never await in `onResourceStop` (the handler is abandoned at its first yield); dispatch one non-awaited batch there, and for full shutdowns also save from txAdmin's `txAdmin:events:serverShuttingDown` (awaits are fine within its `delay`). Yield rules: `skills/common/runtime.md` -> Yield Hazards.
- Notes: failed or 0-row saves are logged and retried up to `MAX_SAVE_FAILS` (the next gameplay change marks the player dirty again); error-surfacing rules are in `skills/common/database.md` -> OxMySQL API Shape. Use `INSERT ... ON DUPLICATE KEY UPDATE` if this resource owns row creation.
- Notes: on `playerDropped` the final save is always issued, ordered after any in-flight autosave (bounded 10s wait), and the RAM cache is cleared only after it returns. A final save that still fails is logged and that data is lost. If a quick reconnect must never load stale data, have the loader wait while a final save for that identifier is still pending.
- Notes: uses the oxmysql API (`MySQL.update` / `MySQL.update.await`), not the legacy `MySQL.async.*` aliases - see `skills/common/database.md` -> OxMySQL API Shape.

## Template

Copy this block when adding a new entry, then fill it in. Leave it blank intentionally - it is a skeleton for future patterns, not a real pattern.

- Pattern:
- Use when:
- Avoid when:
- Example:
- Notes:
