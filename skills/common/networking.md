# Networking And OneSync Rules

Use this file when a RedM/FiveM resource creates networked entities, depends on entity ownership, uses routing buckets/instances, broadcasts to clients, reacts to player scope, or handles built-in client events (`weaponDamageEvent`, `startProjectileEvent`, `ptFxEvent`, and the rest).

This file covers the multiplayer/OneSync layer. Native marshalling is in `skills/common/native-usage.md`; entity safety/caching is in `skills/common/native-rules.md`; the untrusted-boundary rules are in `skills/common/security-performance.md`.

## Contents

- Sides And Authority
- Handles And Net IDs
- Entity Ownership
- Routing Buckets
- Broadcasting And Scoped Messages
- Player Scope
- Entity Lifecycle Events
- Built-in Client Events
- Creating Networked Entities
- Debugging
- Review Questions

## Sides And Authority

- The server is authoritative for world decisions: who owns an entity, which routing bucket a player is in, whether an entity may exist, and which clients receive a broadcast.
- `IsDuplicityVersion()` returns `true` on the server. Use it in shared scripts to branch by side.
- Server-side game natives are a limited OneSync subset (entity getters/setters, player state). Most game natives are client-only; see `skills/common/native-usage.md` -> Client, Server, And Shared Context.
- Known server-side native quirks live in `memory/`: RedM `GetEntityHealth` returning `0`, `GetVehiclePedIsIn` returning the last vehicle, `GetEntityModel` returning `0` during `entityCreating`. Check `memory/common/native-bugs.md` and `memory/redm/native-bugs.md` before building server logic on a native read.

## Handles And Net IDs

- A local entity handle is process-local and only valid on the side that holds it. A client handle is meaningless on the server and vice versa.
- Net IDs (`NetworkGetNetworkIdFromEntity(entity)`) identify the same entity across sides and clients. Convert at the boundary:
  ```lua
  local netId = NetworkGetNetworkIdFromEntity(entity)       -- send this to other side
  local entity = NetworkGetEntityFromNetworkId(netId)       -- recover the handle
  ```
- Recovered handles may be `0` or invalid. Re-check with `DoesEntityExist` before use.
- Treat client-provided net IDs and handles as untrusted. Validate type, existence, entity type, model, ownership, routing bucket, and distance before trusting them for rewards, ownership, permissions, or saved state.
- Network IDs can be recycled after an entity is deleted. Never cache a net ID long-term as a stable identity; re-resolve or keep a server-side registry instead.

## Entity Ownership

- OneSync gives each networked entity an owning client. `NetworkGetEntityOwner(entity)` returns that owner's player source on the server. ([NetworkGetEntityOwner](https://docs.fivem.net/natives/?_0x526FEE31))
- Ownership migrates: when the owner leaves scope or the game rebalances, ownership can move to another client. Do not assume the creator stays the owner.
- Code that writes to a networked entity should usually run on, or be requested by, its owner. The server can also set state directly via its OneSync native subset.
- The server decides ownership-relevant outcomes (deletion, locking, damage eligibility), not the client that happens to own the entity at that instant.
- For valuable actions tied to an entity, validate ownership/eligibility server-side against a registry, not against a client claim.
- **Ownership migration is an attack surface.** A client requesting control of an entity it does not own (`REQUEST_CONTROL_EVENT`, used to delete/clone/hijack vehicles and objects, or fire explosions by proxy) is the classic entity exploit. Mitigate at the server level with `sv_filterRequestControl` (modes 0-4; mode `4` does not route `REQUEST_CONTROL_EVENT` at all) and re-validate ownership against a server registry before honoring a client request. ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/))
- Treat client "spawn" or "give me this loot/pickup/vehicle" requests like any give-value request: the server decides what spawns, who owns it, and who may claim it. See `skills/common/security-performance.md` -> Give-Value Event Hardening and Entity And Net ID Validation.

## Routing Buckets

- Routing buckets (sometimes called dimensions/instances) partition the world. Players and entities in different buckets cannot see or interact with each other.
- Move both the player and their relevant entities together when entering an instance:
  ```lua
  SetPlayerRoutingBucket(player, bucket)
  SetEntityRoutingBucket(entity, bucket)
  ```
- Read with `GetPlayerRoutingBucket(player)` and `GetEntityRoutingBucket(entity)`. Default bucket is `0`.
- Players keep their bucket across reconnects only if the server re-applies it; store intended bucket in server/persistence state and reapply on join.
- Spawn instance content server-side and place it in the matching bucket so it is scoped correctly. Entities spawned client-side do not automatically follow a player's bucket.
- Validate that an entity a client references is in the same bucket as that player before acting on it; cross-bucket references are a common exploit/teleport vector.
- Clear/reset bucket assignments on instance end, player drop, and resource stop so players are not left in an empty private world.

## Broadcasting And Scoped Messages

- `TriggerClientEvent(name, -1)` sends to every connected client. Avoid it for targeted or frequent data; it scales with player count and wastes bandwidth.
- Send to a single client with `TriggerClientEvent(name, playerId, ...)`.
- Scope "players nearby" work by tracking scope or computing recipients from server-side positions, then trigger per-recipient or to a small set. Do not let the client tell the server who to broadcast to.
- Prefer state bags over manual broadcasts for replicated visible state: the server writes the state, each client reacts via `AddStateBagChangeHandler`. See `skills/common/resource-structure.md` -> State.
- Keep broadcast payloads small and send only the field that changed.

