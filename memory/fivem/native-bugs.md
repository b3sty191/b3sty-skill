# FiveM Native Bugs

Track recurring GTA V / FiveM-only native issues here. Bugs that reproduce in both RedM and FiveM belong in `memory/common/native-bugs.md` instead.

## `AddBlipForArea` Ignores `SetBlipAsShortRange`

- Native: `AddBlipForArea` / `_ADD_BLIP_FOR_AREA` (`0xCE5D0E5E315DB238`), `SetBlipAsShortRange` / `SET_BLIP_AS_SHORT_RANGE` (`0xBE8BE4FE60E27B72`)
- Runtime: FiveM client (GTA V)
- Game build: FiveM client 22591 / GTA V legacy build report; exact affected range unknown.
- Date: 2026-07-02
- Symptom: an area/radar blip created with `AddBlipForArea` remains visible on the minimap at long distance even after `SetBlipAsShortRange(blip, true)`.
- Cause: likely upstream GTA V/RAGE radar-area visibility behavior. Regular coordinate blips do not show the same behavior.
- Fix / workaround: do not rely on `SetBlipAsShortRange` for area blips. Create/remove area blips manually by player distance, or use coordinate/radius marker alternatives when short-range behavior matters.
- Notes: `IsBlipOnMinimap` may also return true for radar-area blips, so it is not a reliable workaround for this issue.
- Source: citizenfx/fivem#3973.

## `SetPedHeadBlendData` Followed By Freemode Mask Variation Can Crash

- Native: `SetPedHeadBlendData` / `SET_PED_HEAD_BLEND_DATA` (`0x9414E18B9434C2FE`), `SetPedComponentVariation` / `SET_PED_COMPONENT_VARIATION` (`0x262B14F48D29DE80`)
- Runtime: FiveM client (GTA V) CfxLua
- Game build: GTA V builds 3258 and 3751 reports; exact affected range unknown.
- Date: 2026-07-02
- Symptom: calling `SetPedHeadBlendData` on a freemode ped, then applying some mask component variations, can crash the FiveM client.
- Cause: unknown freemode head blend/component interaction. Custom streamed freemode head assets can make related failures more likely and should be ruled out during debugging.
- Fix / workaround: avoid applying known crashing mask drawables immediately after `SetPedHeadBlendData`. Gate/test mask drawables, avoid the sequence in bulk appearance apply paths, and prefer a staged apply path with rollback/fallback for risky masks.
- Notes: reported repro uses `mp_m_freemode_01`, mask component `1`, drawable `28`, texture `0`; disabling the `SetPedHeadBlendData` path avoids the crash.
- Source: citizenfx/fivem#4037.

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
