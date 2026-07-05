# b3sty Style

## Core Principles

- Prefer direct, readable code over heavy abstraction.
- Hardcoded values are preferred when they make the logic easier to read in place.
- Treat performance and optimization as important requirements, not optional cleanup.
- Keep related logic and data close together when jumping between files would make the flow harder to understand.
- Add abstraction only when it removes real duplication or clearly improves maintenance.
- Match the local project style before introducing a new pattern.
- Prefer "easy to read in one place" over clean architecture when the two conflict.

## Code Shape

- Use explicit names and straightforward control flow.
- Keep functions focused, but do not split tiny helpers just for the sake of splitting.
- Do not create helper functions for one-off code unless the inline version is genuinely hard to read or unsafe.
- Do not create local variables just to avoid hardcoded literals; inline one-off model names, event names, config keys, vector values, and limits when they read clearly beside the logic.
- Create a local only when the value is reused, expensive to compute, validated before use, mutated, or the inline expression would hide intent.
- Prefer a clear single-file flow for small resources.
- Split files when the data or logic becomes large enough that separation improves scanning.
- Add comments only for non-obvious behavior or temporary workarounds.
- Do not create framework-like abstractions, dispatchers, or class systems for small resources.
- Do not make code generic before there is real repeated use.
- Security and performance matter, but the final code should still be easy to read in b3sty style.

## Formatting

- Use 4 spaces for indentation.
- Add spaces after commas in function parameters, function calls, and table values.
- Prefer readable spacing around operators and comparisons.
- In config/data tables, keep trailing commas when it makes adding new rows easier.
- Follow the existing quote style in a project; do not churn quotes without a reason.
- Keep display/data keys as `["Name"] = value` in editable config/data.

## Lua Style

- Use table modules or local controller objects for resource logic.
- Prefer method syntax for controller behavior:
  ```lua
  local Controller = {}

  function Controller:Initialize()
      -- ...
  end
  ```
- Config and data files should usually return a table:
  ```lua
  return {
      ["Category Limit"] = {
          ["Head"] = 10,
      },
  }
  ```
- Use `require(...)` for config/data modules when the runtime supports it.
- Prefer bracket key declarations like `["Name"] = value` for config/data tables.
- Bracket keys are especially preferred when the data is meant to be edited by humans or may contain spaces.
- Runtime access may use bracket or dot style based on the existing code and hot-path readability.
- Use bracket access for keys with spaces or dynamic names.
- In hot paths, cache config/data lookup results in locals instead of repeating deep table access.
- For static runtime fields, dot access is acceptable when it is already the project style and reads clearly.
- Inline values such as model names, bones, positions, rotations, categories, limits, and event names are fine when they are clearer beside the logic that uses them.
- Add LuaDoc `---@param` annotations for reusable helper functions, exports, callbacks, and native wrappers when parameter meaning is not obvious.

## CfxLua Syntax

- In RedM/FiveM CfxLua code, b3sty uses the supported compound assignment operators when they make code shorter and clearer.
- Supported CfxLua compound assignment operators:
  - `+=`
  - `-=`
  - `*=`
  - `/=`
  - `<<=`
  - `>>=`
  - `&=`
  - `|=`
  - `^=`
- Do not use `++` or `--`; CfxLua does not implement increment/decrement operators.
- Do not assume these operators work in standard Lua, standalone Lua tools, or non-Cfx runtimes.
- Prefer compound assignment for simple updates such as counters, bit flags, and accumulated values:
  ```lua
  count += 1
  flags |= visibleFlag
  mask &= allowedFlag
  ```
- Avoid compound assignment when the expression becomes harder to read than the expanded form.

## Config Splitting

- Use `config.lua` for small/shared config that is broadly needed by the resource.
- When config/data grows large or has separate concerns, split it into `configs/*.lua` as the standard pattern.
- Each split config file should return a table with `return { ... }`.
- Do not turn `config.lua` into an eager aggregator that requires every split config file.
- Require split config files directly in the script that actually uses them.
- Store required config modules in local variables near the top of the script.
- Split large position lists, object lists, category lists, shop locations, zone data, and similar datasets into separate config files.
- Do not over-split small configs; keep simple values in one readable file.

## Performance

- Prefer RAM/cache/indexes over repeated CPU work only when it keeps hot paths or expensive repeated work cheaper.
- CPU single-core time is limited in FXServer workloads, but bad caches can waste memory and increase GC pressure.
- Avoid loading config/data modules that the current script does not use.
- Cache repeated lookups in locals when they are used often in a loop.
- Avoid unnecessary loops, repeated native calls, and repeated table scans.
- Prefer simple direct code, but do not trade away performance for convenience.

## Documentation

- Write skill and memory documentation in English.
- Add comments only for non-obvious behavior or temporary workarounds.
