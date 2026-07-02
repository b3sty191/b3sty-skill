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
- Cache repeated native calls in loops following `skills/common/native-rules.md`.
- Clean up spawned entities on resource stop and player drop following `skills/common/security-performance.md`.

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
