# Native Usage — Calling Natives From Lua

Mechanics: read a doc entry, turn it into a correct CfxLua call, debug a call that compiles but misbehaves. Policy (safety, caching, performance, when to wrap): `skills/common/native-rules.md`. References: `references/natives/fivem-gta5-natives.md` (GTA V / FiveM), `references/natives/redm-rdr3-natives.md` (RDR3 / RedM).

## Contents

Lookup Workflow · Search Recipes · Reading A Doc Entry · RedM Confidence Policy · Name Conversion · Type Mapping · Hashes · Vectors · Named Native Calls And Out Params · Calling By Hash · InvokeNative Pitfalls · Struct Natives · Client, Server, And Shared Context · Game Builds · Wrappers And LuaDoc · Verification Loop

## Lookup Workflow

1. Pick the reference for the target game; never assume a native exists or behaves the same in the other game.
2. `rg` the entry (recipes below) rather than opening the file, and read it whole: hash, return type, params, behavior, notes, and (RedM) build + confidence.
3. Check `memory/common/native-bugs.md` and the matching `memory/fivem/` or `memory/redm/` file for known quirks before trusting documented behavior.
4. Write the call with the rules below, verify in game (Verification Loop), and record new quirks in `memory/` with date and game build.

## Search Recipes

Headings are `` ### `NATIVE_NAME` ``; use `.` in the pattern to avoid shell-escaping backticks. Search only the matching game file; raise `-A` for long Behavior/Notes blocks.

- Name: `rg -n -A 20 '^### .SET_PED_AMMO_BY_TYPE.' references/natives/redm-rdr3-natives.md`
- Hash only: `rg -n -B 3 -A 20 '0x5FD1E1F011E76D7E' references/natives/redm-rdr3-natives.md`
- Fuzzy, then open the winner: `rg -n '^### ' references/natives/redm-rdr3-natives.md | rg -i 'ammo'`
- Namespace: `rg -n '^## WEAPON$' references/natives/redm-rdr3-natives.md`

## Reading A Doc Entry

- FiveM (verbatim upstream): heading, meta line with `0x<long hash>` (identity hash, the one for `Citizen.InvokeNative`), optionally `0x<short hash>` (legacy/alternate — never invoke with it) and return type, then a C signature, description and params. `cs_type(...)` markers are upstream codegen type overrides: trust the effective outer type, test in game when marshalling looks ambiguous.
- RedM (generated analysis): heading, meta line of hash · return type · minimum `build` · `confidence` · closest GTA V equivalent, then Summary, **Parameters**, **Returns**, **Behavior**, **Notes**. Notes may name the `apiset` (client/server) and struct field layouts (`f_0`, `f_1`, ...) — respect both. The GTA V equivalent is porting orientation only; verify the RDR3 signature independently before sharing code.
- The namespace heading a native sits under is organization only; it never appears in the Lua function name.

## RedM Confidence Policy

- `documented` — trust it; still check `memory/redm/native-bugs.md` for runtime quirks.
- `high` — trust for normal use; sanity-check the effect on first run.
- `medium` / `inferred` — a hypothesis: test in game before shipping, never put server authority or valuable outcomes on it.
- `low` — verify everything in game first; prefer a `documented`/`high` alternative.
- Record what testing confirms or refutes in `memory/redm/native-bugs.md` with date and game build.

## Name Conversion (Docs To Lua)

Not a style convention — the literal codegen the CitizenFX Lua runtime uses to register every native global in both games (`ext/natives/codegen_out_lua.lua`, `printFunctionName`):

```lua
native.name:lower():gsub('0x', 'n_0x'):gsub('_(%a)', string.upper):gsub('(%a)(.+)', function(a, b)
    return a:upper() .. b
end)
```

Four passes: lowercase; literal `0x` → `n_0x` (only hash-only names); every `_` immediately followed by a **letter** collapses into that letter uppercased, anywhere including a leading `_`; uppercase the first letter. So `GET_ENTITY_HEALTH` → `GetEntityHealth(entity)`, `SET_PED_AMMO_BY_TYPE` → `SetPedAmmoByType(ped, ammoType, ammo)`, `_ACTIVATE_COVER_LAYER` → `ActivateCoverLayer(coverLayer)`.

