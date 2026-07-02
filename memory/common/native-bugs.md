# Native Bugs

Track recurring native issues here.

## `SetPedAmmoByType` Reserve Ammo Does Not Decrease Correctly

- Native: `SetPedAmmoByType`
- Runtime: RedM/FiveM CfxLua
- Game build: Unknown
- Date: Unknown
- Symptom: using `SetPedAmmoByType` alone can make reserve ammo fail to decrease correctly.
- Cause: direct reserve updates can leave native ammo state inconsistent.
- Fix / workaround: clear all ped ammo first with `RemoveAllPedAmmo(ped)`, read and reapply the current ammo map from the resource's local player state/helper, then set the requested ammo type.
- Notes: wrap this behavior in a helper and document the parameters with LuaDoc.
- Notes: this is a legacy imported memory entry. Confirm the affected game build and date when the issue is next reproduced.

```lua
local function GetCurrentAmmoMap()
    -- Read from this resource's player data/state cache.
    return {}
end

---@param ammoType string Native ammo type name.
---@param amount integer Reserve ammo amount to apply.
function SetAmmoByType(ammoType, amount)
    local ped = PlayerPedId()
    RemoveAllPedAmmo(ped)

    local ammoMap = GetCurrentAmmoMap()
    ammoMap = type(ammoMap) == "table" and ammoMap or {}

    for ammo, reserve in pairs(ammoMap) do
        SetPedAmmoByType(ped, joaat(ammo), reserve)
    end

    SetPedAmmoByType(ped, joaat(ammoType), amount)
end
```

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
