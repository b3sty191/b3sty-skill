# CFX Runtime And Async Rules

Use this file for FXServer/CitizenFX runtime behavior that is not native-specific: threads and waits, the `source` magic variable, exports and references, identifiers, convars, resource lifecycle, yield hazards, and game builds.

These are the mechanics every RedM/FiveM Lua author hits. Native call mechanics are in `skills/common/native-usage.md`; multiplayer/OneSync behavior is in `skills/common/networking.md`.

## Contents

- Threads And Waits
- The `source` Variable
- Exports And Stale References
- Players And Identifiers
- Convars
- Resource Lifecycle
- Yield Hazards
- Game Builds
- Debugging
- Review Questions

## Threads And Waits

- `CreateThread(function() ... end)` starts a coroutine thread. A thread that never `Wait`s blocks the resource's main thread (and on the server, the shared Lua runtime) until it returns.
- `Wait(ms)` yields the current thread. `Wait(0)` yields one frame and resumes next frame. A loop without `Wait` is a busy loop that stalls the runtime.
- Use staged waits by distance/activeness (idle `Wait(1000)+`, nearby `Wait(500)`, active `Wait(100)`, frame work `Wait(0)`); see `skills/common/security-performance.md` -> Performance Rules.
- `Citizen.Wait`, `Citizen.Await`, and `Citizen.CreateThreadNow` exist for specific cases; default to `Wait`/`CreateThread`. `Citizen.Await` is for awaiting a future-like value inside a thread.
- Do not leave per-frame (`Wait(0)`) threads running when the work is idle. Gate them by distance or state and let idle threads sleep long.
- A thread started inside a resource keeps running until it ends or the resource stops; start long-lived loops explicitly and ensure they have an exit path.

## The `source` Variable

- `source` is an implicit event variable: the player source (server) or the net event sender. It is only meaningful inside event/callback handlers.
- Capture it before any yield:
  ```lua
  RegisterNetEvent("resource_name:server:action", function()
      local source = source
      -- safe to Wait / await here; `source` is now a stable local
  end)
  ```
- After a yield, the implicit `source` can be stale/invalid. Re-validate with `GetPlayer(source)`, `DoesPlayerExist`, or `source` bounds after yielding before mutating state.
- Never accept a `source` value from a client payload as identity. Real `source` comes from the runtime, not the data. See Players And Identifiers.

## Exports And Stale References

- `exports['resource_name']:method(...)` calls another resource's export. The exports table is a runtime proxy; calling it each time always reaches the current code.
- The staleness gotcha is caching the result of an export call that returns a shared object:
  ```lua
  local ESX = exports['es_extended']:getSharedObject()   -- captured once at load
  ```
  If the providing resource restarts, `ESX` may still reference the old object/code while the rest of the server uses the new one. After a framework restart, prefer re-fetching the shared object over trusting a load-time local.
- For the same reason, do not assume `exports['name']` is non-nil at load. The provider may not have started yet. Check `GetResourceState('name')` or gate the call on `onResourceStart`/`onServerResourceStart`.
- See `skills/common/multi-resource.md` -> Dependencies And Load Order for declaring dependencies instead of racing with `Wait`.

## Players And Identifiers

- `GetPlayerIdentifiers(source)` returns a table of identifiers. Verified types: `steam` (hex), `discord` (int), `xbl` (int), `live` (Microsoft PUID), `license`/`license2` (ROS hash - `license2` can equal `license` for Steam users), `fivem` (Cfx user id), `ip` (IPv4 string). Availability depends on the server/client link. ([GetPlayerIdentifiers](https://docs.fivem.net/docs/scripting-reference/runtimes/lua/functions/GetPlayerIdentifiers/))
- `GetPlayerIdentifierByType(source, "license")` returns a single identifier when that is all you need.
- `license:` (the player's Rockstar/Cfx license) is the usual stable primary key across sessions. Pick one identifier scheme and keep it server-side.
- Identity is only reliable server-side. Never trust an identifier sent by the client in an event payload; identity comes from `GetPlayerIdentifiers(source)` on the server, keyed by the runtime `source`. Do not trust a single identifier type in isolation - `ip` is weak (shared NAT, rotates), so ban/whitelist on the strongest available identifier (commonly `license`).
- Run ban/whitelist and auth checks during `playerConnecting` using the `deferrals` API (`defer`, `update`, `done` called exactly once) for async DB/license lookups, not after the player is in-game. Tune trust with `sv_authMinTrust` (1-5, spoof-resistance) and `sv_authMaxVariance` (1-5, stability per provider). ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/))
- `GetPlayer(source)`, `GetPlayerName(source)`, `GetPlayerPed(source)`, `GetPlayerPing(source)` read server-side player state. `GetPlayers()` returns connected sources (also see the player state bag API in `skills/common/resource-structure.md`).
- Validate `source` is a real connected player before using it (`source > 0` and the player exists), especially after a yield.
- See `skills/common/security-performance.md` -> Identifier Trust for the full trust rules.

## Convars

- `GetConvar(name, default)` and `GetConvarInt(name, default)` read convars. Always pass a default. ([convars](https://docs.fivem.net/docs/scripting-reference/convars/))
- Exposure by command:
  - `set name value` — standard convar, server-side only; clients cannot read or set it.
  - `setr name value` — server replicated; readable by clients via `GetConvar`, changeable only server-side. Anything in `setr` is public to clients.
  - `sets name "value"` — server information; exposed publicly in `info.json` and the server list. Never use `sets` for anything sensitive.
- In resources, `SetConvar`, `SetConvarReplicated`, and `SetConvarServerInfo` mirror the three commands; standard convars can only be used in server scripts.
- Keep secrets (tokens, webhook keys, DB credentials) in server-only `set` convars or env, never in `setr`/`sets` or shared/client files. See `skills/common/security-performance.md` -> Config, Convars, And Secrets.
- Do not read a convar every frame; read it once on load and when a config-change reload path runs.

## Resource Lifecycle

- `ensure` in `server.cfg` starts the resource and restarts it if it crashes. `start` starts it once. Use `ensure` for resources that must stay up.
- Load order follows declaration order. Declare dependencies with `dependency`/`dependencies` in `fxmanifest.lua` and check `GetResourceState` for optional ones instead of guessing with `Wait`.
- Resource events:
  - `onResourceStart(resource)` — fires on both sides when a resource starts, including this one.
  - `onResourceStarting(resource)` — fires before start; useful to set up before another resource initializes.
  - `onResourceStop(resource)` — fires on both sides; guard with `resourceName == GetCurrentResourceName()`.
  - `onServerResourceStart(resource)` / `onServerResourceStop(resource)` — server-side, fired for other resources starting/stopping.
- When a provider resource restarts, callers holding a cached export result or a pending callback can go stale. Re-fetch references and clear pending state. See Exports And Stale References and `skills/common/security-performance.md` -> Callback Safety.
- See `skills/common/multi-resource.md` -> Failure Handling for degrading cleanly when a dependency is absent.

## Yield Hazards

- Do not yield (no `Wait`, no `MySQL.*.await`, no async export) inside `entityCreating`. The handler gates creation; long or yielding work can stall replication or time out the network request. Move heavy work to a thread keyed by the handle.
- In `playerConnecting`, do not block. Use the `deferrals` API (`defer`, `update`, `done`, `handover`) to run async checks (DB, license, whitelist) and call `deferrals.done()` exactly once.
- Avoid yielding between a validation check and a valuable mutation. Check-and-mutate atomically; otherwise recheck after the yield. See `skills/common/security-performance.md` -> Atomic State Changes And Replay Protection.
- `MySQL.*.await` calls are blocking awaits within their coroutine; on the server they must run in a coroutine context (a thread or event handler), not the synchronous startup path.

## Game Builds

- The running game build affects which natives are available and how some behave. Compare `GetGameBuildNumber()` against a native's minimum build before relying on newer natives; the server's `sv_enforceGameBuild` sets the enforced build (startup-only). ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/))
- FiveM (GTA V) enforceable builds (as of the current docs): `1604, 2060, 2189, 2372, 2545, 2612, 2699, 2802, 2944, 3095, 3258, 3407, 3570, 3751` - each includes all prior content.
- RedM (RDR3): `1491` is the current enforceable build (September 2022 update); older defaults like `1311`/`1355`/`1436` existed historically.
- Always confirm the live list against the current artifact, since new builds are added over time.
- Guard optional newer-build natives with a build check and an explicit fallback rather than letting them fail silently on older servers.
- When behavior differs by build, record the build number in the `memory/` entry.

## Debugging

- A "resource hangs" or "server freezes" symptom is almost always a thread that never yields or a synchronous `MySQL.*.await` on the main path.
- A "works only sometimes" event bug is usually a stale `source` read after a yield, or a provider resource that restarted under cached references.
- Confirm load order and `GetResourceState` for cross-resource calls before assuming an export is broken.
- See `skills/common/debugging.md` for the general flow.

## Review Questions

- Does every loop yield, and do idle loops sleep long instead of `Wait(0)`?
- Is `source` captured before any yield and re-validated after?
- Are load-time export results re-fetched if their provider can restart?
- Does identity come from `GetPlayerIdentifiers(source)` on the server, never from client data?
- Are convars read once (not per frame) and secrets kept server-only?
- Is heavy/async work kept out of `entityCreating`, and `playerConnecting` deferred properly?
- Are newer-build natives gated with a build check and fallback?
