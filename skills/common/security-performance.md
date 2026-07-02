# Security And Performance Rules

Use these rules for RedM/FiveM resources where player input, server state, entities, database writes, callbacks, or loops are involved.

## Priority

- Security and performance are core requirements, not cleanup tasks.
- Keep the b3sty style: direct, readable, hardcode-friendly code is fine, but do not sacrifice validation or runtime cost.
- Keep security/performance checks direct and local; do not build a framework or generic layer around them.

## Server Authority

- The server must be the source of truth for money, items, jobs, groups, permissions, ownership, rewards, cooldowns, and saved player data.
- Client code may request an action, render UI, play effects, attach objects, or apply optimistic local state.
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

## Required Event Pattern

```lua
local ACTION_THROTTLE = {}
local ITEM_INDEX = Items["INDEX"]
local ITEM_LIST = Items["LIST"]

local function IsActionThrottled(source, key, limit)
    local now = GetGameTimer()
    local playerThrottle = ACTION_THROTTLE[source]
    if not playerThrottle then
        playerThrottle = {}
        ACTION_THROTTLE[source] = playerThrottle
    end

    if now - (playerThrottle[key] or 0) < limit then
        return true
    end

    playerThrottle[key] = now
    return false
end

RegisterNetEvent("resource_name:server:action", function(payload)
    local source = source
    if not source or source <= 0 then return end
    if type(payload) ~= "table" then return end

    if IsActionThrottled(source, "action", 500) then return end

    local item = payload["Item"]
    local amount = tonumber(payload["Amount"])

    if type(item) ~= "string" or item == "" then return end
    if not amount or amount ~= amount then return end

    amount = math.floor(amount)
    if amount <= 0 or amount > 100 then return end

    local itemIndex = ITEM_INDEX[item]
    local itemData = itemIndex and ITEM_LIST[itemIndex]
    if not itemData then return end

    -- permission, ownership, cooldown, and action checks go here
end)

AddEventHandler("playerDropped", function()
    local src = source
    if src then
        ACTION_THROTTLE[src] = nil
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

## Sync Safety

- State bags are fine for visual state, but important state must be changed server-side.
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

## Database And Persistence

- Use parameterized SQL queries only.
- Avoid string-building SQL with user input.
- Track dirty fields for large player data.
- Save only changed JSON fields when possible.
- Debounce autosaves instead of saving on every small mutation.
- Use retry windows for failed saves.
- On resource stop or player drop, force-save dirty player state.
- Do not run a database write every tick or every client update.
- See `memory/common/cfx-patterns.md` -> Player Persistence Pattern for a concrete RAM-cache + spread-autosave + force-save shape.

## Logging And Secrets

- Log rejected security-sensitive actions with enough context to debug, but do not log secrets.
- Redact fields whose names include `password`, `secret`, `token`, `apikey`, `authorization`, `bearer`, `cookie`, `webhook`, or `licensekey`.
- Bound log payload depth, string length, item count, and key count.
- Queue and batch logs instead of sending a request per event.
- Cap queue size and drop or compact safely when the queue is too large.
- Store real tokens and webhook keys in server convars, never in client/shared files.

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
- Does this event need a throttle or cooldown?
- Does this callback/event clean up pending state on disconnect?
- Is any secret or webhook visible to the client?
- Is this loop always necessary, or can it be event-driven?
- Is any hot path scanning a large table repeatedly?
- Can this data be indexed once and read O(1)?
- Are database writes debounced and dirty-tracked?
- Are log payloads bounded and redacted?
