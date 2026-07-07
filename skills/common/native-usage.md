# Native Usage — Calling Natives From Lua

Use this file when writing or reviewing CfxLua code that calls game natives, when translating an entry from the generated native references into a working Lua call, or when a native call compiles but misbehaves.

The generated references that document every native are:

- `references/natives/fivem-gta5-natives.md` — GTA V / FiveM.
- `references/natives/redm-rdr3-natives.md` — RDR3 / RedM.

`skills/common/native-rules.md` holds the policy layer (safety, caching, performance, when to wrap). This file holds the mechanics: how to read a doc entry and turn it into a correct Lua call.

## Contents

- Lookup Workflow
- Search Recipes
- Reading A Doc Entry
- RedM Confidence Policy
- Name Conversion (Docs To Lua)
- Type Mapping
- Hashes
- Vectors
- Named Native Calls And Out Params
- Calling By Hash With Citizen.InvokeNative
- InvokeNative Pitfalls
- Struct Natives (RDR3 `Any*`)
- Client, Server, And Shared Context
- Game Builds
- Wrappers And LuaDoc
- Verification Loop

## Lookup Workflow

1. Pick the reference file for the target game. Never assume a native exists or behaves the same in the other game.
2. Search the file with `rg` (recipes below); do not open the whole file.
3. Read the full entry: hash, return type, parameters, behavior, notes, and (RedM) build + confidence.
4. Check `memory/common/native-bugs.md` and the matching `memory/fivem/` or `memory/redm/` file for known quirks before trusting the documented behavior.
5. Write the call using the conversion rules below.
6. Verify in game following the Verification Loop, and record new quirks in `memory/` with date and game build.

## Search Recipes

Headings in both files have the shape `` ### `NATIVE_NAME` ``. Use `.` in the pattern to avoid shell-escaping backticks.

- Exact native by name:
  ```
  rg -n -A 20 '^### .SET_PED_AMMO_BY_TYPE.' references/natives/redm-rdr3-natives.md
  ```
- Native by hash (works even when only the hash is known):
  ```
  rg -n -B 3 -A 20 '0x5FD1E1F011E76D7E' references/natives/redm-rdr3-natives.md
  ```
- Fuzzy discovery by keyword (list candidates first, then open the winner):
  ```
  rg -n '^### ' references/natives/redm-rdr3-natives.md | rg -i 'ammo'
  ```
- Jump to a namespace section:
  ```
  rg -n '^## WEAPON$' references/natives/redm-rdr3-natives.md
  ```

Increase `-A` when an entry has long Behavior/Notes blocks. Search the one matching game file only.

## Reading A Doc Entry

FiveM entry shape (verbatim from the upstream repo):

- Heading: `` ### `NATIVE_NAME` ``.
- Meta line: `0x<long hash>` (the native's identity hash — the one used with `Citizen.InvokeNative`), optionally `0x<short hash>` (a legacy/alternate hash — do not invoke with it), and the return type.
- A C signature block, then verbatim description and parameter list.
- `cs_type(...)` markers in signatures are upstream codegen type overrides; trust the effective outer type and test in game when the marshalling looks ambiguous.

RedM entry shape (generated analysis):

- Heading, then a meta line: hash · return type · minimum `build` · `confidence` · closest GTA V equivalent.
- Summary, **Parameters**, **Returns**, **Behavior**, and **Notes** sections.
- Notes may name the `apiset` (client/server) and struct field layouts (`f_0`, `f_1`, ...). Respect both.
- The GTA V equivalent is for porting orientation only; verify the RDR3 signature independently before sharing code.

The namespace heading a native sits under is organization only. It never appears in the Lua function name.

## RedM Confidence Policy

RedM entries carry a confidence level. Calibrate trust to it:

- `documented` — trust the entry; still check `memory/redm/native-bugs.md` for runtime quirks.
- `high` — trust for normal use; sanity-check the effect the first time it runs.
- `medium` / `inferred` — treat as a hypothesis. Test in game before shipping, and do not build server authority or valuable outcomes on the inferred behavior.
- `low` — verify everything in game first. Prefer a `documented`/`high` alternative when one exists.
- When testing confirms or refutes an entry, record the result in `memory/redm/native-bugs.md` with date and game build so the next task starts from a fact.

## Name Conversion (Docs To Lua)

This is not a style convention — it is the literal codegen the CitizenFX Lua runtime uses to register every native global, shared by FiveM and RedM (`ext/natives/codegen_out_lua.lua`, function `printFunctionName`):

```lua
native.name:lower():gsub('0x', 'n_0x'):gsub('_(%a)', string.upper):gsub('(%a)(.+)', function(a, b)
    return a:upper() .. b
end)
```

Read as four passes over the doc name, applied identically to every native in both games:

1. Lowercase the whole name.
2. Replace a literal `0x` substring with `n_0x` (only matters for hash-only names with no friendly name).
3. Collapse every `_` immediately followed by a **letter** into that letter, uppercased, dropping the underscore — regardless of position, including a leading underscore.
4. Uppercase the first letter of the result.

Worked examples:

- `GET_ENTITY_HEALTH` → `GetEntityHealth(entity)`.
- `ACTIVATE_TIMECYCLE_EDITOR` → `ActivateTimecycleEditor`.
- `_ACTIVATE_COVER_LAYER` → `ActivateCoverLayer(coverLayer)` (the leading `_` collapses the same as any other).
- Hash-only heading (no friendly name, e.g. `0x1234ABCD...`) → `N_0x1234abcd...` (step 2 turns `0x` into `n_0x` before capitalization; the identifier must start with a letter). This global exists, but calling by explicit hash with a `--[[NAME]]` comment reads better in review.

Edge case — **an underscore followed by a digit does not collapse**, because the pattern only matches a following letter (`%a`), not a digit. A native with a trailing `_2`-style segment keeps the underscore in the Lua name (for example a hypothetical `..._INDEX_2` becomes `...Index_2`, not `...Index2`). Check the actual global in an F8/server console with `type(FunctionName)` when a name has a digit segment and the direct call is `nil`.

- If the expected global is still `nil` at runtime after accounting for the digit edge case, the running artifact's codegen predates the name (renamed/newer native); fall back to `Citizen.InvokeNative` with the doc hash, which always works.
- A native can have multiple registered names (`aliases` in the codegen); each alias name goes through this same conversion and becomes its own valid global for the same underlying call. The generated reference files here do not enumerate aliases — if a project uses a different name than the doc heading for what looks like the same native, verify the hash matches before assuming it is unrelated.
- When calling by hash, keep the doc name beside it so the call stays greppable against the reference:
  ```lua
  local health = Citizen.InvokeNative(0x82368787EA73C0F7 --[[GET_ENTITY_HEALTH]], entity)
  ```

## Type Mapping

| Doc type | Lua value |
| --- | --- |
| `Ped`, `Vehicle`, `Entity`, `Object`, `Player`, `Cam`, `Blip`, `Pickup`, `FireId`, `Interior`, `ScrHandle` | integer handle |
| `Hash` | integer hash — see Hashes |
| `int` | integer number |
| `float` | float number — see InvokeNative Pitfalls |
| `BOOL` | `true`/`false` on named natives; `1`/`0` from `Citizen.InvokeNative` |
| `char*` (param) | Lua string |
| `char*` (return) | Lua string or `nil` — guard before use |
| `float x, float y, float z` | three separate numbers |
| `Vector3` | `vector3(x, y, z)` |
| `int*`, `float*`, `Vector3*` (output) | extra return value (named) or `Citizen.PointerValue*` (by hash) |
| `Any*` (struct) | packed buffer — see Struct Natives |

## Hashes

- `joaat("weapon_revolver_cattleman")` computes a Jenkins hash at runtime; CfxLua provides `joaat` as a built-in.
- Backtick hash literals compile the hash at load time and are preferred for constants: `` `WEAPON_REVOLVER_CATTLEMAN` ``.
- Both are CfxLua extensions — RedM/FiveM code only, never standalone Lua tooling (same rule as compound operators in `skills/common/style.md`).
- `GetHashKey(name)` works too but is a native call; prefer `joaat`/backtick literals in hot paths.
- Lua may print hashes as negative numbers (signed 32-bit). Compare hashes to hashes (`GetEntityModel(ped) == joaat("player_zero")`), never to hex strings or manually typed decimal values.

## Vectors

- Construct with `vector3(x, y, z)`; `vector2`, `vector4`, and `quat` also exist.
- Natives declared with `Vector3` params take one vector3; natives declared `float x, float y, float z` take three numbers — read the signature, do not guess.
- Coordinate-returning natives like `GetEntityCoords` return a real `vector3`; use `.x/.y/.z` fields directly.
- `#(a - b)` returns the distance between two vectors; per `skills/common/native-rules.md`, prefer cheap early-out checks before exact distance work in hot paths.

## Named Native Calls And Out Params

- Named natives are plain global functions; `BOOL` params take `true`/`false` and `BOOL` returns are real booleans.
- Output pointer params (`int*`, `float*`, `Vector3*`) do not appear in the Lua argument list. They come back as extra return values after the primary return, in declaration order:
  ```lua
  -- BOOL GET_GROUND_Z_FOR_3D_COORD(float x, float y, float z, float* groundZ, BOOL includeWater)
  local found, groundZ = GetGroundZFor_3dCoord(x, y, z, false)
  ```
- When a native is void with output pointers, the outputs are the only return values.
- Some upstream signatures still show an initial value being passed for an out param; when the runtime asks for it, pass a sane default (usually `0` or `0.0`).

## Calling By Hash With Citizen.InvokeNative

`Citizen.InvokeNative(hash, args...)` invokes any native by its identity hash. Marshal results explicitly:

- `int`/`BOOL` results return by default; `BOOL` arrives as `1`/`0` (see pitfalls).
- `float` result: append `Citizen.ResultAsFloat()`.
- `char*` result: append `Citizen.ResultAsString()`.
- `Vector3` result: append `Citizen.ResultAsVector()`.
- 64-bit results (rare): `Citizen.ResultAsLong()`.
- If a result comes back `nil` on an older artifact, append `Citizen.ReturnResultAnyway()`.

```lua
-- int GET_ENTITY_HEALTH(Entity entity) — RDR3 0x82368787EA73C0F7
local health = Citizen.InvokeNative(0x82368787EA73C0F7 --[[GET_ENTITY_HEALTH]], entity, Citizen.ResultAsInteger())
```

Output pointers by hash use placeholder markers; outputs return after the primary return value, in order:

- `Citizen.PointerValueInt()`, `Citizen.PointerValueFloat()`, `Citizen.PointerValueVector()` for plain out params.
- `Citizen.PointerValueIntInitialized(v)` / `Citizen.PointerValueFloatInitialized(v)` when the native reads the value before writing it.

```lua
-- void native(Entity transport, int* flags) — flags returns as the call result
local flags = Citizen.InvokeNative(hash, transport, Citizen.PointerValueInt())
```

## InvokeNative Pitfalls

- **`0` is truthy in Lua.** Never put a raw `Citizen.InvokeNative` BOOL result in an `if`; compare `== 1` explicitly. Named natives return real booleans and are safe.
- **Float params must be float-subtype numbers.** The invoker marshals by the Lua value, not the native signature: `1` marshals as an integer and corrupts a float argument. Write literals as `1.0` and coerce computed values with `+ 0.0` (check with `math.type(v) == "float"` when unsure).
- **Never pass `nil` for an "optional" param.** Pass `0`, `false`, or the documented default instead; `nil` does not marshal as a safe empty value.
- **String returns can be `nil`;** guard before concatenation or `joaat`.
- **Argument count must match the signature exactly.** Extra or missing args silently corrupt the call; recount against the doc entry when a hash call misbehaves.
- Prefer the named global when it exists — it self-documents, marshals BOOL/out-params for you, and removes the pitfalls above.

## Struct Natives (RDR3 `Any*`)

Many RDR3 natives pack arguments or results into one struct pointer instead of discrete params. The RedM reference marks these as `Any*` and its Notes often give the field layout (`f_0`, `f_1`, `f_2`, ...).

- **Plain CfxLua cannot build an arbitrary struct pointer.** `Citizen.InvokeNative` only marshals numbers, strings, vectors, and the scalar `PointerValue*` out-params (see Calling By Hash above); it has no built-in mechanism to allocate/pass a pointer to a multi-field custom struct (confirmed unsupported in pure Lua per `citizenfx/fivem#2484`). A struct-argument `Any*` native is uncallable from stock Lua without an external buffer-building dependency.
- **`DataView` is a real but third-party pattern**, not a CfxLua built-in. RedM community code uses a `DataView`-style resource (`DataView.ArrayBuffer(size)`, `:SetInt32(offset, value)`, `:GetInt32(offset)`, `:Buffer()`) to allocate a raw buffer and hand its pointer to `Citizen.InvokeNative` as the `Any*` argument. Before using this pattern:
  - Confirm the target project already depends on a `DataView`-equivalent resource, or get explicit sign-off to add one — do not assume the global exists.
  - Declare it as a `dependency` in `fxmanifest.lua` like any other external resource (see `skills/common/multi-resource.md`).
  - Verify the exact API surface (method names, buffer sizing, endianness) against whatever `DataView` build the project actually uses; names above are illustrative, not a spec.
- Script struct fields are commonly 8-byte slots: `f_0` at offset 0, `f_1` at offset 8, `f_2` at offset 16, and so on — but confirm this against the doc Notes for the specific native, not by assumption.
- Illustrative shape once a `DataView`-equivalent dependency is confirmed available:
  ```lua
  -- _ADD_COVER_BLOCKING_AREA (0x733077295AB51304): f_0 volume handle, f_1 = 1, f_2 = flags
  local struct = DataView.ArrayBuffer(8 * 3)
  struct:SetInt32(0, volumeHandle)  -- f_0
  struct:SetInt32(8, 1)             -- f_1
  struct:SetInt32(16, -1)           -- f_2
  Citizen.InvokeNative(0x733077295AB51304 --[[_ADD_COVER_BLOCKING_AREA]], struct:Buffer())
  ```
- For output structs, size the buffer generously, call the native, then read fields back at the matching offsets (`GetInt32`, `GetFloat32`, `GetInt64`).
- An undersized buffer or wrong layout can crash the client. Verify the layout from the doc Notes, test in game, and record the confirmed layout and the `DataView` dependency actually used in `memory/redm/native-bugs.md`.
- Prefer a non-struct alternative native when one exists — struct natives should be a last resort given the extra dependency and crash risk. Wrap unavoidable struct natives in one controller method so the buffer layout and dependency assumption live in exactly one place.

## Client, Server, And Shared Context

- Most game natives in these references are client-only. The server runs CFX runtime natives plus a limited OneSync subset of game natives (entity getters/setters, player state).
- CFX natives (`RegisterCommand`, `GetResourceState`, state bag APIs, `GetGameBuildNumber`, ...) are not in the generated files; verify them against the CFX namespace at `docs.fivem.net/natives` instead.
- When a RedM entry names an `apiset`, respect it — a client-apiset native does nothing useful on the server.
- `IsDuplicityVersion()` returns `true` on the server; use it in shared scripts that must branch by side.
- Server-side game natives can behave differently from their client versions. Known cases live in `memory/`: RedM server `GetEntityHealth` returning `0`, server `GetVehiclePedIsIn` returning the last vehicle, `GetEntityModel` returning `0` during `entityCreating`. Check the matching `memory/*/native-bugs.md` before building server logic on a native read.

## Game Builds

- RedM entries carry a minimum `build` (for example `build 1207`); FiveM natives may require a newer GTA V build than the server enforces.
- The running build must satisfy the native's minimum: compare `GetGameBuildNumber()` (and the server's `sv_enforceGameBuild`) before relying on newer natives.
- Guard optional newer-build natives with a build check and an explicit fallback instead of letting them fail silently on older servers.
- When behavior differs by build, record the build number in the `memory/` entry — the templates already require the `Game build:` field.

