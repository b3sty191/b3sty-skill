# Common Errors

Track common errors and fixes here.

## Lua `not` Precedence In Comparisons

- Error: `if not attach[tostring(i)] == true then`
- Context: checking whether a state value is not enabled.
- Cause: Lua applies `not` before `==`, so the expression can be read or evaluated differently than intended.
- Fix:
  ```lua
  if attach[tostring(i)] ~= true then
      -- ...
  end
  ```
- Prevention: use `~= true`, `== false`, or assign the value to a clearly named local before comparing.

## Missing Entity Guards

- Error: calling natives on an entity handle that no longer exists.
- Context: player objects, attached props, peds, vehicles, or cleanup loops.
- Cause: entities can be deleted by the game, stream out, detach, or be removed by another resource.
- Fix: check `DoesEntityExist(entity)` before reading, attaching, detaching, or deleting.
- Prevention: keep cleanup and reattach code defensive.

## Template

Copy this block when adding a new entry, then fill it in. Leave it blank intentionally - it is a skeleton for future entries, not a real error.

- Error:
- Context:
- Cause:
- Fix:
- Prevention:
- Date:
- Game build:
