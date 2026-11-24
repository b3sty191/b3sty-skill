# Cfx Patterns

Reusable FXServer/CfxLua patterns, for both RedM and FiveM unless noted.

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
- Save Sequence Guard Pattern
- Linked Trade Save Pattern
- Build-Aside Reload Pattern
- Net Event Guard Injection Pattern
- Template

## Table Controller Pattern

- Pattern: keep resource state and methods in one local table.
- Use when: a resource needs shared indexes, active entities, cached data, or lifecycle methods.
- Example:
  ```lua
  local Controller = { ["Visible"] = "all", ["Players"] = {} }

  function Controller:Initialize()
      self.ObjectsIndex = {}
  end
  ```
- Notes: keeps the flow direct instead of wrapping a small resource in a framework.

## Index Map Pattern

- Pattern: a sorted list plus a reverse lookup table.
- Use when: synced state should carry small indexes instead of long object names.
- Also use when: code loops a list repeatedly to find one entry by name, ID, hash, category, or source.
- Example:
  ```lua
  function Controller:BuildObjectIndex(objects)
      self.ObjectsIndex, self.ObjectsIndexKey = {}, {}

      for objectName in pairs(objects) do self.ObjectsIndex[#self.ObjectsIndex + 1] = objectName end
      table.sort(self.ObjectsIndex)

      for index, objectName in ipairs(self.ObjectsIndex) do self.ObjectsIndexKey[objectName] = index end
  end
  ```
- Notes: fits inventory items, object attachers, clothing sets, other editable data maps.
- Notes: in hot paths, direct lookup beats repeated `for` scans.

## State Bag Render Pattern

- Pattern: server changes `Player(source).state`, client listens and renders local entities.
- Use when: clients need to see visual state for nearby or known players.
- Example: server `Player(source).state:set("attach", attach, true)`, client `AddStateBagChangeHandler("attach", ...)`.
- Notes: keep validation and important state changes server-side.
- Notes: compatible with `setr sv_stateBagStrictMode true` - the replicated write happens on the server, clients only render from state.

## Local Attached Prop Pattern

- Pattern: server validates the item/action and syncs a small attach state; each client creates local non-networked props and attaches them to the relevant ped.
- Use when: props are cosmetic, attached, preview-only, or otherwise render-only.
- Avoid when: the prop is a shared gameplay entity - pickup, storage object, placed world object, blocker, persistent owned object.
- Example:
  ```lua
  -- Server, after validation:
  Player(source).state:set("attach", { ["1"] = true }, true)

  -- Client renders from state.
  local Controller = { ["AttachedProps"] = {} }   -- [bagName] = { object, ... }

  function Controller:ClearAttachState(bagName)
      for _, object in ipairs(self.AttachedProps[bagName] or {}) do
          if DoesEntityExist(object) then DeleteEntity(object) end
      end

      self.AttachedProps[bagName] = nil
  end

  AddStateBagChangeHandler("attach", nil, function(bagName, _, attachState)
      Controller:ClearAttachState(bagName)   -- cleared key: remove by bag name, the player may not resolve
      if type(attachState) ~= "table" then return end

      local player = GetPlayerFromStateBagName(bagName)
      if player == 0 then return end

      -- CreateObject(model, x, y, z, false, false, false), then AttachEntityToEntity(object,
      -- GetPlayerPed(player), boneIndex, ...); track each object in Controller.AttachedProps[bagName].
  end)
  ```
- Notes: clean props up on state removal, player stream-out/drop, and resource stop.
- Notes: a light reattach loop is acceptable for tracked props - attached objects can detach, stream out, or be deleted by the game.
- Notes: never treat a client-created local prop handle as proof of ownership, reward eligibility, or saved state.
- Notes: with strict state bag mode, never set replicated attach state from the client; send a validated server request and let the server write the bag.

## Event Naming Pattern

- Pattern: name events with the resource prefix and the handling side.
- Rule: every custom event is `resource_name:server:action` or `resource_name:client:action` (see `skills/common/resource-structure.md` -> Events).
- Concrete shape used in b3sty resources:
  ```lua
  RegisterNetEvent("resource_name:server:add", function(itemName, state) end)
  RegisterNetEvent("resource_name:client:playerDropped", function(playerId) end)
  ```

## Cleanup Pattern

- Pattern: delete local entities on `onResourceStop`, player drop, and disabled state.
- Use when: the resource creates objects, blips, zones, peds, vehicles, or temporary handles.
- Notes: guard deletes with `DoesEntityExist`. Full cleanup scope (blips, zones, NUI focus, timers, callbacks, throttles, caches, local state) is in `skills/common/performance.md` -> Cleanup.

## Simple Resource Pattern

