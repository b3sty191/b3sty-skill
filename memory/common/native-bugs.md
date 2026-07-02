# Native Bugs

Track recurring native issues that reproduce in both RedM and FiveM here. RedM-only or FiveM-only bugs belong in `memory/redm/` or `memory/fivem/` instead.

## Server-Side `GetEntityModel` Can Return `0` During `entityCreating`

- Native: `GetEntityModel` / `GET_ENTITY_MODEL`
- Runtime: RedM/FiveM server, OneSync, `entityCreating`
- Game build: RedM build 1491 and FiveM build 3258/3751 reports; exact affected range unknown.
- Date: 2026-07-02
- Symptom: `GetEntityModel(entity)` can return `0` for a valid network entity during `entityCreating`, including peds, pickups, or client-created vehicles.
- Cause: creation/sync data may not be available to the server when `entityCreating` fires. RedM object model parsing is also known to be incomplete in some paths.
- Fix / workaround: do not reject or `CancelEvent()` solely because `GetEntityModel(entity) == 0`. Validate what is available at creation time, then defer model-dependent checks until `entityCreated` or after a short wait when the entity data has synced.
- Notes: if model allowlisting is security-critical, combine source/routing bucket/type checks at creation time with a later model recheck and cleanup path instead of assuming `0` means malicious.
- Sources: citizenfx/fivem#2944, citizenfx/fivem#2924, citizenfx/fivem#4053, citizenfx/fivem#2241.

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
