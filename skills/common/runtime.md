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

- `CreateThread(function() ... end)` starts a cooperative coroutine that nothing preempts. Each resource has its own Lua state, but every resource runs on the same main thread (the client game thread or the server main thread). A thread that never `Wait`s therefore freezes the whole client game or server tick, not just its own resource, until it returns.
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
- After a yield, the captured `source` can be stale: the player may have dropped, so natives on that ID return nil, 0 (truthy in Lua), or an empty table (see Players And Identifiers). Server IDs come from a 16-bit counter (1-65534) that wraps back to 1 and skips IDs still in use, so an ID is reused only after ~65k further joins: practically never within one yield, but a `source` kept in a table not cleared on `playerDropped` can map to a different player on a long-running server. During `playerConnecting`, `source` is a temporary ID (65536 and up) that is replaced when the player joins (`playerJoining` receives it as `oldID`), so do not key state by it past the handshake. Re-validate after yielding (`DoesPlayerExist(source)`, or the framework's `GetPlayer(source)`), and for valuable mutations compare an identifier captured before the yield (e.g. `license`) against the current one before applying.
- Never accept a `source` value from a client payload as identity. Real `source` comes from the runtime, not the data. See Players And Identifiers.

## Exports And Stale References

- `exports['resource_name']:method(...)` calls another resource's export. The exports table is a runtime proxy; calling it each time always reaches the current code.
- The staleness gotcha is caching the result of an export call that returns a shared object:
  ```lua
  local ESX = exports['es_extended']:getSharedObject()   -- captured once at load
  ```
  If the providing resource restarts, `ESX` may still reference the old object/code while the rest of the server uses the new one. After a framework restart, prefer re-fetching the shared object over trusting a load-time local.
- Do not guard with `if exports['name'] then`. The exports proxy is never nil, and indexing a method on a provider that has not started (or has no such export) throws `No such export <method> in resource <name>`. Check `GetResourceState('name') == 'started'` before calling, wrap the call in `pcall(function() return exports['name']:method(...) end)`, or make the call from `onResourceStart`/`onServerResourceStart` for that resource.
- See `skills/common/multi-resource.md` -> Dependencies And Load Order for declaring dependencies instead of racing with `Wait`.

## Players And Identifiers

- `GetPlayerIdentifiers(source)` returns a table of identifiers. Verified types: `steam` (hex), `discord` (int), `xbl` (int), `live` (Microsoft PUID), `license`/`license2` (ROS hash - `license2` can equal `license` for Steam users), `fivem` (Cfx user id), `ip` (IPv4 string). Availability depends on the server/client link. ([GetPlayerIdentifiers](https://docs.fivem.net/docs/scripting-reference/runtimes/lua/functions/GetPlayerIdentifiers/))
- `GetPlayerIdentifierByType(source, "license")` returns a single identifier when that is all you need.
- For a stable primary key across sessions, prefer `license2` when present and fall back to `license` (`GetPlayerIdentifierByType(source, "license2") or GetPlayerIdentifierByType(source, "license")`). Pick one identifier scheme and keep it server-side; if a DB is already keyed by `license`, keep that key stable instead of switching schemes mid-life.
- Identity is only reliable server-side. Never trust an identifier sent by the client in an event payload; identity comes from `GetPlayerIdentifiers(source)` on the server, keyed by the runtime `source`. Do not trust a single identifier type in isolation - `ip` is weak (shared NAT, rotates), so ban/whitelist on the strongest available identifier (`license2`, else `license`).
- Run ban/whitelist and auth checks during `playerConnecting` using the `deferrals` API (`defer`, `update`, `done` called exactly once) for async DB/license lookups, not after the player is in-game. `sv_authMinTrust` is effectively a no-op: FXServer compares it against the highest trust among a player's identifiers, and the always-present `ip:` identifier reports trust 5. `sv_authMaxVariance` (1-5, default 5) is the one that matters: it is compared against the lowest variance, where `license`/`steam` report 1 and `ip` reports 5, so any value below 5 rejects players with no `license`/`steam` identifier. ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/), FXServer `InitConnectMethod.cpp`/`EndPointIdentityProvider.cpp`)
- `GetPlayerName(source)`, `GetPlayerPed(source)`, `GetPlayerPing(source)` read server-side player state; `DoesPlayerExist(source)` checks existence, and `GetPlayers()` returns connected sources (also see the player state bag API in `skills/common/resource-structure.md`). `GetPlayer(...)` is a framework function (ESX/QBCore/VORP style), not a CFX native - do not use it as an existence check in framework-free code.
- Do not use `GetPlayerIdentifiers(source)` as an existence check; it returns a table (truthy even when empty) for invalid IDs. Use `GetPlayerName`/`DoesPlayerExist`.
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

- `ensure name` starts the resource if it is stopped, or restarts it if it is already running. That makes it safe to repeat in `server.cfg` and useful as a quick reload in the console. `start name` only starts a stopped resource. Neither command watches for crashes or restarts anything automatically: a script error does not stop a resource, and a stopped resource stays stopped until someone starts it again.
- Load order follows declaration order. Declare dependencies with `dependency`/`dependencies` in `fxmanifest.lua` and check `GetResourceState` for optional ones instead of guessing with `Wait`.
- Resource events:
  - `onResourceStart(resource)` — fires on both sides when a resource starts, including this one.
  - `onResourceStarting(resource)` — fires before start; useful to set up before another resource initializes.
  - `onResourceStop(resourceName)` — fires on both sides for every stopping resource. Guard with `if resourceName ~= GetCurrentResourceName() then return end`, using the handler's own parameter name.
  - `onServerResourceStart(resource)` / `onServerResourceStop(resource)` — server-only counterparts of `onClientResourceStart`/`onClientResourceStop`. They are queued (they run on a later tick) instead of firing immediately like `onResourceStart`, and they fire for every resource, including this one on start. Guard with `resource == GetCurrentResourceName()` when you only care about your own resource.
- When a provider resource restarts, callers holding a cached export result or a pending callback can go stale. Re-fetch references and clear pending state. See Exports And Stale References and `skills/common/security-performance.md` -> Callback Safety.
- See `skills/common/multi-resource.md` -> Failure Handling for degrading cleanly when a dependency is absent.

## Yield Hazards

- Do not yield (no `Wait`, no `MySQL.*.await`, no async export) inside `entityCreating`. The handler gates creation; long or yielding work can stall replication or time out the network request. Move heavy work to a thread keyed by the handle.
- In `playerConnecting`, do not block. Use the `deferrals` API (`defer`, `update`, `done`, `handover`) to run async checks (DB, license, whitelist) and call `deferrals.done()` exactly once.
- Avoid yielding between a validation check and a valuable mutation. Check-and-mutate atomically; otherwise recheck after the yield. See `skills/common/security-performance.md` -> Atomic State Changes And Replay Protection.
- `MySQL.*.await` yields (suspends) only the calling coroutine until the query finishes; it does not block the runtime or other threads. Because it yields, it must run in a coroutine context (a thread, an event handler, or file top level, where it defers the rest of the file), and it counts as a yield for every rule above.

## Game Builds

- The running game build affects which natives are available and how some behave. On the client, compare `GetGameBuildNumber()` against a native's minimum build before relying on newer natives. On the server, `GetGameBuildNumber()` returns 0, so read the enforced build with `GetConvarInt("sv_enforceGameBuild", 0)` instead. When the server does not set it, this returns the artifact's default build (for example 3258 on FiveM or 1491 on RedM), not 0. The server's `sv_enforceGameBuild` sets the enforced build (startup-only; DLC names like `mptuner` are stored as their build number). ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/))
- FiveM (GTA V) enforceable builds (fivem-docs `sv_enforceGameBuild` table, checked 2026-09): `1` (base game, no DLCs), `1604, 2060, 2189, 2372, 2545, 2612, 2699, 2802, 2944, 3095, 3258, 3407, 3570, 3751, 3889`. Each includes all prior content. Re-check the table before relying on this list.
- RedM (RDR3): `1491` is the current enforceable build (September 2022 update); older defaults like `1311`/`1355`/`1436` existed historically.
- Always confirm the live list against the current artifact, since new builds are added over time.
- Guard optional newer-build natives with a build check and an explicit fallback rather than letting them fail silently on older servers.
- When behavior differs by build, record the build number in the `memory/` entry.

## Debugging

- A "resource hangs" or "server freezes" symptom is almost always a loop that never yields (no `Wait`), or heavy synchronous computation or a blocking call on the main path. A top-level `MySQL.*.await` does not error: CfxLua runs each script file inside `CreateThreadNow`, so the await yields and the rest of that file (including handlers registered below it) runs only after the query returns, while later files load first. It errors only in non-yieldable contexts such as a `table.sort` comparator or `__gc` ("attempt to yield across a C-call boundary").
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
