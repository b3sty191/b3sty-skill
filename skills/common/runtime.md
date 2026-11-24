# CFX Runtime And Async Rules

Use for FXServer/CitizenFX runtime behavior outside natives: threads and waits, the `source` magic variable, exports and references, identifiers, convars, resource lifecycle, yield hazards, game builds. Native call mechanics: `skills/common/native-usage.md`. Multiplayer/OneSync: `skills/common/networking.md`.

## Contents

Threads And Waits - The `source` Variable - Exports And Stale References - Players And Identifiers - Convars - Resource Lifecycle - Yield Hazards - Game Builds - Debugging - Review Questions

## Threads And Waits

- `CreateThread(function() ... end)` runs a cooperative coroutine nothing preempts. Resources have separate Lua states but share one main thread (client game thread / server main thread), so a thread that never `Wait`s freezes the whole client or server tick - not just its own resource - until it returns.
- `Wait(ms)` yields the thread, `Wait(0)` resumes next frame; a loop without `Wait` stalls the runtime. Stage waits by distance/activeness - idle `Wait(1000)+`, nearby `Wait(500)`, active `Wait(100)`, frame work `Wait(0)` (`skills/common/performance.md` -> Performance Rules) - and gate `Wait(0)` threads by distance or state so idle ones sleep long.
- `Citizen.Wait`, `Citizen.Await` (awaits a future-like value inside a thread) and `Citizen.CreateThreadNow` cover specific cases; default to `Wait`/`CreateThread`.
- Threads run until they return or the resource stops - start long-lived loops explicitly, with an exit path.
- `GetGameTimer()` is a live millisecond clock, not a per-tick timestamp: two reads in one handler can differ, and a GC pause widens the gap. Never pair or deduplicate events by `GetGameTimer()` equality - compare against a window, or bump a counter once per pass and match that. In-frame CPU budgets: `os.nanotime`/`os.clock`. (verified: offline kill -9 harness, 512 players - 71 of 680 paired trades read different values and duplicated items)
- CfxLua forces generational GC on every resource's Lua state and collects inside whatever frame allocated, so a major collect can stall svMain 200+ ms mid bulk save (measured 64-120 ms at an ~80 MB heap, 227 ms at 677 MB). No `collectgarbage` tuning removed it - allocate less on bulk paths: reuse encoded rows that did not change, and share methods through one metatable instead of per-object closures (full collect over 2048 player objects: 2.5 ms with closures vs 0.09 ms with a shared table). (verified: `LuaScriptRuntime.h` sets generational mode at state creation, measured on FXServer 35945/37850)

## The `source` Variable

- `source` is an implicit event variable - the player source (server) or net event sender - meaningful only inside event/callback handlers, and never read from a client payload: the real one comes from the runtime (see Players And Identifiers).
- Capture it before any yield:
  ```lua
  RegisterNetEvent("resource_name:server:action", function()
      local source = source
      -- safe to Wait / await here; `source` is now a stable local
  end)
  ```
