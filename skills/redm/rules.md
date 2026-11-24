# RedM Rules

For RedM-only resources, or when a shared resource needs RDR3-specific behavior.

## Manifest

- `games { 'rdr3' }` for RedM-only resources; `games { 'rdr3', 'gta5' }` only when the resource is intentionally shared with FiveM.
- Include the required `rdr3_warning` entry whenever RedM is supported.
- Keep the common manifest rules from `skills/common/fxserver.md`.

## Resource Defaults

- Share logic in common client/server files only when the behavior is actually portable.
- Keep RDR3-specific peds, horses, wagons, weapons, controls, animations, and natives in RedM files or clearly guarded branches.
- Do not assume FiveM entity, weapon, ammo, vehicle, or control behavior matches RedM.
- Framework-free by default; if the project already runs a RedM framework, isolate its code behind small local adapters.

## Entities And Natives

- Check RDR3 / RedM native names, hashes, signatures, and parameters in `references/natives/redm-rdr3-natives.md`; turn an entry into the Lua call with `skills/common/native-usage.md` — hash-only natives via `Citizen.InvokeNative`, `Any*` struct packing, confidence policy, and build gates all apply heavily to RDR3.
- Verify RDR3 hashes, parameter order, and return values before sharing a native wrapper with FiveM.
- Treat horses, mounts, wagons, ped components, weapons, ammo, and scenario behavior as RedM-specific until confirmed portable.
- Server-side `GetEntityHealth` and `GetVehiclePedIsIn` are unreliable in RedM — see Entity Health and Vehicle State below, plus `memory/redm/native-bugs.md`.
- Cache repeated native calls in loops (`skills/common/native-rules.md`); clean up spawned entities on resource stop and player drop (`skills/common/security-performance.md`).

## Entity Health

- Never treat server-side `GetEntityHealth(entity)` as the source of truth in RedM; it can return `0` for live entities.
- Client-side health reads are fine for UI or visuals, but client-reported health is untrusted for rewards, damage, permissions, or anti-abuse checks.
- For server-side decisions keep server-owned eligibility/health-like state, or validate through server-controlled action state instead of a direct health native read.
- If a resource must accept client-reported health: clamp and type-check it, rate-limit updates, compare it against expected server-side state, and never make it the only condition for a valuable outcome.

## Vehicle State

- In RedM server code, treat `GetVehiclePedIsIn(ped, false)` as unreliable unless `IsPedInAnyVehicle(ped, false)` is true first; use a small wrapper that returns `0` when the ped is not currently in a vehicle.
- Do not grant rewards, vehicle access, or ownership changes from a non-zero vehicle handle unless the current seated state is verified.

## Ammo

- GTA V also has `SetPedAmmoByType`/`GetPedAmmoByType` (same hashes in both games: set `0x5FD1E1F011E76D7E`, get `0x39D22031557946C1`), but the stale reserve-ammo bug and the `RemoveAllPedAmmo` reapply workaround below are RedM-specific: keep that wrapper behind a RedM guard and use the plain native in FiveM.
- Do not rely on direct RedM ammo set/remove natives alone when setting or reducing reserve ammo by type.
- Wrap it instead: record the requested ammo type and amount in the resource-owned ammo map (local player state/helper), then clear ammo with `RemoveAllPedAmmo(ped)` and reapply the full map, so a later call for another type cannot restore a stale value. This avoids RedM ammo state bugs where reserve ammo may not decrease correctly or may restore after direct ammo natives.
- Keep the public helper signature clean, such as `SetAmmoByType(ammoType, amount)`.
- See `memory/redm/native-bugs.md` for the full entry and a reference wrapper.

## Weapon Cosmetics

- For RedM weapon components, verify the final held weapon entity when visual output matters; ped-level component checks can succeed while the held weapon does not render the cosmetic.
- Keep deny/fallback lists for known non-rendering longarm cosmetics instead of offering every shared component as supported.
- Test shared longarm components on the actual weapon models the resource uses before moving the code into a shared cosmetic system.

## Events And State

- Keep event names resource-prefixed with `:server:` or `:client:` side markers.
- The server owns money, inventory, jobs, permissions, ownership, rewards, cooldowns, and saved state.
- State bags are acceptable for visual state, but server-side validation remains required.

## Compatibility Checks

Before moving RedM code into a shared file, check native availability and parameter behavior, entity type behavior, horse/mount/wagon assumptions, animation/control names, weapon/ammo semantics, framework assumptions, and UI/NUI assumptions.