- Pattern: keep small resources direct instead of adding framework-style layers.
- Use when: a resource has one clear domain and only a few client/server files.
- Avoid when: the same validation, cleanup, or indexing repeats enough to justify a helper.
- Notes: b3sty style prefers readable local flow over generic architecture.

## Config Split Pattern

- Pattern: simple shared values in `config.lua`, large datasets in `configs/*.lua`.
- Use when: a resource has many positions, zones, objects, categories, shops, rewards, or other long lists.
- Example:
  ```lua
  local locationsConfig = require("configs.locations")
  ```
- Notes: plain CfxLua `require` cannot load resource files (fails with "module 'configs.locations' not found"). This shape needs `@ox_lib/init.lua` in the manifest; without ox_lib use the cached `loadConfig` loader in `skills/common/style.md` -> Lua Style. Client-read configs must be listed in `files` either way.
- Notes: full rules in `skills/common/style.md` -> Config Splitting and `skills/common/fxserver.md`.

## Player Persistence Pattern

- Pattern: keep player state in RAM, dirty-track changes, spread autosave over time, force-save on leave/stop.
- Use when: a resource owns saved player data (money, inventory, jobs, stats) and must not block the main thread or lose much data on crash.
- Rule: full persistence rules (dirty tracking, debounce, parameterized SQL, no per-tick writes) are in `skills/common/security-performance.md` -> Database And Persistence.
- Concrete shape:
  ```lua
  local SAVE_QUERY = "UPDATE players SET data = ? WHERE identifier = ?"
  local MAX_SAVE_FAILS = 5

  local Controller = {
      ["PlayerData"] = {}, ["PlayerDirty"] = {}, ["PlayerSaving"] = {}, ["PlayerSaveFails"] = {},
  }

  -- Call from a thread: it awaits the write. `force` skips the in-flight guard (final save on leave).
  function Controller:SavePlayer(source, force)
      if self.PlayerSaving[source] and not force then return end

      local data = self.PlayerData[source]
      if not data then return end

      self.PlayerSaving[source] = true
      self.PlayerDirty[source] = nil

      -- pcall + .await: with default oxmysql settings a callback-style query that errors never
      -- runs its callback, so the failure path below would be unreachable.
      local ok, affected = pcall(MySQL.update.await, SAVE_QUERY, { json.encode(data), data.identifier })
      self.PlayerSaving[source] = nil

      if ok and affected and affected > 0 then
          self.PlayerSaveFails[source] = nil
          return
      end

      -- Error, or 0 rows (no row for this identifier; `0` is truthy in Lua, so test it).
      print(("[%s] player save failed for %s: %s"):format(GetCurrentResourceName(),
          tostring(data.identifier),
          ok and "0 rows updated" or tostring(affected):match("([^\n]*)$"):sub(1, 120)))

      if not self.PlayerData[source] then return end   -- player already cleared

      local fails = (self.PlayerSaveFails[source] or 0) + 1
      self.PlayerSaveFails[source] = fails
      if fails < MAX_SAVE_FAILS then self.PlayerDirty[source] = true end   -- capped retry next pass
  end

  function Controller:ClearPlayer(source)
      self.PlayerData[source], self.PlayerDirty[source] = nil, nil
      self.PlayerSaving[source], self.PlayerSaveFails[source] = nil, nil
  end

  CreateThread(function()   -- spread autosave
      while true do
          Wait(60 * 1000)

          local dirty = {}   -- snapshot: never iterate/mutate PlayerDirty across a yield
          for source in pairs(Controller.PlayerDirty) do dirty[#dirty + 1] = source end

          for i = 1, #dirty do
              Controller:SavePlayer(dirty[i])
              Wait(50)   -- one player at a time, so a pass never stalls the main thread
          end
      end
  end)

  AddEventHandler("playerDropped", function()   -- primary save point, always issued
      local source = source
      if not Controller.PlayerData[source] then return end

      CreateThread(function()
          local waited = 0
          while Controller.PlayerSaving[source] and waited < 10000 do   -- let an in-flight autosave land first
              Wait(100)
              waited = waited + 100
          end

          Controller:SavePlayer(source, true)
          Controller:ClearPlayer(source)
      end)
  end)

  AddEventHandler("onResourceStop", function(resourceName)   -- restart/stop: one non-awaited batch, never yield
      if resourceName ~= GetCurrentResourceName() then return end

      local batch = {}
      for source in pairs(Controller.PlayerDirty) do
          local data = Controller.PlayerData[source]
          if data then batch[#batch + 1] = { json.encode(data), data.identifier } end
      end

      if #batch > 0 then MySQL.prepare(SAVE_QUERY, batch) end
  end)

  -- Gameplay code marks dirty inline: Controller.PlayerDirty[source] = true
  ```
