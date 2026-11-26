# Common Errors

Track common errors and fixes here.

## Lua `not` Precedence In Comparisons

- Error: `if not attach[tostring(i)] == true then`
- Context: checking whether a state value is not enabled.
- Cause: Lua applies `not` before `==`, so the expression evaluates differently than intended.
- Fix:
  ```lua
  if attach[tostring(index)] ~= true then end
  ```
- Prevention: use `~= true` or `== false`, or assign the value to a named local before comparing.
- Date: 2026-07-02
- Game build: n/a (pure Lua / build-independent)

## Missing Entity Guards

- Error: calling natives on an entity handle that no longer exists.
- Context: player objects, attached props, peds, vehicles, cleanup loops.
- Cause: entities can be deleted by the game, stream out, detach, or be removed by another resource.
- Fix: check `DoesEntityExist(entity)` before reading, attaching, detaching, or deleting.
- Prevention: keep cleanup and reattach code defensive.
- Date: 2026-07-02
- Game build: n/a (build-independent entity lifetime behavior)

## Local Function Called Before Its Declaration

- Error: `attempt to call a nil value (global 'helper')` at runtime, though `local function helper` exists in the same file.
- Context: one local function calls another declared lower in the file; common after splitting a file or reordering code.
- Cause: a `local function f` is in scope only *after* its line; a call above it resolves to the global `f`, `nil` in the resource sandbox - it fails only when that path runs, not at load.
- Fix: declare the callee before the caller; for genuine cycles, forward-declare the name.
  ```lua
  -- BROKEN: `helper` above its local declaration resolves to a nil global.
  local function handler() return helper() end
  local function helper() return true end

  -- FIXED: callee first.
  local function helper2() return true end
  local function handler2() return helper2() end

  -- CYCLE: forward-declare, then assign.
  local ping, pong
  function ping(n) if n > 0 then return pong(n - 1) end return "ping" end
  function pong(n) if n > 0 then return ping(n - 1) end return "pong" end
  ```
- Prevention: order functions callee-before-caller; use a forward `local name` only for real mutual recursion.
- Date: 2026-11-20
- Game build: n/a (pure Lua / build-independent)

## Per-Frame Animation Tied To FPS

- Error: marker/fade animation and hold timers run faster or slower with the player's FPS.
- Context: `Wait(0)` draw loops adding a fixed step per frame (`remaining -= 10`, `size += diff * 0.02`, `GetGameTimer() * 0.3` for colour).
- Cause: a frame is not a fixed amount of time; `GetGameTimer()` is milliseconds, so ms-based sine inputs flicker.
- Fix: scale by `GetFrameTime()` (seconds): `remaining -= GetFrameTime() * 1000.0`, lerp with `1 - (1 - speed) ^ (GetFrameTime() * 60.0)`, sine inputs from `GetGameTimer() / 1000.0`.
- Prevention: every per-frame step or timer uses frame time; a loop that can `break` also resets its "running" flag.
- Date: 2026-09-28
- Game build: FiveM 3095 (crest_voicearea)

## Framework Net Event Never Reaches A Plain AddEventHandler

- Error: a HUD / status resource never reacts to `esx:playerLoaded` on join; it works only after restarting that resource mid-session.
- Context: `AddEventHandler("esx:playerLoaded", ...)` in another resource's client script; es_extended sends it from the server (`TriggerClientEvent`).
- Cause: net-event safety is per resource runtime - a network-triggered event reaches only resources that called `RegisterNetEvent` for that name themselves; the framework registering it does not cover others. The restart path worked only because it polled `IsPlayerLoaded()`.
- Fix: `RegisterNetEvent("esx:playerLoaded", function(...) ... end)` in every listening client resource (it still gets local `TriggerEvent` re-fires).
- Prevention: register any server-sent framework event (`esx:playerLoaded`, `esx:onPlayerLogout`, `esx:setJob`, ...) with `RegisterNetEvent` in the listener; keep the restart-time `IsPlayerLoaded()` check too.
- Date: 2026-09-29
- Game build: FiveM 3095 (crest_hud, crest_status)

## `<=` Breaks On A Metatable That Defines Only `__lt`

- Error: `attempt to compare two table values` from `a <= b` on objects that compared fine on an older artifact.
- Context: server-side CfxLua comparing objects (version wrappers, sortable records) whose metatable has `__lt` but no `__le`.
- Cause: from artifact 37850 the server Lua drops the Lua 5.3 compatibility option (only math-library compat remains), so `a <= b` is no longer emulated as `not (b < a)`.
- Fix: define `__le` next to `__lt`.
  ```lua
  local mt = {}
  mt.__lt = function(a, b) return a.v < b.v end
  mt.__le = function(a, b) return not (b.v < a.v) end
  ```
- Prevention: every metatable with `__lt` also gets `__le`; math compat still exists, only the comparison metamethods changed.
- Date: 2026-10-28
- Game build: n/a (server artifact 37850 and later)

## Native Component Crashes The txAdmin Host At Boot

- Error: the server never comes up; `run.sh` dies with SIGSEGV (exit 139) before the first log line, and rolling back the artifact does not help as long as the component stays in `components.json`. `gdb` shows thread `luv_svMain`, faulting address in the component's `.so`.
- Context: a native add-on component that creates convars or globals in `fx::ServerInstanceBase::OnServerCreate` and reads them from a resource hook (`fx::Resource::OnStart` / `OnBeforeStart`).
- Cause: the txAdmin host process loads the same components and starts its `monitor` resource but never fires `OnServerCreate`, so the convar's `shared_ptr` is still null when the hook runs.
- Fix: guard every resource-level hook on the state `OnServerCreate` sets (`if (!g_var || !g_var->GetValue()) return;`).
- Prevention: `skills/common/fxserver-components.md` -> Hooks And Process Lifecycle. To find the culprit, map the faulting address to a library with gdb `info proc mappings`, then `addr2line -e <lib>.dbg <pc - load base>`.
- Date: 2026-11-26
- Game build: n/a (server artifact 38781)

## Template

Copy this block when adding a new entry, then fill it in. Leave it blank intentionally - it is a skeleton for future entries, not a real error.

- Error:
- Context:
- Cause:
- Fix:
- Prevention:
- Date:
- Game build:
