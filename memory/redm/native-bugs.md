# RedM Native Bugs

Track recurring RDR3 / RedM-only native issues here. Bugs that reproduce in both RedM and FiveM belong in `memory/common/native-bugs.md` instead.

## Server-Side `GetEntityHealth` Returns `0`

- Native: `GetEntityHealth` / `GET_ENTITY_HEALTH` (RDR3 client hash `0x82368787EA73C0F7`; server CFX native `0x8E3222B7`)
- Runtime: RedM server (RDR3) CfxLua
- Game build: Unknown
- Date: 2026-07-02
- Symptom: calling `GetEntityHealth(entity)` on the server can return `0` consistently, even when the entity is alive.
- Cause: unknown RedM server native/runtime behavior. Client-side health reads are not affected in the same way.
- Fix / workaround: do not use server-side `GetEntityHealth` as the source of truth in RedM; use client-side reads only for UI/visuals.
- Related rules: `skills/redm/rules.md` -> Entity Health (server-owned state, handling client-reported health).
- Notes: on the server, call the named global `GetEntityHealth`, not `Citizen.InvokeNative` with the RDR3 client hash; FXServer does not register game hashes.
- Notes: confirm the affected game build when the issue is next reproduced.

## Server-Side `GetVehiclePedIsIn(ped, false)` Can Return The Last Vehicle

- Native: `GetVehiclePedIsIn` / `GET_VEHICLE_PED_IS_IN` (RDR3 client hash `0x9A9112A0FE9A4713`; server CFX native `0xAFE92319`)
- Runtime: RedM server (RDR3) CfxLua, OneSync
- Game build: RedM/30408, FXServer-master server v1.0.0.29199 win32 report.
- Date: 2026-07-02
- Symptom: server-side `GetVehiclePedIsIn(ped, false)` can return the last vehicle handle after the ped has exited and is on foot. `GetVehiclePedIsIn(ped, true)` returns the same handle.
- Cause: unknown RedM server native/runtime behavior; the `lastVehicle` flag is not respected in the reported server-side path.
- Fix / workaround: guard the server-side vehicle lookup with `IsPedInAnyVehicle(ped, false)` and return `0` when the ped is not currently in a vehicle.
- Notes: do not use server-side `GetVehiclePedIsIn(ped, false) ~= 0` alone as proof that a RedM player is currently seated in a vehicle.
- Notes: on the server, call the named globals, not `Citizen.InvokeNative` with the RDR3 client hash; FXServer does not register game hashes.
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

- Native: `SetPedAmmoByType` / `SET_PED_AMMO_BY_TYPE` (`0x5FD1E1F011E76D7E`), `_REMOVE_AMMO_FROM_PED` (`0xF4823C813CB8277D`), `_REMOVE_AMMO_FROM_PED_BY_TYPE` (`0xB6CFEC32E3742779`), workaround uses `RemoveAllPedAmmo` / `_REMOVE_ALL_PED_AMMO` (`0x1B83C0DEEBCBB214`)
- Runtime: RedM (RDR3) CfxLua
- Game build: Unknown; citizenfx/fivem#3980 reports RedM all versions.
- Date: 2026-07-02
- Symptom: direct RedM ammo set/remove natives can fail to decrease ammo, only change it temporarily, or allow the old ammo value to restore after shooting, reload, or weapon switching.
- Cause: direct reserve/removal updates can leave native ammo state inconsistent with RedM weapon/inventory state.
- Fix / workaround: own ammo in resource/server state, then apply the full desired ammo map in one wrapper. The wrapper records the requested amount in the owned ammo map first, then clears all ped ammo with `RemoveAllPedAmmo(ped)` and reapplies the whole map, so a later call for another type cannot restore a stale value.
- Notes: wrap this behavior in a helper and document the parameters with LuaDoc.
- Notes: RedM-only workaround. Both games pool ammo by type (`SetPedAmmoByType` has the same hash `0x5FD1E1F011E76D7E` in GTA V), but this wrapper depends on RDR3's `_REMOVE_ALL_PED_AMMO` and targets a RedM-specific stale-ammo bug, so keep it behind a RedM guard. Confirm the affected game build and date when the issue is next reproduced.
- Source: citizenfx/fivem#3980.

```lua
local Controller = {}

function Controller:GetCurrentAmmoMap()
    -- Read from this resource's player data/state cache.
    return {}
end

---@param ammoMap table<string, integer> Ammo type name -> reserve amount.
function Controller:SetCurrentAmmoMap(ammoMap)
    -- Write to this resource's player data/state cache.
end

---@param ammoType string Native ammo type name.
---@param amount integer Reserve ammo amount to apply.
function Controller:SetAmmoByType(ammoType, amount)
    local ped = PlayerPedId()
    local ammoMap = self:GetCurrentAmmoMap()
    ammoMap = type(ammoMap) == "table" and ammoMap or {}

    -- Update owned state first so the next call reapplies this amount, not a stale one.
    ammoMap[ammoType] = amount
    self:SetCurrentAmmoMap(ammoMap)

    RemoveAllPedAmmo(ped)
    for ammo, reserve in pairs(ammoMap) do
        SetPedAmmoByType(ped, joaat(ammo), reserve)
    end
end
```

## Shared Longarm Cosmetic Components May Not Render On Held Weapons

- Native: `GiveWeaponComponentToEntity` / `_GIVE_WEAPON_COMPONENT_TO_ENTITY` (`0x74C9090FDD1BB48E`, target can be a ped or a weapon object), `_HAS_PED_GOT_WEAPON_COMPONENT` (`0xBBC67A6F965C688A`), `HAS_WEAPON_GOT_WEAPON_COMPONENT` (`0x76A18844E743BF91`)
- Runtime: RedM client (RDR3) CfxLua
- Game build: RDR2 build 1491 report; exact affected range unknown.
- Date: 2026-07-02
- Symptom: some shared longarm cosmetic components apply to a ped and can render on standalone weapon objects, but do not render on the final held weapon entity.
- Cause: unknown RedM weapon component/rendering behavior for specific shared longarm cosmetics.
- Fix / workaround: verify cosmetics on the actual held weapon entity, not only with the ped-level check. Keep per-component fallback/deny lists for known non-rendering cosmetics and do not promise unsupported visual variants in UI.
- Notes: reported failing examples include `COMPONENT_LONGARM_GRIPSTOCK_TINT_PEARL`, `COMPONENT_LONGARM_GRIP_MATERIAL_BURLED`, and `COMPONENT_LONGARM_WRAP_MATERIAL_LEATHER` on rolling block/carcano/bolt-action longarms.
- Notes: per citizenfx/fivem#4026, the standalone weapon object path that does render uses the same `GiveWeaponComponentToEntity` native; the failure is specific to the held weapon. Recheck when reproduced.
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