## Player Scope

- OneSync streams entities to clients based on scope. A client only receives data for entities in its scope.
- `playerEnteredScope` and `playerLeftScope` fire with `{ for = playerId, player = playerId }`: another player entered/left the listener's scope. Use them for proximity setup/teardown, not for authority.
- Scope events are informational; re-validate any position, distance, or "is near" claim server-side before valuable outcomes.

## Entity Lifecycle Events

- `entityCreating(handle)` fires on the server before a networked entity is replicated and can be canceled with `CancelEvent()` to prevent the entity from being created - the server-side gate for rejecting client-spawned entities you do not want. ([server-events](https://docs.fivem.net/docs/scripting-reference/events/server-events/))
- Model data may be unavailable at creation time (see `memory/common/native-bugs.md`), so do not reject solely because `GetEntityModel` returns `0`; combine type/source/routing-bucket checks at creation time with a later model recheck.
- `entityCreated(handle)` fires after the entity exists and is replicated; this is where model-dependent checks belong.
- `entityRemoved(entity)` fires when a networked entity is deleted.
- Do not yield in `entityCreating`; creation waits on the handler and long work can time out or stall replication. Move heavy work to a thread keyed by the handle. (Canceling population-created entities may make the event re-fire as the game tries to repopulate.)

## Built-in Client Events

These are triggered by the game/client toward the server. They are part of FiveM/OneSync (documented at [server-events](https://docs.fivem.net/docs/scripting-reference/events/server-events/)) and are client-callable, so treat every one as untrusted input. The full hardened treatment (validation, rate-limit, cancel nuance, logging) is in `skills/common/security-performance.md` -> Built-in Client Events.

- `weaponDamageEvent(sender, data)` — client-reported weapon damage. `data.weaponType`, `data.weaponDamage`, `data.hitGlobalId(s)`, `data.willKill`, `data.silenced`, etc. `data.weaponType` has been reported to carry incorrect hashes (citizenfx/fivem#3827); validate against server-side weapon/entity state, not the field alone.
- `startProjectileEvent(sender, data)` — projectile/thrown creation. Validate `weaponHash`, `projectileHash`, owner, and origin before trusting it.
- `ptFxEvent(sender, data)` — particle effect playback. Cheap to abuse; rate-limit and bound if it can be used to grief or reveal state.
- `removeAllWeaponsEvent(sender, data)` — `data.pedId`; confirm the sender owns/controls that ped before honoring it.
- `explosionEvent(sender, ev)` — interceptable server-side with OneSync: `AddEventHandler('explosionEvent', function(sender, ev) ...)`; `ev` has `explosionType`, `posX/Y/Z`, `damageScale`, `ownerNetId`. `CancelEvent()` here stops the server from routing the explosion to other clients ([cookbook](https://docs.fivem.net/docs/cookbook/2019/08/19/onesync-intercepting-game-events-such-as-explosions/)). Note `CancelEvent()` does not stop other handlers and is not reliable for already-applied damage.

Networked-event abuse is best mitigated with the server convars: `sv_filterRequestControl` (`REQUEST_CONTROL_EVENT`), `sv_enableNetworkedPhoneExplosions` (off by default), `sv_enableNetworkedSounds`, `sv_enableNetworkedScriptEntityStates`, and `block_net_game_event "EVENT_NAME"` ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/)).

For all built-in events:

- Read `sender` as the reporting player; never let `sender`-controlled fields grant authority.
- Validate, bound, and rate-limit. Reject, cancel, or log; do not auto-punish on a single unverified event.
- Log security-relevant ones with bounded fields and rate-limit the logging.

## Creating Networked Entities

- Decide networked vs local at creation. Networked = shared gameplay state (pickups, loot, storage, placed world objects, blockers, owned persistent objects). Local = cosmetic/preview/attached/render-only. See `skills/common/resource-structure.md` -> Local Vs Networked Props.
- Create shared gameplay entities server-side (`CreateObject(...)`, etc.) so ownership and routing bucket are server-controlled. Keep a server registry of created entities.
- For client-created networked entities, the creating client becomes the initial owner; re-claim ownership server-side if the server must control it.
- Preload the model before creation and release it after with `SetModelAsNoLongerNeeded`; see `skills/common/native-rules.md` -> Performance.
- Keep cleanup for every networked entity: delete on state end, player drop, and resource stop; guard deletes with `DoesEntityExist`.

## Debugging

- Confirm the entity exists on the side you are reading it from before trusting a `0`/`nil`.
- When a client cannot see an entity another client sees, check routing bucket and scope first.
- When ownership-dependent code misbehaves, log `NetworkGetEntityOwner` at the moment of use, not once at creation.
- When a broadcast looks missing, confirm it is not being swallowed by routing bucket or by a client that left scope.
- See `skills/common/debugging.md` for the general flow.

## Review Questions

- Is the server deciding ownership, buckets, broadcasts, and creation, or is a client claim being trusted?
- Are client-provided handles and net IDs validated (type, existence, model, owner, bucket, distance) before use?
- Are players and their entities moved into the same routing bucket, and reset on instance end?
- Is any `TriggerClientEvent(name, -1)` broadcast justified, or should it be scoped/targeted?
- Is the resource validating built-in client events (`weaponDamageEvent` and friends) as untrusted input?
- Are networked entities server-created, registered, and cleaned up?