- Notes: `.await` suspends only the calling thread, so saves never block the server; the crash window is one autosave interval - shorter = less loss, more DB load, 60-120s is sane.
- Notes: one shared `SavePlayer` (the autosave loop and `playerDropped` share its write, failure, and retry logic); snapshot + `Wait(50)` keeps the backlog bounded; `onResourceStop` cannot yield, so it batches its own non-awaited write with the same `SAVE_QUERY`; dirty marking is inlined - one line.
- Notes: never await in `onResourceStop` (abandoned at its first yield, so an awaited loop writes at most one player); for full shutdowns also save from txAdmin's `txAdmin:events:serverShuttingDown` (awaits are fine within its `delay`). Yield rules: `skills/common/runtime.md` -> Yield Hazards.
- Notes: failed or 0-row saves are logged and retried up to `MAX_SAVE_FAILS` (the next gameplay change re-marks dirty); use `INSERT ... ON DUPLICATE KEY UPDATE` if this resource owns row creation. This is the oxmysql API (`MySQL.update` / `MySQL.update.await`), not the legacy `MySQL.async.*` aliases - error-surfacing rules in `skills/common/database.md` -> OxMySQL API Shape.
- Notes: the drop save is ordered after any in-flight autosave (bounded 10s wait) and the cache is cleared only after it returns; a final save that still fails is logged and that data is lost. So a quick reconnect cannot load stale data, store `Controller.PendingDrop[identifier]` (the save promise) on drop and gate the loader on it:
  ```lua
  local waited = 0
  while Controller.PendingDrop[identifier] and waited < DROP_SAVE_TIMEOUT do
      Wait(250)
      waited = waited + 250
  end

  if Controller.PendingDrop[identifier] then
      deferrals.done("previous session is still being saved, retry shortly")
      return
  end
  ```
  Escalate while the save keeps missing the timeout: 1x free the memory/slot, 2x allow joins but refuse offline edits as busy (a save in flight would land on top of the edit), 4x let a join watchdog drop loads that never finish (an oxmysql await with no connection never returns), 10x give up with an ERROR log (verified: offline join/drop regression tests).
- Notes: after the drop row is written, wait one tick and write it again if a yielding `playerDropped` handler changed the data (at most twice). Never `pcall`-swallow a load failure and leave the player on the loading screen - refuse the join with a visible reason.

## Save Sequence Guard Pattern

- Pattern: every saved row carries a monotonic `save_seq BIGINT NOT NULL DEFAULT 0`, and each write refuses to land behind a newer one.
- Use when: saves of one row can overlap - a retry, a late autosave, a second process, an external saver.
- Avoid when: exactly one in-process writer ever touches the row.
- Example:
  ```lua
  -- Seed from max(DB, local KVP) and record the sequence before the write goes out, so a
  -- crash can never reuse a sequence.
  local stored = tonumber(GetResourceKvpString("seq:" .. identifier) or "0") or 0
  local seq = math.max(row.save_seq or 0, stored) + 1
  SetResourceKvp("seq:" .. identifier, tostring(seq))

  local affected = MySQL.update.await(
      "UPDATE users SET data = ?, save_seq = ? WHERE identifier = ? AND save_seq < ?",
      { json.encode(data), seq, identifier, seq })

  if affected == 0 then   -- superseded by a newer save: count it, never retry it
      Controller.Superseded = Controller.Superseded + 1
  end
  ```
- Notes: `NOT NULL DEFAULT 0` matters - with NULL, `save_seq < ?` is never true and that row never saves. Seeding from 0 instead of the stored max silently refuses every save after a relog.
- Notes: 0 affected rows means superseded, not failed: count it, warn at most once a minute, never retry. Every write changes `save_seq`, so the count is reliable whatever the client-found-rows connection flag is.
- Notes: a multi-row batch guards with `WHERE u.save_seq < v.save_seq`; when fewer rows matched than were sent, read the sequences back with one `SELECT ... IN (...)` to see which were refused (`MySQL.transaction` returns only true/false, never counts).
- Notes: gate joins while a sequence is still unconfirmed in SQL instead of loading an older row; a cache in front of SQL (Redis `appendfsync everysec`) acknowledging a write is not durability (verified: kill -9 harness at 512 players, `seq_regressions`, `dupe_*` and `loss_*` all 0).

## Linked Trade Save Pattern

