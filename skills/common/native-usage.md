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
- `SET_PED_AMMO_BY_TYPE` → `SetPedAmmoByType(ped, ammoType, ammo)`.
- `_ACTIVATE_COVER_LAYER` → `ActivateCoverLayer(coverLayer)` (the leading `_` collapses the same as any other).
- Hash-only heading (no friendly name, e.g. `0x1234ABCD...`) → `N_0x1234abcd...` (step 2 turns `0x` into `n_0x` before capitalization; the identifier must start with a letter). This global exists, but calling by explicit hash with a `--[[NAME]]` comment reads better in review.

Edge case — **an underscore followed by a digit does not collapse**, because the pattern only matches a following letter (`%a`), not a digit. A native with a trailing `_2`-style segment keeps the underscore in the Lua name (for example a hypothetical `..._INDEX_2` becomes `...Index_2`, not `...Index2`). Check the actual global in an F8/server console with `type(FunctionName)` when a name has a digit segment and the direct call is `nil`.

- If the expected global is still `nil` at runtime after accounting for the digit edge case, the running artifact's codegen predates the name (renamed/newer native); fall back to `Citizen.InvokeNative` with the doc hash. That works on the client when the running game build has the native. It does not work on the server: FXServer registers no game hashes (its server-side natives, including the OneSync entity subset, use CFX hashes), so a hash from these references hits no handler and silently returns `false`/nothing.
- A native can have multiple registered names (`aliases` in the codegen); each alias name goes through this same conversion and becomes its own valid global for the same underlying call. The generated reference files here do not enumerate aliases — if a project uses a different name than the doc heading for what looks like the same native, verify the hash matches before assuming it is unrelated.
- When calling by hash, keep the doc name beside it so the call stays greppable against the reference:
  ```lua
  -- RDR3 hash (GTA V: 0xEEF059FAD016D209)
  local health = Citizen.InvokeNative(0x82368787EA73C0F7 --[[GET_ENTITY_HEALTH]], entity, Citizen.ResultAsInteger())
  ```

## Type Mapping

| Doc type | Lua value |
| --- | --- |
| `Ped`, `Vehicle`, `Entity`, `Object`, `Player`, `Cam`, `Blip`, `Pickup`, `FireId`, `Interior`, `ScrHandle` | integer handle |
| `Hash` | integer hash — see Hashes |
| `int` | integer number |
| `float` | float number — see InvokeNative Pitfalls |
| `BOOL` | non-zero integer (usually `1`) or `false` from named natives and from a bare `Citizen.InvokeNative` (0 becomes `false`); `1`/`0` only when `Citizen.ResultAsInteger()` is appended |
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

- Named natives are plain global functions. `BOOL` params take `true`/`false`. `BOOL` returns come back as `1`/`false`, not real booleans: use them directly in `if`/`not` and never compare `== true`.
- Output pointer params (`int*`, `float*`, `Vector3*`) usually do not appear in the Lua argument list (exception: when a native's only pointer is its last param, the generated function keeps a positional slot for it - an optional initial value for `int*`/`float*`, see the caveat under Calling By Hash). They come back as extra return values after the primary return, in declaration order:
  ```lua
  -- BOOL GET_GROUND_Z_FOR_3D_COORD(float x, float y, float z, float* groundZ, BOOL includeWater)
  local found, groundZ = GetGroundZFor_3dCoord(x + 0.0, y + 0.0, z + 0.0, false)
  ```
- When a native is void with output pointers, the outputs are the only return values.
- Some upstream signatures still show an initial value being passed for an out param; when the runtime asks for it, pass a sane default (usually `0` or `0.0`).

## Calling By Hash With Citizen.InvokeNative

`Citizen.InvokeNative(hash, args...)` invokes any native by its identity hash. Marshal results explicitly:

- With no `ResultAs*` marker, a zero result becomes `false` and a non-zero result an integer (see pitfalls). Append `Citizen.ResultAsInteger()` to any int result that can legitimately be 0.
- `float` result: append `Citizen.ResultAsFloat()`.
- `char*` result: append `Citizen.ResultAsString()`.
- `Vector3` result: append `Citizen.ResultAsVector()`.
- 64-bit results (rare): `Citizen.ResultAsLong()`.
- When you pass any `Citizen.PointerValue*` marker and also want the native's own return value, append `Citizen.ReturnResultAnyway()` or the matching `Citizen.ResultAs*`. Without it, only the pointer outputs are returned.

```lua
-- int GET_ENTITY_HEALTH(Entity entity) — RDR3 0x82368787EA73C0F7
local health = Citizen.InvokeNative(0x82368787EA73C0F7 --[[GET_ENTITY_HEALTH]], entity, Citizen.ResultAsInteger())
```

Output pointers by hash use placeholder markers. The outputs come back in order after the primary return value only if you also pass `Citizen.ReturnResultAnyway()` or a `Citizen.ResultAs*`. Otherwise the outputs are the only return values:

- `Citizen.PointerValueInt()`, `Citizen.PointerValueFloat()`, `Citizen.PointerValueVector()` for plain out params.
- `Citizen.PointerValueIntInitialized(v)` / `Citizen.PointerValueFloatInitialized(v)` when the native reads the value before writing it.
- Caveat: in current CfxLua, `Citizen.PointerValueFloatInitialized(v)` ignores `v` and starts the pointer at 0.0 (upstream bug in `Lua_GetPointerField`). This also affects named natives whose only pointer is a trailing `float*` (codegen passes it through `PointerValueFloatInitialized`). For in/out float params, verify in game, or pass a writable buffer (`string.blob(string.pack('<f', v))` or DataView, never a plain short string - see Struct Natives) and `string.unpack` the value back.

```lua
-- void native(Entity transport, int* flags) — flags returns as the call result
local flags = Citizen.InvokeNative(hash, transport, Citizen.PointerValueInt())

-- BOOL GET_GROUND_Z_FOR_3D_COORD(float x, float y, float z, float* groundZ, BOOL includeWater)
-- GTA V hash (RDR3: 0x24FA4267BB8D2431). Without ReturnResultAnyway, `found` would hold the ground Z and `groundZ` would be nil.
local found, groundZ = Citizen.InvokeNative(0xC906A7DAB05C8D2B --[[GET_GROUND_Z_FOR_3D_COORD]], x + 0.0, y + 0.0, z + 0.0, Citizen.PointerValueFloat(), false, Citizen.ReturnResultAnyway())
```

## InvokeNative Pitfalls

- **BOOL results are `1`/`false`, never `true`, and `0` is truthy in Lua.** A bare InvokeNative or named BOOL is `1`/`false` and is safe in `if`. With `Citizen.ResultAsInteger()` it is `1`/`0`, and `0` is truthy, so compare `~= 0` (or `== 1`). Never compare any BOOL `== true`.
- **Float params must be float-subtype numbers, in named and hash calls alike.** The invoker marshals by the Lua value, not the native signature: `1` marshals as an integer and corrupts a float argument, so `SetEntityHeading(ped, 90)` is as broken as the hash call. Write literals as `1.0` and coerce computed values with `+ 0.0` (check with `math.type(v) == "float"` when unsure).
- **Pass the documented default explicitly** (`0`, `0.0`, `false`) instead of `nil` for "optional" params. `nil` silently marshals as a raw 0 (reads as 0/0.0/false/NULL), which hides intent and can mask a missing or misspelled variable.
- **String returns can be `nil`;** guard before concatenation or `joaat`.
- **Argument count must match the signature exactly.** Extra or missing args silently corrupt the call; recount against the doc entry when a hash call misbehaves.
- Prefer the named global when it exists: it self-documents and handles out-params and Hash-name strings for you. It does not coerce floats, so float params still need float-subtype values (`90.0`, `v + 0.0`). BOOL returns are still `1`/`false`.

## Struct Natives (RDR3 `Any*`)

Many RDR3 natives pack arguments or results into one struct pointer instead of discrete params. The RedM reference marks these as `Any*` and its Notes often give the field layout (`f_0`, `f_1`, `f_2`, ...).

- **CfxLua passes a Lua string argument as a pointer to its bytes**, so an `Any*` struct can be built in pure Lua with `string.pack` (or `string.blob` plus a writer). For output structs, use a `string.blob` buffer or one longer than 40 bytes, so the native never writes into an interned short string. Then read the fields back with `string.unpack`.
- **`dataview.lua` (gottfriedleibniz) is the common pure-Lua helper for this.** It defines a global `DataView` (`DataView.ArrayBuffer(size)`, `:SetInt32`, `:GetInt32`, `:Buffer()`). Copy it into the resource as a `client_script`/`shared_script` listed before the code that uses it, or reference it with `'@otherresource/dataview.lua'`. Do not assume the global exists. Before using it:
  - Confirm the target project already ships `dataview.lua` (or an equivalent helper), or get explicit sign-off to add it.
  - List the file in `fxmanifest.lua` before its users. Declare a `dependency` only when the project really ships DataView as its own resource (see `skills/common/multi-resource.md`).
  - Verify the exact API surface (method names, buffer sizing, endianness) against whatever `DataView` build the project actually uses; names above are illustrative, not a spec.
- Script struct fields are commonly 8-byte slots: `f_0` at offset 0, `f_1` at offset 8, `f_2` at offset 16, and so on — but confirm this against the doc Notes for the specific native, not by assumption.
- Illustrative shape once `dataview.lua` (or an equivalent) is confirmed loaded, plus the same struct with stock `string.pack`:
  ```lua
  -- _ADD_COVER_BLOCKING_AREA (0x733077295AB51304): f_0 volume handle, f_1 = 1, f_2 = flags
  local struct = DataView.ArrayBuffer(8 * 3)
  struct:SetInt32(0, volumeHandle)  -- f_0
  struct:SetInt32(8, 1)             -- f_1
  struct:SetInt32(16, -1)           -- f_2
  Citizen.InvokeNative(0x733077295AB51304 --[[_ADD_COVER_BLOCKING_AREA]], struct:Buffer())

  -- Stock Lua: one int32 plus 4 padding bytes per 8-byte slot
  local packed = string.pack('<i4xxxxi4xxxxi4xxxx', volumeHandle, 1, -1)
  Citizen.InvokeNative(0x733077295AB51304 --[[_ADD_COVER_BLOCKING_AREA]], packed)
  ```
- For output structs, size the buffer generously, call the native, then read fields back at the matching offsets (`string.unpack`, or DataView `GetInt32`/`GetFloat32`/`GetInt64`).
- An undersized buffer or wrong layout can crash the client. Verify the layout from the doc Notes, test in game, and record the confirmed layout and the buffer helper actually used (`string.pack` or `dataview.lua`) in `memory/redm/native-bugs.md`.
- Prefer a non-struct alternative native when one exists — struct natives should be a last resort given the extra helper and crash risk. Wrap unavoidable struct natives in one controller method so the buffer layout and helper assumption live in exactly one place.

## Client, Server, And Shared Context

- Most game natives in these references are client-only. The server runs CFX runtime natives plus a limited OneSync subset of game natives (entity getters/setters, player state).
- CFX natives (`RegisterCommand`, `GetResourceState`, state bag APIs, `GetGameBuildNumber`, ...) are not in the generated files; verify them against the CFX namespace at `docs.fivem.net/natives` instead.
- When a RedM entry names an `apiset`, respect it — a client-apiset native does nothing useful on the server.
- `IsDuplicityVersion()` returns `true` on the server; use it in shared scripts that must branch by side.
- Server-side game natives can behave differently from their client versions. Known cases live in `memory/`: RedM server `GetEntityHealth` returning `0`, server `GetVehiclePedIsIn` returning the last vehicle, `GetEntityModel` returning `0` during `entityCreating`. Check the matching `memory/*/native-bugs.md` before building server logic on a native read.

## Game Builds

- RedM entries carry a minimum `build` (for example `build 1207`); FiveM natives may require a newer GTA V build than the server enforces.
- The running build must satisfy the native's minimum. On the client, compare `GetGameBuildNumber()` against the native's minimum build. On the server, `GetGameBuildNumber()` returns 0, so read the enforced build with `GetConvarInt('sv_enforceGameBuild', 0)` instead. Treat 0 as the server default or unknown build and verify behavior.
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
4. Calls marshal correctly: floats are float-subtype (named and hash calls), BOOL results are never compared `== true` (compare `~= 0` under `Citizen.ResultAsInteger()`), int results that can be 0 use `Citizen.ResultAsInteger()`, pointer-marker calls add `Citizen.ReturnResultAnyway()` when the return value is needed, results use the right `Citizen.ResultAs*`, struct buffers match the documented layout.
5. The effect was observed in game (or the closest available repro) with no console errors.
6. Newly confirmed quirks, refuted doc entries, or build-specific behavior were recorded in the right `memory/` namespace with date and game build.
