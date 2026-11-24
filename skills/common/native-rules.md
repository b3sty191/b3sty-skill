# Native Rules

Policy layer for native calls. Mechanics — doc entry to Lua call, name conversion, `Citizen.InvokeNative` marshalling, struct natives, build gating — are in `skills/common/native-usage.md`.

## Usage

- Verify native hashes and parameter order before use.
- Wrap repeated native calls in named functions; keep one-off calls next to the behavior they control unless a wrapper improves clarity.
- Add LuaDoc `---@param` annotations to helpers with important inputs, especially native wrappers.
- Follow `skills/common/native-usage.md` for hash calls, out-pointer params, RDR3 struct arguments, and low-confidence doc entries.

## Native References

- `references/natives/fivem-gta5-natives.md` for GTA V / FiveM, `references/natives/redm-rdr3-natives.md` for RDR3 / RedM.
- Large generated files: `rg` the matching one, never open both (`skills/common/native-usage.md` -> Search Recipes).
- A native in both games still needs its signature and behavior verified in the target game's reference before the code is shared.
- Calibrate trust to the RedM entry's confidence (`documented`/`high`/`medium`/`inferred`/`low`); see `skills/common/native-usage.md` -> RedM Confidence Policy.

## Safety

- Guard entity, ped, vehicle, and object handles, and check entities exist before reading or mutating them.
- Never assume a native behaves the same across RedM and FiveM; use `skills/fivem/rules.md` or `skills/redm/rules.md` for game-specific behavior.
- In server-side `entityCreating`, do not cancel an entity solely because `GetEntityModel(entity)` returns `0` — model data can be unavailable then. Defer model-dependent checks when possible.

## Performance

- Cache `PlayerPedId()`, `GetPlayerPed(player)`, `GetEntityCoords(entity)` and similar results inside loops when reused; never call the same native twice in one expression when a local is clearer and cheaper.
- Prefer squared distance checks before `math.sqrt` or distance helpers in hot paths.
- Load models before creating entities; release them with `SetModelAsNoLongerNeeded` once the resource no longer needs them loaded.
- Avoid per-frame native calls unless the behavior must update every frame.

## Debugging

- Record shared native issues and workarounds in `memory/common/native-bugs.md`, game-specific ones in `memory/fivem/` or `memory/redm/`.
- Include native name, hash, runtime, symptom, and fix.
