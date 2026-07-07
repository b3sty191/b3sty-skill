# FiveM Rules

Use this file for FiveM-only resources or when a shared resource needs GTA V-specific behavior.

## Manifest

- Use `games { 'gta5' }` for FiveM-only resources.
- Do not include `rdr3_warning` in FiveM-only resources.
- Use `games { 'rdr3', 'gta5' }` only when the resource is intentionally shared with RedM.
- Keep the common manifest rules from `skills/common/fxserver.md`.

## Resource Defaults

- Keep shared logic in common client/server files only when the behavior is actually portable.
- Keep GTA V-specific peds, vehicles, weapons, controls, animations, and natives in FiveM-specific files or clearly guarded branches.
- Do not assume RedM entity, weapon, ammo, or mount behavior matches FiveM.
- Stay framework-free by default; when a project already uses a FiveM framework, isolate framework-specific code behind small local adapters.

## Entities And Natives

- Use `references/natives/fivem-gta5-natives.md` when checking GTA V / FiveM native names, hashes, signatures, or parameters.
- Use `skills/common/native-usage.md` to turn a doc entry into the Lua call: name conversion, `Citizen.InvokeNative` marshalling, out-pointer params, and game-build gates.
- Verify GTA V native hashes, parameter order, and return values before sharing a native wrapper with RedM.
- Treat GTA V vehicles, peds, props, weapons, and network ownership as FiveM-specific until confirmed portable.
- Do not rely on `SetBlipAsShortRange` for `AddBlipForArea` area blips; handle distance visibility manually when needed.
- Cache repeated native calls in loops following `skills/common/native-rules.md`.
- Clean up spawned entities on resource stop and player drop following `skills/common/security-performance.md`.

## Blips

- `AddBlipForArea` area blips can stay visible at long distance even when `SetBlipAsShortRange(blip, true)` is set.
- For short-range area behavior, create/remove the area blip based on player distance or use another blip/marker shape that supports short-range visibility.
- See `memory/fivem/native-bugs.md` before building minimap behavior around area blips.

## Appearance

- When applying freemode appearance, avoid untested bulk sequences that call `SetPedHeadBlendData` and immediately apply mask component variations.
- Gate known risky masks, test component combinations on the target game build, and provide rollback/fallback behavior for appearance apply flows.
- Check `memory/fivem/native-bugs.md` when debugging freemode mask/head blend crashes.

## Events And State

- Keep event names resource-prefixed with `:server:` or `:client:` side markers.
- The server owns money, inventory, jobs, permissions, ownership, rewards, cooldowns, and saved state.
- State bags are acceptable for visual state, but server-side validation remains required.

## Compatibility Checks

Before moving FiveM code into a shared file, check:

- native availability and parameter behavior;
- entity type behavior;
- animation/control names;
- weapon/ammo semantics;
- framework assumptions;
- UI/NUI assumptions.