- Pattern: when value moves between two owners, build both rows in the same frame and write them in one transaction.
- Use when: give, transfer, trade, drop + pickup, any third-party remove + add.
- Avoid when: the mutation changes one row only.
- Example:
  ```lua
  -- Same frame, no yield between the snapshots, so neither side can move on.
  local giverRow, receiverRow = Controller:BuildRow(giver), Controller:BuildRow(receiver)
  Controller.Linked[giver], Controller.Linked[receiver] = true, true   -- held out of the solo autosave lanes

  local ok = MySQL.transaction.await({ { SAVE_QUERY, giverRow }, { SAVE_QUERY, receiverRow } })

  Controller.Linked[giver], Controller.Linked[receiver] = nil, nil
  if not ok then Controller.PlayerDirty[giver], Controller.PlayerDirty[receiver] = true, true end
  ```
- Notes: saving the sides separately leaves a crash window - the receiver's new row with the giver's old row is a dupe, the reverse is a loss. Retries and sequence numbers cannot close it (verified: kill -9 harness, `item_delta` +7 at 512 players before the fix; 64-player runs were clean, so a small roster hides the bug).
- Notes: keep both players out of the solo autosave lanes until the group is written, or a solo lane commits half the pair.

## Build-Aside Reload Pattern

- Pattern: rebuild a shared catalog into a local table and swap it in with one assignment.
- Use when: reloading items, jobs, shops or any shared table from the database while players are online.
- Avoid when: the table is only read at startup, before any player is loaded.
- Example:
  ```lua
  function Controller:ReloadItems()
      local rows = MySQL.query.await("SELECT name, weight FROM items")
      if not rows or #rows == 0 then return end   -- keep the old catalog on failure

      local items = {}   -- built aside; self.Items stays readable during the await
      for i = 1, #rows do items[rows[i].name] = rows[i] end
      for name, item in pairs(self.PendingItems) do items[name] = item end   -- registered during the await

      self.PendingItems = {}
      self.Items = items   -- one assignment: no reader ever sees a partial table
  end
  ```
- Notes: clearing the live table before the await lets a reader see it empty, and an empty inventory can be saved over real data (verified: offline items regression test).
- Notes: push the change to online players as one shared diff, not each player's full inventory (300 items x 50 players: 1.04 MB -> 3.3 KB measured).

## Net Event Guard Injection Pattern

- Pattern: load one shared guard file as the first server script of every protected resource; it replaces `RegisterNetEvent` / `AddEventHandler` in that Lua state, so handlers stay untouched. The installer writes that line into each fxmanifest while it starts and runs `refresh`, so every resource ensured after it starts guarded.
- Use when: many resources need the same per-event rate limit / schema / signal path and editing every handler is impractical (verified 2026-10-13 against FXServer source 35945, FiveM build 3095).
- Avoid when: the resource is JS/C#, a system resource (`citizen/system_resources`), or registers its net events in `shared_scripts` - the guard never sees those.
- Example:
  ```
  # resources.cfg, above the installer's ensure
  add_ace resource.crest_skillissue command.refresh allow
  add_filesystem_permission crest_skillissue write crest_garage
  ensure crest_skillissue
  ```
- Notes (from source):
  - `add_filesystem_permission` is accepted only while the startup cfg runs (`FilesystemPermissions.cpp`); without it `SaveResourceFile` (returns nil) and Lua `io.open` writes into another resource are refused.
  - fxmanifest is read at scan time, not at start; `refresh` reloads the metadata of every known resource, started ones only take it on restart (`ServerResourceList.cpp`).
  - `@other/file.lua` resolves from disk for any scanned resource, started or not (`ScriptHost.cpp` OpenHostFile; mounts in `ServerResources.cpp` after each scan).
  - `ExecuteCommand` runs synchronously under principal `resource.<name>`: grant `add_ace resource.<name> command.<cmd> allow` (`ResourceScriptFunctions.cpp`).
  - `shared_scripts` load before `server_scripts` (`ResourceScriptingComponent.cpp`).
  - Server-local `TriggerEvent` has `source == ""`; `internal-net:` events such as `playerDropped` get a numeric `source` like client events, so wrap only names the resource `RegisterNetEvent`s, not every `AddEventHandler` (`scheduler.lua` event routine).
  - Resources started before the installer (its dependencies, or anything ensured earlier) take the guard only on their next full start; an installer with no dependencies, ensured first, covers everything on the same boot.
  - One wrapper per handler double-charges limits when a resource has 2+ handlers on one event: register one raw handler per event and fan out, each in its own `Citizen.CreateThreadNow` like the scheduler.
  - Reference implementation with offline tests: `txData/Script/examples/crest_skillissue` (example copy outside `resources/`: `guard.lua`, `core/installer.lua`, `DOCS.md` guard section, `lua5.4 tests/run.lua`).

## Template

Copy this block when adding a new entry, then fill it in. Leave it blank intentionally - it is a skeleton for future patterns, not a real pattern.

- Pattern:
- Use when:
- Avoid when:
- Example:
- Notes:
