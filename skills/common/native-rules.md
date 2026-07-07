# Native Rules

This file is the policy layer for native calls. For the mechanics — translating a doc entry into a Lua call, name conversion, `Citizen.InvokeNative` marshalling, struct natives, build gating — open `skills/common/native-usage.md`.

## Usage

- Verify native hashes and parameter order before use.
- Prefer named wrapper functions for repeated native calls.
- Keep native calls close to the behavior they control unless a wrapper improves clarity.
- Add LuaDoc `---@param` annotations to helper functions with important inputs, especially native wrappers.
- Follow `skills/common/native-usage.md` when calling a native by hash, handling out-pointer params, packing RDR3 struct arguments, or working from a low-confidence doc entry.

## Native References

- Use `references/natives/fivem-gta5-natives.md` for GTA V / FiveM native lookup.
- Use `references/natives/redm-rdr3-natives.md` for RDR3 / RedM native lookup.
- These files are large generated references; search the matching file with `rg` instead of opening both. Search recipes are in `skills/common/native-usage.md` -> Search Recipes.
- If a native appears in both games, verify the signature and behavior in the target game's reference before sharing code.
- Calibrate trust to the RedM entry's confidence level (`documented`/`high`/`medium`/`inferred`/`low`); see `skills/common/native-usage.md` -> RedM Confidence Policy.

## Safety

- Guard entity, ped, vehicle, and object handles before native calls.
- Check that entities exist before reading or mutating them.
- Avoid assuming a native behaves the same across RedM and FiveM.
- Use `skills/fivem/rules.md` or `skills/redm/rules.md` when native behavior is game-specific.
- In server-side `entityCreating`, do not cancel an entity solely because `GetEntityModel(entity)` returns `0`; model data can be unavailable at that point. Defer model-dependent checks when possible.

## Performance

- Cache `PlayerPedId()`, `GetPlayerPed(player)`, `GetEntityCoords(entity)`, and similar native results inside loops when reused.
- Do not call the same native multiple times in one expression when a local variable would be clearer and cheaper.
- Prefer squared distance checks before using `math.sqrt` or distance helpers in hot paths.
- Load models before creating entities; release models with `SetModelAsNoLongerNeeded` when the resource no longer needs to keep them loaded.
- Avoid per-frame native calls unless the behavior must update every frame.

## Debugging

- Record shared native issues and workarounds in `memory/common/native-bugs.md`.
- Record game-specific native issues in `memory/fivem/` or `memory/redm/`.
- Include native name, hash, runtime, symptom, and fix when documenting a bug.
