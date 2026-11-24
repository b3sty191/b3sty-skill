# FiveM Rules

For FiveM-only resources, or when a shared resource needs GTA V-specific behavior.

## Manifest

- `games { 'gta5' }` for FiveM-only resources; `games { 'rdr3', 'gta5' }` only when the resource is intentionally shared with RedM.
- No `rdr3_warning` in FiveM-only resources.
- Keep the common manifest rules from `skills/common/fxserver.md`.

## Resource Defaults

- Share logic in common client/server files only when the behavior is actually portable.
- Keep GTA V-specific peds, vehicles, weapons, controls, animations, and natives in FiveM files or clearly guarded branches.
- Do not assume RedM entity, weapon, ammo, or mount behavior matches FiveM.
- Framework-free by default; if the project already runs a FiveM framework, isolate its code behind small local adapters.

## Entities And Natives

- Check GTA V / FiveM native names, hashes, signatures, and parameters in `references/natives/fivem-gta5-natives.md`; turn an entry into the Lua call with `skills/common/native-usage.md` (name conversion, `Citizen.InvokeNative` marshalling, out-pointer params, build gates).
- Verify GTA V hashes, parameter order, and return values before sharing a native wrapper with RedM.
- Treat GTA V vehicles, peds, props, weapons, and network ownership as FiveM-specific until confirmed portable.
- Do not rely on `SetBlipAsShortRange` for `AddBlipForArea` area blips; handle distance visibility manually when needed.
- Cache repeated native calls in loops (`skills/common/native-rules.md`); clean up spawned entities on resource stop and player drop (`skills/common/security-performance.md`).

## Blips

- `AddBlipForArea` area blips can stay visible at long distance even with `SetBlipAsShortRange(blip, true)` set; for short-range behavior, create/remove the blip by player distance or use another blip/marker shape that supports short-range visibility.
- See `memory/fivem/native-bugs.md` before building minimap behavior around area blips.

## Appearance

- Applying freemode appearance: avoid untested bulk sequences that call `SetPedHeadBlendData` and immediately apply mask component variations.
- Gate known risky masks, test component combinations on the target game build, and give apply flows rollback/fallback behavior.
- Check `memory/fivem/native-bugs.md` when debugging freemode mask/head blend crashes.

## Events And State

- Keep event names resource-prefixed with `:server:` or `:client:` side markers.
- The server owns money, inventory, jobs, permissions, ownership, rewards, cooldowns, and saved state.
- State bags are acceptable for visual state, but server-side validation remains required.

## Compatibility Checks

Before moving FiveM code into a shared file, check native availability and parameter behavior, entity type behavior, animation/control names, weapon/ammo semantics, framework assumptions, and UI/NUI assumptions.
