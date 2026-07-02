# RedM Rules

Use this file for RedM-only resources or when a shared resource needs RDR3-specific behavior.

## Manifest

- Use `games { 'rdr3' }` for RedM-only resources.
- Include the required `rdr3_warning` entry when RedM is supported.
- Use `games { 'rdr3', 'gta5' }` only when the resource is intentionally shared with FiveM.
- Keep the common manifest rules from `skills/common/fxserver.md`.

## Resource Defaults

- Keep shared logic in common client/server files only when the behavior is actually portable.
- Keep RDR3-specific peds, horses, wagons, weapons, controls, animations, and natives in RedM-specific files or clearly guarded branches.
- Do not assume FiveM entity, weapon, ammo, vehicle, or control behavior matches RedM.
- Stay framework-free by default; when a project already uses a RedM framework, isolate framework-specific code behind small local adapters.

## Entities And Natives

- Use `references/natives/redm-rdr3-natives.md` when checking RDR3 / RedM native names, hashes, signatures, or parameters.
- Verify RDR3 native hashes, parameter order, and return values before sharing a native wrapper with FiveM.
- Treat horses, mounts, wagons, ped components, weapons, ammo, and scenario behavior as RedM-specific until confirmed portable.
- Do not rely on server-side `GetEntityHealth` for RedM health checks; it can return `0` for live entities. See `memory/redm/native-bugs.md`.
- Do not rely on server-side `GetVehiclePedIsIn(ped, false) ~= 0` alone to prove a RedM player is currently seated; guard it with `IsPedInAnyVehicle`.
- Cache repeated native calls in loops following `skills/common/native-rules.md`.
- Clean up spawned entities on resource stop and player drop following `skills/common/security-performance.md`.

## Entity Health

- In RedM, avoid using `GetEntityHealth(entity)` on the server as the source of truth.
- Client-side health reads are acceptable for UI or visual behavior, but client-reported health is untrusted for rewards, damage, permissions, or anti-abuse checks.
- For server-side decisions, keep server-owned eligibility/health-like state where possible, or validate through server-controlled action state instead of trusting a direct health native read.
- If a resource must accept client-reported health, clamp and type-check it, rate-limit updates, compare it against expected server-side state, and never use it as the only condition for valuable outcomes.

## Vehicle State

- In RedM server code, treat `GetVehiclePedIsIn(ped, false)` as unreliable unless `IsPedInAnyVehicle(ped, false)` is true first.
- Use a small wrapper that returns `0` when the ped is not currently in a vehicle.
- Do not grant rewards, vehicle access, or ownership changes from a non-zero vehicle handle unless the current seated state is verified.

## Ammo

- Ammo by type is an RDR3 concept; FiveM/GTA V uses different ammo natives, so do not share this code without a RedM guard.
- Do not rely on direct RedM ammo set/remove natives alone when setting or reducing reserve ammo by type.
- Use a wrapper that clears ammo with `RemoveAllPedAmmo(ped)`, reads the current ammo map from the resource's local player state/helper, reapplies that map, then applies the requested ammo type and amount.
- Keep the public helper signature clean, such as `SetAmmoByType(ammoType, amount)`.
- This avoids RedM ammo state bugs where reserve ammo may not decrease correctly or may restore after using direct ammo natives.
- See `memory/redm/native-bugs.md` for the full entry and a reference wrapper.

## Weapon Cosmetics

- For RedM weapon components, verify the final held weapon entity when visual output matters; ped-level component checks can succeed while the held weapon does not render the cosmetic.
- Keep deny/fallback lists for known non-rendering longarm cosmetics instead of offering every shared component as supported.
- Test shared longarm components on the actual weapon models used by the resource before moving the code into a shared cosmetic system.

## Events And State

- Keep event names resource-prefixed with `:server:` or `:client:` side markers.
- The server owns money, inventory, jobs, permissions, ownership, rewards, cooldowns, and saved state.
- State bags are acceptable for visual state, but server-side validation remains required.

## Compatibility Checks

Before moving RedM code into a shared file, check:

- native availability and parameter behavior;
- entity type behavior;
- horse/mount/wagon assumptions;
- animation/control names;
- weapon/ammo semantics;
- framework assumptions;
- UI/NUI assumptions.