- A captured `source` still goes stale if the player dropped: natives on that ID return nil, 0 (truthy in Lua) or an empty table. Server IDs come from a 16-bit counter (1-65534) that wraps back to 1 and skips IDs still in use, so reuse needs ~65k further joins - never within one yield, but a `source` kept in a table not cleared on `playerDropped` can map to another player on a long-running server. In `playerConnecting` it is a temporary ID (65536 and up) replaced when the player joins (`playerJoining` receives it as `oldID`) - never key state by it past the handshake. Re-validate after yielding (`DoesPlayerExist(source)`, or the framework's `GetPlayer(source)`); for valuable mutations compare an identifier captured before the yield (e.g. `license`) with the current one.

## Exports And Stale References

- `exports['resource_name']:method(...)` goes through a runtime proxy, so every call reaches the current code. The gotcha is caching what it returns:
  ```lua
  local ESX = exports['es_extended']:getSharedObject()   -- captured once at load
  ```
  After the provider restarts, `ESX` can still reference the old object/code while the rest of the server uses the new one - re-fetch the shared object instead of trusting a load-time local.
- Never guard with `if exports['name'] then`: the proxy is never nil, and indexing a method on a provider that has not started (or has no such export) throws `No such export <method> in resource <name>`. Check `GetResourceState('name') == 'started'`, wrap in `pcall(function() return exports['name']:method(...) end)`, or call from that resource's `onResourceStart`/`onServerResourceStart`.
- Export and funcref returns are packed as `{ fn(...) }` and unpacked with `table.unpack`, so a `nil` first value leaves a hole and can lose the values behind it: return `false, reason`, never `nil, reason`. An error inside an export reaches the caller as a bare `error()` - a blank `SCRIPT ERROR` with no message - while the real message and traceback print under the *provider* resource, so read its console lines instead of debugging the caller. (verified: `scheduler.lua`)
- Declare dependencies instead of racing with `Wait`: `skills/common/multi-resource.md` -> Dependencies And Load Order.

## Players And Identifiers

- `GetPlayerIdentifiers(source)` returns all identifiers, `GetPlayerIdentifierByType(source, "license")` one. Verified types: `steam` (hex), `discord` (int), `license`/`license2` (ROS hash - `license2` can equal `license` for Steam users), `fivem` (Cfx user id), `ip` (IPv4 string); availability depends on the server/client link. `xbl`/`live` are retired and a `license` can change (`skills/common/security-performance.md` -> Identifier Trust). ([GetPlayerIdentifiers](https://docs.fivem.net/docs/scripting-reference/runtimes/lua/functions/GetPlayerIdentifiers/))
- Stable primary key across sessions: `GetPlayerIdentifierByType(source, "license2") or GetPlayerIdentifierByType(source, "license")`. Pick one scheme and keep it server-side; a DB already keyed by `license` keeps that key instead of switching mid-life.
- Identity is reliable only server-side: take it from `GetPlayerIdentifiers(source)` keyed by the runtime `source`, never from an event payload. Never trust one type alone - `ip` is weak (shared NAT, rotates), so ban/whitelist on the strongest available (`license2`, else `license`).
- Run ban/whitelist and auth checks during `playerConnecting` through the `deferrals` API (`defer`, `update`, `done` called exactly once) for async DB/license lookups, not once the player is in-game. `sv_authMinTrust` is effectively a no-op: FXServer compares it against the *highest* trust among a player's identifiers, and the always-present `ip:` identifier reports trust 5. `sv_authMaxVariance` (1-5, default 5) is the one that matters: compared against the lowest variance, where `license`/`steam` report 1 and `ip` reports 5, so any value below 5 rejects players with no `license`/`steam` identifier. ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/), FXServer `InitConnectMethod.cpp`/`EndPointIdentityProvider.cpp`)
- Server-side player state: `GetPlayerName(source)`, `GetPlayerPed(source)`, `GetPlayerPing(source)`, `DoesPlayerExist(source)` for existence, `GetPlayers()` for connected sources (player state bag API: `skills/common/resource-structure.md`). `GetPlayer(...)` is a framework function (ESX/QBCore/VORP style), not a CFX native - never an existence check in framework-free code.
- `GetPlayerIdentifiers(source)` is not an existence check: it returns a table (truthy even when empty) for invalid IDs. Use `GetPlayerName`/`DoesPlayerExist`, and confirm `source > 0` and connected, especially after a yield.
- Full trust rules: `skills/common/security-performance.md` -> Identifier Trust.

## Convars

- `GetConvar(name, default)` and `GetConvarInt(name, default)` read convars - always pass a default, and read once on load and on a config-reload path, never per frame. ([convars](https://docs.fivem.net/docs/scripting-reference/convars/))
- Exposure by command: `set name value` is server-side only, clients cannot read or set it; `setr name value` is server replicated, readable by clients via `GetConvar` and changeable only server-side, so anything in `setr` is public to clients; `sets name "value"` is server information, published in `info.json` and the server list - never use it for anything sensitive. In resources `SetConvar`, `SetConvarReplicated` and `SetConvarServerInfo` mirror the three; standard convars work only in server scripts.
- Keep secrets (tokens, webhook keys, DB credentials) in server-only `set` convars or env, never in `setr`/`sets` or shared/client files (`skills/common/server-hardening.md` -> Config, Convars, And Secrets).

## Resource Lifecycle

- `ensure name` starts a stopped resource or restarts a running one - safe to repeat in `server.cfg`, handy as a console reload; `start name` only starts a stopped one. Neither watches for crashes or restarts anything automatically: a script error does not stop a resource, and a stopped resource stays stopped until someone starts it again.
- Load order follows declaration order: declare `dependency`/`dependencies` in `fxmanifest.lua`, and check `GetResourceState` for optional ones instead of guessing with `Wait`.
- Stopping a resource also stops every resource that declares it as a dependency, and starting it again does **not** bring them back - they stay stopped with their `onResourceStop` already run, so a framework restart leaves dependents down and `restart oxmysql` leaves `es_extended` and everything under it stopped. `ensure` each dependent afterwards, or restart the server (verified: `ResourceDependencyLoader.cpp`).
- Resource events: `onResourceStart(resource)` (both sides, any resource starting, including this one); `onResourceStarting(resource)` (before start - set up before another resource initializes); `onResourceStop(resourceName)` (both sides, every stopping resource - guard with `if resourceName ~= GetCurrentResourceName() then return end`, using the handler's own parameter name); `onServerResourceStart(resource)`/`onServerResourceStop(resource)` (server-only counterparts of `onClientResourceStart`/`onClientResourceStop`, queued onto a later tick instead of firing immediately like `onResourceStart`, fired for every resource including this one on start - guard with `resource == GetCurrentResourceName()` for your own).
- A provider restart leaves callers' cached export results and pending callbacks stale: re-fetch references and clear pending state. See Exports And Stale References and `skills/common/security-performance.md` -> Callback Safety.
- Degrade cleanly when a dependency is absent: `skills/common/multi-resource.md` -> Failure Handling.

## Yield Hazards

- Never yield (no `Wait`, no `MySQL.*.await`, no async export) inside `entityCreating`: the handler gates creation, so yielding work can stall replication or time out the network request - move heavy work to a thread keyed by the handle.
- Never block in `playerConnecting`: run async checks (DB, license, whitelist) through the `deferrals` API (`defer`, `update`, `done`, `handover`) and call `deferrals.done()` exactly once.
- Do not yield between a validation check and a valuable mutation - check-and-mutate atomically, else recheck after the yield (`skills/common/security-performance.md` -> Atomic State Changes And Replay Protection).
- `MySQL.*.await` suspends only the calling coroutine until the query finishes, not the runtime or other threads, but it needs a coroutine context (a thread, an event handler, or file top level, where it defers the rest of the file) and counts as a yield for every rule above.

## Game Builds

- The running build decides which natives exist and how some behave. Client: compare `GetGameBuildNumber()` against the native's minimum build. Server: `GetGameBuildNumber()` returns 0, so read `GetConvarInt("sv_enforceGameBuild", 0)`, which without an explicit setting returns the artifact's default build (for example 3258 on FiveM or 1491 on RedM), not 0. `sv_enforceGameBuild` is startup-only; DLC names like `mptuner` are stored as their build number. ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/))
- FiveM (GTA V) enforceable builds (fivem-docs `sv_enforceGameBuild` table, checked 2026-09): `1` (base game, no DLCs), `1604, 2060, 2189, 2372, 2545, 2612, 2699, 2802, 2944, 3095, 3258, 3407, 3570, 3751, 3889`, each including all prior content. RedM (RDR3): `1491` is the current enforceable build (September 2022 update); older defaults like `1311`/`1355`/`1436` existed historically. Always re-check both against the live artifact - new builds are added over time.
- Guard optional newer-build natives with a build check and an explicit fallback instead of letting them fail silently on older servers, and record the build number in the `memory/` entry when behavior differs by build.

## Debugging

- "Resource hangs"/"server freezes" is almost always a loop that never yields (no `Wait`), heavy synchronous computation, or a blocking call on the main path. A top-level `MySQL.*.await` does not error: CfxLua runs each script file inside `CreateThreadNow`, so the await yields and the rest of that file (including handlers registered below it) runs only after the query returns, while later files load first. It errors only in non-yieldable contexts such as a `table.sort` comparator or `__gc` ("attempt to yield across a C-call boundary").
- "Works only sometimes" event bugs are usually a stale `source` read after a yield, or a provider that restarted under cached references. Confirm load order and `GetResourceState` for cross-resource calls before assuming an export is broken.
- General flow: `skills/common/debugging.md`.

## Review Questions

- Does every loop yield, and do idle loops sleep long instead of `Wait(0)`?
- Is `source` captured before any yield and re-validated after?
- Are load-time export results re-fetched if their provider can restart?
- Does identity come from `GetPlayerIdentifiers(source)` on the server, never from client data?
- Are convars read once (not per frame) and secrets kept server-only?
- Is heavy/async work kept out of `entityCreating`, and `playerConnecting` deferred properly?
- Are newer-build natives gated with a build check and fallback?