## Wrappers And LuaDoc

- Keep one-off native calls inline beside the behavior they control (b3sty style).
- Wrap a native in a controller method when it is called by hash, needs a workaround, or is reused across call sites — the quirk then lives in exactly one place:
  ```lua
  local Controller = {}

  ---@param ped number
  ---@return number vehicle Current vehicle handle, or 0 when not seated.
  function Controller:GetCurrentVehicle(ped)
      if not IsPedInAnyVehicle(ped, false) then
          return 0
      end

      return GetVehiclePedIsIn(ped, false)
  end
  ```
- Add LuaDoc `---@param`/`---@return` to wrappers whose parameter meaning is not obvious, matching `skills/common/native-rules.md`.
- Reference the `memory/` entry above wrappers that encode a workaround so the reason survives review.
- Caching, loop hygiene, and per-frame budgets stay under `skills/common/native-rules.md` — do not duplicate them here.

## Verification Loop

Before finishing native-heavy work, confirm:

1. Name, hash, parameter order, and return type match the doc entry for the **target game**.
2. The call runs on the right side (client/server) and the running build satisfies the native's minimum build.
3. `memory/common/native-bugs.md` and the game-specific `memory/` file were checked for known quirks.
4. Hash-invoked calls marshal correctly: floats are float-subtype, BOOL results compared `== 1`, results use the right `Citizen.ResultAs*`, struct buffers match the documented layout.
5. The effect was observed in game (or the closest available repro) with no console errors.
6. Newly confirmed quirks, refuted doc entries, or build-specific behavior were recorded in the right `memory/` namespace with date and game build.
