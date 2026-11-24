# Performance And Cleanup Rules

CPU hot paths, caches and indexes, staged waits, lifecycle cleanup, and keeping all of it direct. Bandwidth and event cost are in `skills/common/network-performance.md`; how to measure is in `skills/common/debugging.md` -> Performance Debugging. The core event-security rules, and the index of every section a rule below names as "above" or "below", are in `skills/common/security-performance.md` -> Contents.

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
- Keep hot-loop payloads and state-bag data small; network cost, latent events, and rate limits are in `skills/common/network-performance.md`.
- `GetGamePool('CVehicle')` (and `CPed`, `CObject`, `CPickup`) walks the whole pool; never call it every frame. Scan on a slow timer, or track only entities you created or that entered a zone.
- Do not allocate in per-frame loops: no new tables, closures, string concatenation, or `json.encode` per iteration. Reuse a table or build it only when something changed.
- Resolve hashes once: backtick literals or `joaat` at load time, not `GetHashKey` inside a loop.
- Long server loops (all players, big tables) yield with `Wait(0)` every N iterations so one resource cannot stall the server tick.
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