- Hash-only heading (no friendly name, e.g. `0x1234ABCD...`) → global `N_0x1234abcd...`; pass 2 makes the identifier start with a letter. It exists, but an explicit hash call with a `--[[NAME]]` comment reads better in review.
- Edge case: `_` before a **digit** does not collapse (`%a` is letters only), so a trailing `_2`-style segment keeps it (`..._INDEX_2` → `...Index_2`, not `...Index2`). When a digit segment leaves the direct call `nil`, check the real global with `type(FunctionName)` in an F8/server console.
- Still `nil`? The artifact's codegen predates the name (renamed/newer native): use `Citizen.InvokeNative` with the doc hash. Client only, and only if the running build has the native — never the server, which registers no game hashes (FXServer's server-side natives, including the OneSync entity subset, use CFX hashes), so a reference hash hits no handler and silently returns `false`/nothing.
- A native can have several registered names (`aliases` in the codegen), each converting into its own valid global for the same call. These references do not list aliases: when a project uses a different name for what looks like the same native, verify the hash before assuming it is unrelated.
- Keep the doc name beside a hash call so it stays greppable against the reference:
  ```lua
  -- int GET_ENTITY_HEALTH(Entity entity) — RDR3 hash (GTA V: 0xEEF059FAD016D209)
  local health = Citizen.InvokeNative(0x82368787EA73C0F7 --[[GET_ENTITY_HEALTH]], entity, Citizen.ResultAsInteger())
  ```

## Type Mapping

| Doc type | Lua value |
| --- | --- |
| `Ped`, `Vehicle`, `Entity`, `Object`, `Player`, `Cam`, `Blip`, `Pickup`, `FireId`, `Interior`, `ScrHandle` | integer handle |
| `Hash` | integer hash — see Hashes |
| `int` | integer number |
| `float` | float number — see InvokeNative Pitfalls |
| `BOOL` | non-zero integer (usually `1`) or `false`, from named natives and bare `Citizen.InvokeNative` alike; `1`/`0` only with `Citizen.ResultAsInteger()` |
| `char*` (param) | Lua string |
| `char*` (return) | Lua string or `nil` — guard before use |
| `float x, float y, float z` | three separate numbers |
| `Vector3` | `vector3(x, y, z)` |
| `int*`, `float*`, `Vector3*` (output) | extra return value (named) or `Citizen.PointerValue*` (by hash) |
| `Any*` (struct) | packed buffer — see Struct Natives |

## Hashes

- `joaat("weapon_revolver_cattleman")` hashes at runtime (CfxLua built-in); backtick literals compile at load time and are preferred for constants: `` `WEAPON_REVOLVER_CATTLEMAN` ``. Both are CfxLua extensions — RedM/FiveM only, never standalone Lua tooling (as with compound operators in `skills/common/style.md`).
- `GetHashKey(name)` works too but is a native call; prefer `joaat`/backtick literals in hot paths.
- Lua may print hashes as negative numbers (signed 32-bit): compare hashes to hashes (`GetEntityModel(ped) == joaat("player_zero")`), never to hex strings or typed decimals.

## Vectors

- `vector3(x, y, z)`; `vector2`, `vector4`, `quat` also exist. A `Vector3` param takes one vector3, a `float x, float y, float z` signature three numbers — read the signature, do not guess.
- Coordinate returns like `GetEntityCoords` are real `vector3`s; use `.x/.y/.z` directly.
- `#(a - b)` is the distance; per `skills/common/native-rules.md`, prefer cheap early-outs before exact distance work in hot paths.

## Named Native Calls And Out Params

- Named natives are plain globals; `BOOL` params take `true`/`false`, and `BOOL` returns are `1`/`false`, never real booleans: use them directly in `if`/`not` (see pitfalls).
- Out pointers (`int*`, `float*`, `Vector3*`) are usually absent from the Lua arg list — exception: a native whose only pointer is its last param keeps a positional slot for it (an optional initial value for `int*`/`float*`; see the Calling By Hash caveat). They return as extra values after the primary return, in declaration order:
  ```lua
  -- BOOL GET_GROUND_Z_FOR_3D_COORD(float x, float y, float z, float* groundZ, BOOL includeWater)
  local found, groundZ = GetGroundZFor_3dCoord(x + 0.0, y + 0.0, z + 0.0, false)
  ```
- Void native with out pointers: the outputs are the only return values.
- When an upstream signature shows an initial value for an out param and the runtime asks for it, pass a sane default (`0` or `0.0`).

## Calling By Hash With Citizen.InvokeNative

`Citizen.InvokeNative(hash, args...)` invokes any native by identity hash (example under Name Conversion). Marshal results explicitly:

- No `ResultAs*` marker: a zero result becomes `false`, non-zero an integer. Append `Citizen.ResultAsInteger()` to any int result that can legitimately be 0.
- `Citizen.ResultAsFloat()` for `float`, `Citizen.ResultAsString()` for `char*`, `Citizen.ResultAsVector()` for `Vector3`, `Citizen.ResultAsLong()` for 64-bit results (rare).
- Any `Citizen.PointerValue*` marker makes the pointer outputs the only return values; add `Citizen.ReturnResultAnyway()` or the matching `Citizen.ResultAs*` to also get the native's own return, which then comes first with the outputs in order after it.
- Markers: `Citizen.PointerValueInt()`, `Citizen.PointerValueFloat()`, `Citizen.PointerValueVector()`; `Citizen.PointerValueIntInitialized(v)` / `Citizen.PointerValueFloatInitialized(v)` when the native reads the value before writing it.
- Caveat: current CfxLua `Citizen.PointerValueFloatInitialized(v)` ignores `v` and starts the pointer at 0.0 (upstream bug in `Lua_GetPointerField`); it also hits named natives whose only pointer is a trailing `float*` (codegen routes it through `PointerValueFloatInitialized`). For in/out floats, verify in game or pass a writable buffer (`string.blob(string.pack('<f', v))` or DataView, never a plain short string — see Struct Natives) and `string.unpack` the value back.

```lua
-- void native(Entity transport, int* flags) — flags returns as the call result
local flags = Citizen.InvokeNative(hash, transport, Citizen.PointerValueInt())

-- BOOL GET_GROUND_Z_FOR_3D_COORD(float x, float y, float z, float* groundZ, BOOL includeWater)
-- GTA V hash (RDR3: 0x24FA4267BB8D2431); without ReturnResultAnyway, found would hold the ground Z and groundZ nil
local found, groundZ = Citizen.InvokeNative(0xC906A7DAB05C8D2B --[[GET_GROUND_Z_FOR_3D_COORD]], x + 0.0, y + 0.0, z + 0.0, Citizen.PointerValueFloat(), false, Citizen.ReturnResultAnyway())
```

## InvokeNative Pitfalls

- **BOOL results are `1`/`false`, never `true`, and `0` is truthy in Lua.** A bare InvokeNative or named BOOL is `1`/`false` and safe in `if`; under `Citizen.ResultAsInteger()` it is `1`/`0`, so compare `~= 0` (or `== 1`). Never compare any BOOL `== true`.
- **Float params must be float-subtype numbers, named and hash calls alike.** The invoker marshals by Lua value, not signature: `1` marshals as an integer and corrupts a float argument, so `SetEntityHeading(ped, 90)` is as broken as the hash call. Write `1.0`, coerce with `+ 0.0` (check `math.type(v) == "float"`).
- **Pass the documented default explicitly** (`0`, `0.0`, `false`), never `nil`, for "optional" params: `nil` silently marshals as a raw 0 (reads as 0/0.0/false/NULL), hiding intent and masking a missing or misspelled variable.
- **String returns can be `nil`;** guard before concatenation or `joaat`.
- **Argument count must match the signature exactly.** Extra or missing args silently corrupt the call; recount against the doc entry when a hash call misbehaves.
- **An unregistered native, and every argument past a native's known parameter count, mangles 64-bit integers.** The invoker overwrites the upper 32 bits of each non-zero, non-pointer integer argument with a fixed DEADBEEF marker, so only the low 32 bits survive. Pass large values as strings or split them into two 32-bit args (verified: `ScriptInvoker.cpp`, FXServer 35945).
- Prefer the named global when it exists: it self-documents and handles out-params and Hash-name strings. It still does not coerce floats (`90.0`, `v + 0.0` required) and its BOOL returns are still `1`/`false`.

## Struct Natives (RDR3 `Any*`)

Many RDR3 natives pack args or results into one struct pointer instead of discrete params; the RedM reference marks these `Any*` and its Notes often give the field layout (`f_0`, `f_1`, `f_2`, ...).

- **CfxLua passes a Lua string argument as a pointer to its bytes**, so an `Any*` struct can be built in pure Lua with `string.pack` (or `string.blob` plus a writer). Output structs need a `string.blob` buffer or one longer than 40 bytes, so the native never writes into an interned short string; read fields back with `string.unpack`.
- Fields are commonly 8-byte slots (`f_0` at offset 0, `f_1` at 8, `f_2` at 16, ...) — confirm against the doc Notes for that native, never by assumption.
- **`dataview.lua` (gottfriedleibniz) is the common pure-Lua helper**, defining a global `DataView` (`DataView.ArrayBuffer(size)`, `:SetInt32`, `:GetInt32`, `:Buffer()`). Copy it in as a `client_script`/`shared_script` listed before its users, or reference `'@otherresource/dataview.lua'`; never assume the global exists. First confirm the project already ships it or an equivalent (otherwise get explicit sign-off to add it), list it in `fxmanifest.lua` before its users — a `dependency` only if DataView really ships as its own resource (`skills/common/multi-resource.md`) — and verify the exact API surface (method names, buffer sizing, endianness) against the build in use; names here are illustrative, not a spec.
- Example (DataView, then the same struct with stock `string.pack`):
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
- Output structs: size the buffer generously, call the native, read fields at the matching offsets (`string.unpack`, or DataView `GetInt32`/`GetFloat32`/`GetInt64`).
- An undersized buffer or wrong layout can crash the client: verify the layout from the doc Notes, test in game, and record the confirmed layout and helper used (`string.pack` or `dataview.lua`) in `memory/redm/native-bugs.md`.
- Prefer a non-struct alternative when one exists — struct natives are a last resort given the extra helper and crash risk. Wrap unavoidable ones in one controller method so layout and helper assumption live in exactly one place.

## Client, Server, And Shared Context

- Most game natives here are client-only; the server runs CFX runtime natives plus a limited OneSync subset of game natives (entity getters/setters, player state).
- CFX natives (`RegisterCommand`, `GetResourceState`, state bag APIs, `GetGameBuildNumber`, ...) are not in the generated files; verify them against the CFX namespace at `docs.fivem.net/natives`.
- When a RedM entry names an `apiset`, respect it — a client-apiset native does nothing useful on the server.
- `IsDuplicityVersion()` returns `true` on the server; use it in shared scripts that branch by side.
- Server-side game natives can differ from their client versions; known cases in `memory/`: RedM server `GetEntityHealth` returning `0`, server `GetVehiclePedIsIn` returning the last vehicle, `GetEntityModel` returning `0` during `entityCreating`. Check the matching `memory/*/native-bugs.md` before building server logic on a native read.

## Game Builds

- RedM entries carry a minimum `build` (e.g. `build 1207`); FiveM natives may need a newer GTA V build than the server enforces. The running build must satisfy the minimum.
- Client: compare `GetGameBuildNumber()` against it. Server: `GetGameBuildNumber()` returns 0, so read the enforced build with `GetConvarInt('sv_enforceGameBuild', 0)`, treating 0 as the server default or unknown build, then verify behavior.
- Guard optional newer-build natives with a build check and an explicit fallback instead of letting them fail silently on older servers.
- When behavior differs by build, record the build number in the `memory/` entry — the templates already require the `Game build:` field.

## Wrappers And LuaDoc

- Keep one-off native calls inline beside the behavior they control (b3sty style).
- Wrap a native in a controller method when it is called by hash, needs a workaround, or is reused across call sites — the quirk then lives in exactly one place:
  ```lua
  ---@param ped number
  ---@return number vehicle Current vehicle handle, or 0 when not seated.
  function Controller:GetCurrentVehicle(ped)
      if not IsPedInAnyVehicle(ped, false) then
          return 0
      end

      return GetVehiclePedIsIn(ped, false)
  end
  ```
- Add LuaDoc `---@param`/`---@return` to wrappers whose parameter meaning is not obvious, matching `skills/common/native-rules.md`, and reference the `memory/` entry above a wrapper that encodes a workaround so the reason survives review.
- Caching, loop hygiene, and per-frame budgets stay in `skills/common/native-rules.md` — do not duplicate them here.

## Verification Loop

Before finishing native-heavy work: name/hash/param order/return type match the doc entry for the **target game**; the call runs on the right side and the running build meets the native's minimum; `memory/common/native-bugs.md` and the game-specific `memory/` file were checked; marshalling follows the pitfalls above (float subtype, no BOOL `== true`, `Citizen.ResultAsInteger()` on ints that can be 0, `Citizen.ReturnResultAnyway()` with pointer markers, right `Citizen.ResultAs*`, struct buffer matching the layout); the effect was observed in game (or the closest repro) with no console errors; new quirks, refuted entries, or build-specific behavior were recorded in the right `memory/` namespace with date and game build.
