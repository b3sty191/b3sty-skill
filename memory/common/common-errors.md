# Common Errors

Track common errors and fixes here.

## Lua `not` Precedence In Comparisons

- Error: `if not attach[tostring(i)] == true then`
- Context: checking whether a state value is not enabled.
- Cause: Lua applies `not` before `==`, so the expression can be read or evaluated differently than intended.
- Fix:
  ```lua
  local attachIndex = tostring(index)

  if attach[attachIndex] ~= true then
      -- ...
  end
  ```
- Prevention: use `~= true`, `== false`, or assign the value to a clearly named local before comparing.
- Date: 2026-07-02
- Game build: n/a (pure Lua / build-independent)

## Missing Entity Guards

- Error: calling natives on an entity handle that no longer exists.
- Context: player objects, attached props, peds, vehicles, or cleanup loops.
- Cause: entities can be deleted by the game, stream out, detach, or be removed by another resource.
- Fix: check `DoesEntityExist(entity)` before reading, attaching, detaching, or deleting.
- Prevention: keep cleanup and reattach code defensive.
- Date: 2026-07-02
- Game build: n/a (build-independent entity lifetime behavior)

## Local Function Called Before Its Declaration

- Error: `attempt to call a nil value (global 'helper')` at runtime, even though a `local function helper` is defined in the same file.
- Context: one local function calls another that is declared lower in the file; common after splitting a file into helpers or reordering code.
- Cause: a `local function f` is only in scope *after* its line. A reference above that line does not see the local, so it resolves to the global `f`, which is `nil` in a resource's sandboxed environment - the error surfaces only when that path runs, not at load.
- Fix: declare the callee before the caller; for genuine cycles, forward-declare the name first.
  ```lua
  -- BROKEN: `helper` above its local declaration resolves to a nil global.
  local function handler()
      return helper()
  end
  local function helper()
      return true
  end

  -- FIXED: callee declared before caller.
  local function helper2()
      return true
  end
  local function handler2()
      return helper2()
  end

  -- CYCLE: forward-declare the name, then assign.
  local ping, pong
  function ping(n) if n > 0 then return pong(n - 1) end return "ping" end
  function pong(n) if n > 0 then return ping(n - 1) end return "pong" end
  ```
- Prevention: order functions callee-before-caller within a file; reach for a forward `local name` only for real mutual recursion.
- Date: 2026-11-20
- Game build: n/a (pure Lua / build-independent)

## Template

Copy this block when adding a new entry, then fill it in. Leave it blank intentionally - it is a skeleton for future entries, not a real error.

- Error:
- Context:
- Cause:
- Fix:
- Prevention:
- Date:
- Game build:
