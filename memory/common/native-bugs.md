# Native Bugs

Native issues that reproduce in both RedM and FiveM. Game-specific ones go in `memory/redm/` or `memory/fivem/`.

## Server-Side `GetEntityModel` Can Return `0` During `entityCreating`

- Native: `GetEntityModel` / `GET_ENTITY_MODEL`
- Runtime: RedM/FiveM server, OneSync, `entityCreating`
- Game build: RedM 1491 (#2944, #2241; peds/objects); FiveM artifact 30707 (#4053, client-created vehicles). The ambient-pickup case (#2924, client 10939 / FXServer 10367) has only an unmerged PR (#2940), and even that leaves pickups without a custom model at 0.
- Date: 2026-07-02
- Symptom: `GetEntityModel(entity)` can return `0` for a valid network entity during `entityCreating` - notably peds/objects (RedM), ambient pickups, or client-created vehicles (FiveM).
- Cause: creation/sync data may not reach the server when `entityCreating` fires; RedM object model parsing is also incomplete in some paths.
- Fix / workaround: never reject or `CancelEvent()` just because `GetEntityModel(entity) == 0`. Validate what is available at creation, then defer model-dependent checks to `entityCreated` or a `CreateThread` keyed by the handle that rechecks after a short wait. Never `Wait` inside `entityCreating` (see `skills/common/runtime.md` -> Yield Hazards). Once the entity exists it cannot be cancelled, so delete it (after `DoesEntityExist`) if the recheck fails.
- Notes: if model allowlisting is security-critical, combine source/routing bucket/type checks at creation with a later model recheck and cleanup path instead of treating `0` as malicious.
- Sources: citizenfx/fivem#2944, citizenfx/fivem#2924 (pickup case; open PR citizenfx/fivem#2940 is only a partial fix), citizenfx/fivem#4053, citizenfx/fivem#2241.

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
