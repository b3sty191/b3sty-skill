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

- The server is authoritative for world decisions: which routing bucket a player is in, whether an entity may exist, which clients receive a broadcast, and ownership-relevant outcomes (who may use, claim, or delete an entity). Under OneSync, clients own and simulate networked entities and FXServer migrates that ownership; server scripts can read the owner (`NetworkGetEntityOwner`) but not assign it. See Entity Ownership.
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

- OneSync gives each networked entity an owning client when one is in scope. `NetworkGetEntityOwner(entity)` returns the owning player's server ID on the server, or `-1` when no client owns the entity (server-owned/orphaned). Handle `-1` before treating the result as a player. ([NetworkGetEntityOwner](https://docs.fivem.net/natives/?_0x526FEE31))
- Ownership migrates: when the owner leaves scope or the game rebalances, ownership can move to another client. Do not assume the creator stays the owner.
- Code that writes to a networked entity should usually run on, or be requested by, its owner. The server can also set state directly via its OneSync native subset.
- The server decides ownership-relevant outcomes (deletion, locking, damage eligibility), not the client that happens to own the entity at that instant.
- For valuable actions tied to an entity, validate ownership/eligibility server-side against a registry, not against a client claim.
- **Ownership migration is an attack surface.** A client requesting control of an entity it does not own (`REQUEST_CONTROL_EVENT`, used to delete/clone/hijack vehicles and objects, or fire explosions by proxy) is the classic entity exploit. Mitigate on FiveM with `sv_filterRequestControl`: `0` off (default), `1` blocks requests for player-controlled entities (currently occupied vehicles) older than `sv_filterRequestControlSettleTimer` (default `30000` ms), `2` blocks all player-controlled entities, `-1` acts like `2` and warns in console, `3` also blocks settled non-player entities, `4` does not route `REQUEST_CONTROL_EVENT` at all. Any non-zero mode also blocks cross-bucket control requests and senders in strict entity lockdown. Entities flagged server-side with `SetEntityIgnoreRequestControlFilter(entity, true)` bypass every mode and the strict-lockdown check (the cross-bucket check still applies). RedM servers accept the convar, but the filter is compiled only for the GTA V server state and has no effect there, so re-validate ownership against a server registry before honoring a client request on both games. ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/))
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
- Spawn instance content server-side and place it in the matching bucket so it is scoped correctly.
- An entity gets its creating client's routing bucket when it is created, but it does not follow later `SetPlayerRoutingBucket` moves (only the player's own ped moves). Move owned vehicles/props explicitly with `SetEntityRoutingBucket`. Always set the bucket right after server-side creation (once `DoesEntityExist` is true), because RPC creation may run on a nearby client in a different bucket.
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
- `playerEnteredScope` / `playerLeftScope` receive `data` with string fields: `data["for"]` (the player whose scope changed) and `data.player` (the player who entered/left). `for` is a Lua keyword, so use bracket access, and convert with `tonumber(...)` before comparing with server IDs. These events cost more as player count grows (the docs discourage them). Prefer state bags for scoped replication, and never use them for authority.
- Scope events are informational; re-validate any position, distance, or "is near" claim server-side before valuable outcomes.

## Entity Lifecycle Events

- `entityCreating(handle)` fires on the server before a networked entity is replicated and can be canceled with `CancelEvent()` to prevent the entity from being created - the server-side gate for rejecting client-spawned entities you do not want. ([server-events](https://docs.fivem.net/docs/scripting-reference/events/server-events/))
- Model data may be unavailable at creation time (see `memory/common/native-bugs.md`), so do not reject solely because `GetEntityModel` returns `0`; combine type/source/routing-bucket checks at creation time with a later model recheck.
- `entityCreated(handle)` fires after the entity exists and is replicated; this is where model-dependent checks belong.
- `entityRemoved(entity)` fires when a networked entity is deleted.
- Do not yield in `entityCreating`; creation waits on the handler and long work can time out or stall replication. Move heavy work to a thread keyed by the handle. (Canceling population-created entities may make the event re-fire as the game tries to repopulate.)

## Built-in Client Events

These are triggered by the game/client toward the server. They are part of FiveM/OneSync (documented at [server-events](https://docs.fivem.net/docs/scripting-reference/events/server-events/)) and are client-callable, so treat every one as untrusted input. The full hardened treatment (validation, rate-limit, cancel nuance, logging) is in `skills/common/security-performance.md` -> Built-in Client Events.

- `weaponDamageEvent(sender, data)` — client-reported weapon damage. `data.weaponType`, `data.weaponDamage`, `data.hitGlobalId(s)`, `data.willKill`, `data.silenced`, etc. `data.weaponType` is an unsigned 32-bit hash, while `GetHashKey`/backticks return signed values (citizenfx/fivem#3827: `2982836145` vs `-1312131151` for `weapon_rpg`), so normalize before comparing: `local h = data.weaponType; if h > 0x7FFFFFFF then h = h - 0x100000000 end`. It is still client-reported; validate against server-side weapon/entity state, not the field alone.
- `startProjectileEvent(sender, data)` — projectile/thrown creation. Validate `weaponHash`, `projectileHash`, owner, and origin before trusting it.
- `ptFxEvent(sender, data)` (FiveM only) — particle effect playback. Cheap to abuse; rate-limit and bound if it can be used to grief or reveal state.
- `removeAllWeaponsEvent(sender, data)` (FiveM only): `data.pedId` is the network ID of a ped owned by *another* player; the event fires because the sender does not own it. Resolve it with `NetworkGetEntityFromNetworkId(data.pedId)`, and call `CancelEvent()` unless a server-authorized flow (for example an ACE-gated police/admin action) expects this sender to disarm that ped. If nothing legitimate uses it, block it with `block_net_game_event "REMOVE_ALL_WEAPONS_EVENT"`.
- `explosionEvent(sender, ev)` — interceptable server-side with OneSync: `AddEventHandler('explosionEvent', function(sender, ev) ...)`; `ev` has `explosionType`, `posX/Y/Z`, `damageScale`, `ownerNetId`. `CancelEvent()` here stops the server from routing the explosion to other clients ([cookbook](https://docs.fivem.net/docs/cookbook/2019/08/19/onesync-intercepting-game-events-such-as-explosions/)). Note `CancelEvent()` does not stop other handlers and is not reliable for already-applied damage.
- RedM raises `weaponDamageEvent`, `explosionEvent`, `startProjectileEvent`, `respawnPlayerPedEvent`, `lightningEvent`, `clearPedTasksEvent` (`data.pedId`, `data.immediately`), `endLootEvent` (`data.targetId`), and the carriable events (`pickupCarriableEvent`, `placeCarriableOntoParentEvent`, `sendCarriableUpdateCarryStateEvent`, `carriableVehicleStowStartEvent`, `carriableVehicleStowCompleteEvent`). Loot and carriable events are the RedM dupe surface; validate them against server registry state.

Networked-event abuse is best mitigated with the server convars: `sv_filterRequestControl` (FiveM only; `REQUEST_CONTROL_EVENT`), `sv_enableNetworkedPhoneExplosions` (off by default), `sv_enableNetworkedSounds`, `sv_enableNetworkedScriptEntityStates`, and `block_net_game_event "EVENT_NAME"` ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/)).

For all built-in events:

- Read `sender` as the reporting player; never let `sender`-controlled fields grant authority.
- `sender` arrives as a string (the player's server ID); convert with `tonumber(sender)` before numeric comparisons or using it as a table key.
- Validate, bound, and rate-limit. Reject, cancel, or log; do not auto-punish on a single unverified event.
- Log security-relevant ones with bounded fields and rate-limit the logging.

## Creating Networked Entities

- Decide networked vs local at creation. Networked = shared gameplay state (pickups, loot, storage, placed world objects, blockers, owned persistent objects). Local = cosmetic/preview/attached/render-only. See `skills/common/resource-structure.md` -> Local Vs Networked Props.
- Spawn shared gameplay entities from the server (`CreateObject`/`CreateVehicle`/`CreatePed` RPC natives, or `CreateVehicleServerSetter` on FiveM only) so the server decides what spawns and keeps the handle in a registry. This does not make ownership server-controlled: RPC creation is executed by the nearest client, which becomes the initial owner, and ownership migrates with scope. Once `DoesEntityExist(entity)` is true, set the routing bucket explicitly with `SetEntityRoutingBucket(entity, bucket)`.
- For client-created networked entities, the creating client is the initial owner (`NetworkGetFirstEntityOwner`). No server native can take or assign ownership. If the server must control the entity, reject it in `entityCreating` and spawn a server-side replacement, or gate every outcome through the server registry.
- For client-side creation, preload the model (`RequestModel` + `HasModelLoaded`) and release it with `SetModelAsNoLongerNeeded`. Server-side creation takes the model hash directly and needs no model loading. See `skills/common/native-rules.md` -> Performance.
- Keep cleanup for every networked entity: delete on state end, player drop, and resource stop; guard deletes with `DoesEntityExist`.

## Debugging

- Confirm the entity exists on the side you are reading it from before trusting a `0`/`nil`.
- When a client cannot see an entity another client sees, check routing bucket and scope first.
- When ownership-dependent code misbehaves, log `NetworkGetEntityOwner` at the moment of use, not once at creation.
- When a broadcast looks missing, confirm it is not being swallowed by routing bucket or by a client that left scope.
- See `skills/common/debugging.md` for the general flow.

## Review Questions

- Is the server deciding buckets, broadcasts, creation, and ownership-relevant outcomes (use, claim, delete), or is a client claim (including whoever currently owns the entity) being trusted?
- Are client-provided handles and net IDs validated (type, existence, model, owner, bucket, distance) before use?
- Are players and their entities moved into the same routing bucket, and reset on instance end?
- Is any `TriggerClientEvent(name, -1)` broadcast justified, or should it be scoped/targeted?
- Is the resource validating built-in client events (`weaponDamageEvent` and friends) as untrusted input?
- Are networked entities server-created, registered, and cleaned up?
