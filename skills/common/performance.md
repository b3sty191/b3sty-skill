# Performance And Cleanup Rules

CPU hot paths, caches and indexes, staged waits, lifecycle cleanup, and keeping all of it direct. Bandwidth and event cost: `skills/common/network-performance.md`; how to measure: `skills/common/debugging.md` -> Performance Debugging. Core event-security rules and the index of every section named "above"/"below": `skills/common/security-performance.md` -> Contents.

## Performance Rules

- Caches: trade RAM for CPU only on hot paths or expensive repeated work - FXServer is often limited by single-core CPU time, but RAM is not free and bad caches create leaks or GC pressure. Precompute indexes, normalized config, lookup maps, encoded data, and reusable results when the saved CPU is worth the memory; never cache cold-path data or values cheaper to recompute, and never rescan data every tick just to save a little memory. Every cache needs an owner, a reason to exist, and a cleanup path - clear the ones tied to player/resource lifetime so memory cannot grow forever.
- Loops: avoid `Wait(0)` unless the logic must run every frame. Staged/adaptive waits:
  - Far or idle state: `Wait(1000)` or more.
  - Nearby polling: `Wait(500)`.
  - Active checks: `Wait(100)` or more.
  - Frame controls/draw calls only: `Wait(0)`.
- Prefer event/state-bag driven updates over always-running loops; do not scan all players, all entities, or all pending requests every tick unless the list is small and the interval long.
- Inside loops, cache repeated natives and table lookups in locals: no repeated `PlayerPedId()`, `GetEntityCoords()`, `GetPlayerPed(...)`, or large table scans when a local value is enough.
- Lookups: build reverse indexes once for large config lists (`Items["INDEX"][name] = index`, same for `Jobs` and `Weapons`) and read them directly - O(1) maps instead of `for` loops scanning for one entry by name, ID, category, hash, or source.
- Require only the config modules the current script uses; do not eager-load large config files into scripts that do not need them.
- Keep hot-loop payloads and state-bag data small; network cost, latent events, and rate limits are in `skills/common/network-performance.md`.
- `GetGamePool('CVehicle')` (and `CPed`, `CObject`, `CPickup`) walks the whole pool; never call it every frame. Scan on a slow timer, or track only entities you created or that entered a zone.
- No allocation in per-frame loops: no new tables, closures, string concatenation, or `json.encode` per iteration. Reuse a table, or build it only when something changed.
- Resolve hashes once: backtick literals or `joaat` at load time, never `GetHashKey` inside a loop.
- Long server loops (all players, big tables) yield with `Wait(0)` every N iterations so one resource cannot stall the server tick.

## Cleanup

- On player drop or resource stop, clean entities, objects, peds, vehicles, blips, zones, NUI focus, timers, callback entries, throttle tables, queue entries, state bags, local state, and player caches.
- Guard entity cleanup with `DoesEntityExist`.
- Increment timer IDs or use cancellation guards when delayed timers may outlive the player/resource state they were created for.
- In loops over many players, wrap per-player work defensively so one bad player state cannot stop the whole loop.

## Anti-Overengineering

- No new framework, class system, event dispatcher, or generic module loader for a small resource.
- Security checks and performance caches stay direct and local unless the same pattern is reused enough to justify a helper.
- One clear validation block beats a generic validator that hides what the event accepts; one clear cleanup function beats many tiny cleanup abstractions in a small resource.
