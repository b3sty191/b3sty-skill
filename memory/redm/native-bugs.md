# RedM Native Bugs

Track recurring RDR3 / RedM-only native issues here. Bugs that reproduce in both RedM and FiveM belong in `memory/common/native-bugs.md` instead.

## Server-Side `GetEntityHealth` Returns `0`

- Native: `GetEntityHealth` / `GET_ENTITY_HEALTH` (`0x82368787EA73C0F7`)
- Runtime: RedM server (RDR3) CfxLua
- Game build: Unknown
- Date: 2026-07-02
- Symptom: calling `GetEntityHealth(entity)` on the server can return `0` consistently, even when the entity is alive.
- Cause: unknown RedM server native/runtime behavior. Client-side health reads are not affected in the same way.
- Fix / workaround: do not use server-side `GetEntityHealth` as the source of truth in RedM. Use client-side reads only for UI/visual behavior. For server-side decisions, keep server-owned eligibility or health-like state where possible, or validate through server-controlled action state instead of trusting a direct health native read.
- Notes: if client-reported health is unavoidable, treat it as untrusted input: type-check, clamp, rate-limit, compare against expected server-side state, and never use it as the only condition for rewards, damage, permissions, or anti-abuse checks.
- Notes: confirm the affected game build when the issue is next reproduced.

## Server-Side `GetVehiclePedIsIn(ped, false)` Can Return The Last Vehicle

- Native: `GetVehiclePedIsIn` / `GET_VEHICLE_PED_IS_IN` (`0x9A9112A0FE9A4713`)
- Runtime: RedM server (RDR3) CfxLua, OneSync
- Game build: RedM/30408, FXServer-master server v1.0.0.29199 win32 report.
- Date: 2026-07-02
- Symptom: server-side `GetVehiclePedIsIn(ped, false)` can return the last vehicle handle after the ped has exited and is on foot. `GetVehiclePedIsIn(ped, true)` returns the same handle.
- Cause: unknown RedM server native/runtime behavior; the `lastVehicle` flag is not respected in the reported server-side path.
- Fix / workaround: guard the server-side vehicle lookup with `IsPedInAnyVehicle(ped, false)` and return `0` when the ped is not currently in a vehicle.
- Notes: do not use server-side `GetVehiclePedIsIn(ped, false) ~= 0` alone as proof that a RedM player is currently seated in a vehicle.
- Source: citizenfx/fivem#4006.

```lua
local Controller = {}

---@param ped number
---@return number
function Controller:GetCurrentVehicle(ped)
    if not IsPedInAnyVehicle(ped, false) then
        return 0
    end

    return GetVehiclePedIsIn(ped, false)
end
```

## RedM Ammo Set/Remove Natives Can Leave Ammo State Stale

- Native: `SetPedAmmoByType` / `SET_PED_AMMO_BY_TYPE` (`0x5FD1E1F011E76D7E`), `_REMOVE_AMMO_FROM_PED` (`0xF4823C813CB8277D`), `_REMOVE_AMMO_FROM_PED_BY_TYPE` (`0xB6CFEC32E3742779`)
- Runtime: RedM (RDR3) CfxLua
- Game build: Unknown; citizenfx/fivem#3980 reports RedM all versions.
- Date: 2026-07-02
- Symptom: direct RedM ammo set/remove natives can fail to decrease ammo, only change it temporarily, or allow the old ammo value to restore after shooting, reload, or weapon switching.
- Cause: direct reserve/removal updates can leave native ammo state inconsistent with RedM weapon/inventory state.
- Fix / workaround: own ammo in resource/server state, then apply the full desired ammo map in one wrapper. Clear all ped ammo first with `RemoveAllPedAmmo(ped)`, read and reapply the current ammo map from the resource's local player state/helper, then set the requested ammo type.
- Notes: wrap this behavior in a helper and document the parameters with LuaDoc.
- Notes: RedM-only. Ammo by type is an RDR3 concept; FiveM/GTA V uses different ammo natives. Confirm the affected game build and date when the issue is next reproduced.
- Source: citizenfx/fivem#3980.

```lua
local Controller = {}

function Controller:GetCurrentAmmoMap()
    -- Read from this resource's player data/state cache.
    return {}
end

---@param ammoType string Native ammo type name.
---@param amount integer Reserve ammo amount to apply.
function Controller:SetAmmoByType(ammoType, amount)
    local ped = PlayerPedId()
    RemoveAllPedAmmo(ped)

    local ammoMap = self:GetCurrentAmmoMap()
    ammoMap = type(ammoMap) == "table" and ammoMap or {}

    for ammo, reserve in pairs(ammoMap) do
        SetPedAmmoByType(ped, joaat(ammo), reserve)
    end

    SetPedAmmoByType(ped, joaat(ammoType), amount)
end
```

## Shared Longarm Cosmetic Components May Not Render On Held Weapons

- Native: RDR3 weapon component apply path (`0x74C9090FDD1BB48E`), `_HAS_PED_GOT_WEAPON_COMPONENT` (`0xBBC67A6F965C688A`), `HAS_WEAPON_GOT_WEAPON_COMPONENT` (`0x76A18844E743BF91`)
- Runtime: RedM client (RDR3) CfxLua
- Game build: RDR2 build 1491 report; exact affected range unknown.
- Date: 2026-07-02
- Symptom: some shared longarm cosmetic components apply to a ped and can render on standalone weapon objects, but do not render on the final held weapon entity.
- Cause: unknown RedM weapon component/rendering behavior for specific shared longarm cosmetics.
- Fix / workaround: verify cosmetics on the actual held weapon entity, not only with the ped-level check. Keep per-component fallback/deny lists for known non-rendering cosmetics and do not promise unsupported visual variants in UI.
- Notes: reported failing examples include `COMPONENT_LONGARM_GRIPSTOCK_TINT_PEARL`, `COMPONENT_LONGARM_GRIP_MATERIAL_BURLED`, and `COMPONENT_LONGARM_WRAP_MATERIAL_LEATHER` on rolling block/carcano/bolt-action longarms.
- Source: citizenfx/fivem#4026.

## Template

Copy this block when adding a new entry, then fill it in. Leave it blank intentionally - it is a skeleton for future entries, not a real bug.

- Native:
- Runtime:
- Game build:
- Date:
- Symptom:
- Cause:
- Fix / workaround:
- Notes:
