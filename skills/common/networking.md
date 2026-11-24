# Networking And OneSync Rules

Use for RedM/FiveM networked entities, entity ownership, routing buckets/instances, broadcasts, player scope and built-in client events (`weaponDamageEvent`, `startProjectileEvent`, `ptFxEvent`, ...). Native marshalling: `skills/common/native-usage.md`. Entity safety/caching: `skills/common/native-rules.md`. Untrusted boundaries: `skills/common/security-performance.md`.

## Contents

Sides And Authority - Handles And Net IDs - Entity Ownership - Routing Buckets - Broadcasting And Scoped Messages - Player Scope - Entity Lifecycle Events - Built-in Client Events - Creating Networked Entities - Debugging - Review Questions

## Sides And Authority

- Server decides: routing buckets, whether an entity may exist, broadcast recipients, ownership outcomes (use/claim/delete). Under OneSync clients own and simulate networked entities and FXServer migrates ownership - the server reads the owner (`NetworkGetEntityOwner`), never assigns it (Entity Ownership).
- `IsDuplicityVersion()` is `true` on the server - branch by side with it in shared scripts.
- Server-side game natives are a limited OneSync subset (entity getters/setters, player state); the rest are client-only - `skills/common/native-usage.md` -> Client, Server, And Shared Context.
- Server-side native quirks live in `memory/`: RedM `GetEntityHealth` returns `0`, `GetVehiclePedIsIn` the last vehicle, `GetEntityModel` `0` during `entityCreating` - check `memory/common/native-bugs.md` and `memory/redm/native-bugs.md` before trusting a server-side read.

## Handles And Net IDs

- Entity handles are process-local: a client handle is meaningless on the server and vice versa.
- Net IDs (`NetworkGetNetworkIdFromEntity(entity)`) identify the entity across sides and clients; convert at the boundary:
  ```lua
  local netId = NetworkGetNetworkIdFromEntity(entity)   -- send to other side
  local entity = NetworkGetEntityFromNetworkId(netId)   -- recover the handle
  ```
- Recovered handles may be `0`/invalid - re-check `DoesEntityExist`.
- Client net IDs/handles are untrusted: check type, existence, entity type, model, ownership, routing bucket and distance before rewards, ownership, permissions or saved state.
- Net IDs are recycled after deletion - never cache one as an identity; re-resolve, or keep a server-side registry.

## Entity Ownership

- An entity has an owning client whenever one is in scope: `NetworkGetEntityOwner(entity)` gives that player's server ID, or `-1` when none owns it (server-owned/orphaned) - handle `-1` before treating it as a player. ([NetworkGetEntityOwner](https://docs.fivem.net/natives/?_0x526FEE31))
- Ownership migrates on scope loss or engine rebalance; the creator does not stay owner.
- Write to a networked entity from its owner, or request it there; the server can also set state via its OneSync native subset.
- The server, not the momentary owner, decides deletion, locking, damage eligibility and other ownership outcomes - validate valuable entity actions against a server registry, never a client claim.
- **Ownership migration is an attack surface.** A client requesting control of an entity it does not own (`REQUEST_CONTROL_EVENT`: delete/clone/hijack vehicles and objects, explosions by proxy) is the classic entity exploit. FiveM mitigates with `sv_filterRequestControl`: `0` off (default); `1` blocks requests for player-controlled entities (currently occupied vehicles) older than `sv_filterRequestControlSettleTimer` (default `30000` ms); `2` all player-controlled entities; `-1` like `2` plus a console warning; `3` also settled non-player entities; `4` does not route `REQUEST_CONTROL_EVENT` at all. Any non-zero mode also blocks cross-bucket control requests and senders in strict entity lockdown. `SetEntityIgnoreRequestControlFilter(entity, true)` bypasses every mode and the strict-lockdown check (cross-bucket still applies). RedM accepts the convar but the filter is compiled only for the GTA V server state and does nothing there, so on both games re-validate ownership against a server registry before honoring a client request. ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/))
- Client spawn/claim requests ("give me this loot/pickup/vehicle") are give-value requests: the server decides what spawns, who owns it, who may claim it - `skills/common/give-value-hardening.md` -> Give-Value Event Hardening, `skills/common/client-input-validation.md` -> Entity And Net ID Validation.

## Routing Buckets

- Buckets (dimensions/instances) partition the world: different buckets cannot see or interact. Default `0`; read with `GetPlayerRoutingBucket(player)`/`GetEntityRoutingBucket(entity)`.
- Move the player and their relevant entities together into an instance:
  ```lua
  SetPlayerRoutingBucket(player, bucket)
  SetEntityRoutingBucket(entity, bucket)
  ```
- Buckets survive a reconnect only if the server re-applies them - keep the intended bucket in server/persistence state and reapply on join.
- Spawn instance content server-side into the matching bucket.
- An entity inherits its creator's bucket and ignores later `SetPlayerRoutingBucket` moves (only the player's own ped moves), so move owned vehicles/props explicitly with `SetEntityRoutingBucket`. Set it right after server-side creation (once `DoesEntityExist` is true): RPC creation may run on a nearby client in another bucket.
- Check a client-referenced entity shares that player's bucket; cross-bucket references are a common exploit/teleport vector.
- Clear buckets on instance end, player drop and resource stop so nobody is left in an empty private world.

## Broadcasting And Scoped Messages

- `TriggerClientEvent(name, -1)` hits every client and scales with player count - avoid it for targeted or frequent data; one client is `TriggerClientEvent(name, playerId, ...)`.
- Compute "players nearby" from tracked scope or server-side positions, then trigger per recipient or small set. Never let the client name the recipients.
- Prefer state bags to manual broadcasts for replicated visible state: server writes, each client reacts via `AddStateBagChangeHandler` (`skills/common/resource-structure.md` -> State).
- Keep payloads small; send only the field that changed.

## Player Scope

- A client only receives data for entities in its scope.
- Default culling radius is 424 m, measured in 2D (XY) - a helicopter 1 km straight overhead still counts as near. Priority: `SetEntityDistanceCullingRadius` (per entity, unvalidated) > `SetPlayerCullingRadius` (per player, `0` = default) > 424 m, and only while `onesync_distanceCulling` is on (the default). Cost grows with r²: 424 -> 600 m is about twice the area. (verified: ServerGameState.cpp / ServerGameState_Scripting.cpp, FXServer 35945)
- Player slots per client are fixed: at most 128 other players on FiveM, 32 on RedM. Once full, a further in-scope player is never created there - invisible, no error, cap not raisable server-side. In crowds shrink that player's `SetPlayerCullingRadius` so the nearest players take the slots. (verified: ServerGameState.cpp, FXServer 35945)
- `playerEnteredScope`/`playerLeftScope` pass `data` with string fields `data["for"]` (whose scope changed) and `data.player` (who entered/left): `for` is a Lua keyword, so bracket access, and `tonumber(...)` before comparing with server IDs. They cost more as player count grows (the docs discourage them) - prefer state bags for scoped replication, never authority.
- Scope events are informational; re-validate any position, distance or "is near" claim server-side before valuable outcomes.

## Entity Lifecycle Events

- `entityCreating(handle)` fires server-side before a networked entity replicates; `CancelEvent()` prevents creation - the gate for rejecting client-spawned entities you do not want. ([server-events](https://docs.fivem.net/docs/scripting-reference/events/server-events/))
- Model data may be missing then (`memory/common/native-bugs.md`): never reject solely because `GetEntityModel` returns `0` - combine type/source/routing-bucket checks at creation with a later model recheck.
- `entityCreated(handle)` fires once the entity exists and is replicated: model-dependent checks go there. `entityRemoved(entity)` fires on deletion.
- Never yield in `entityCreating`: creation waits on the handler, so long work can time out or stall replication - move heavy work to a thread keyed by the handle. (Canceling population-created entities may re-fire it as the game repopulates.)

## Built-in Client Events

Game/client-to-server events, part of FiveM/OneSync ([server-events](https://docs.fivem.net/docs/scripting-reference/events/server-events/)) and client-callable, so every one is untrusted input. Full hardening (validation, rate-limit, cancel nuance, logging): `skills/common/client-input-validation.md` -> Built-in Client Events.

- `weaponDamageEvent(sender, data)` — client-reported damage: `data.weaponType`, `data.weaponDamage`, `data.hitGlobalId(s)`, `data.willKill`, `data.silenced`, etc. `data.weaponType` is unsigned 32-bit while `GetHashKey`/backticks are signed (citizenfx/fivem#3827: `2982836145` vs `-1312131151` for `weapon_rpg`) - normalize: `local h = data.weaponType; if h > 0x7FFFFFFF then h = h - 0x100000000 end`. Validate against server-side weapon/entity state, not the field.
- `weaponDamageEvent` traps: `data.weaponDamage` is `0` unless `overrideDefaultDamage` is set, so it is not the damage dealt; `data.hitComponent` is parsed only when `data.damageType >= 2` (ped hits) - type 0/1 carry `localPos` instead - and RedM's event has no `hitComponent` field. (verified: ServerGameState.cpp FIVE and RDR3 parsers, FXServer 35945)
- `startProjectileEvent(sender, data)` — projectile/thrown creation; validate `weaponHash`, `projectileHash`, owner, origin.
- `ptFxEvent(sender, data)` (FiveM only) — particle playback; cheap to abuse, so rate-limit and bound where it can grief or reveal state.
- `removeAllWeaponsEvent(sender, data)` (FiveM only) — `data.pedId` is the net ID of a ped owned by *another* player (it fires because the sender does not own it). Resolve with `NetworkGetEntityFromNetworkId(data.pedId)` and `CancelEvent()` unless a server-authorized flow (e.g. ACE-gated police/admin) expects this sender to disarm that ped; if nothing legitimate uses it, `block_net_game_event "REMOVE_ALL_WEAPONS_EVENT"`.
- `explosionEvent(sender, ev)` — interceptable server-side with OneSync: `AddEventHandler('explosionEvent', function(sender, ev) ...)`; `ev` has `explosionType`, `posX/Y/Z`, `damageScale`, `ownerNetId`. `CancelEvent()` stops the server routing it to other clients ([cookbook](https://docs.fivem.net/docs/cookbook/2019/08/19/onesync-intercepting-game-events-such-as-explosions/)) but does not stop other handlers and is unreliable for already-applied damage.
- RedM raises `weaponDamageEvent`, `explosionEvent`, `startProjectileEvent`, `respawnPlayerPedEvent`, `lightningEvent`, `clearPedTasksEvent` (`data.pedId`, `data.immediately`), `endLootEvent` (`data.targetId`) and the carriables (`pickupCarriableEvent`, `placeCarriableOntoParentEvent`, `sendCarriableUpdateCarryStateEvent`, `carriableVehicleStowStartEvent`, `carriableVehicleStowCompleteEvent`). Loot and carriable events are the RedM dupe surface - validate against server registry state.

Convars that blunt networked-event abuse: `sv_filterRequestControl` (FiveM only; `REQUEST_CONTROL_EVENT`), `sv_enableNetworkedPhoneExplosions` (off by default), `sv_enableNetworkedSounds`, `sv_enableNetworkedScriptEntityStates`, `block_net_game_event "EVENT_NAME"` ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/)).

For all of them: `sender` is the reporting player, never authority - no `sender`-controlled field may grant it - and arrives as a string server ID, so `tonumber(sender)` before numeric comparison or table keys. Validate, bound, rate-limit; reject, cancel or log, never auto-punish on one unverified event; log security-relevant ones with bounded fields and rate-limited logging.

## Creating Networked Entities

- Networked vs local is a creation-time decision: networked = shared gameplay state (pickups, loot, storage, placed world objects, blockers, owned persistent objects); local = cosmetic/preview/attached/render-only (`skills/common/resource-structure.md` -> Local Vs Networked Props).
- Spawn shared gameplay entities from the server (`CreateObject`/`CreateVehicle`/`CreatePed` RPC natives, `CreateVehicleServerSetter` on FiveM only) so the server decides what spawns and registers the handle. Ownership stays client-side: RPC creation runs on the nearest client, which becomes the initial owner, and migrates with scope. Set the bucket with `SetEntityRoutingBucket(entity, bucket)` once `DoesEntityExist(entity)` is true.
- Client-created networked entities keep the creating client as initial owner (`NetworkGetFirstEntityOwner`); no server native can take or assign ownership. For server control, reject in `entityCreating` and spawn a server-side replacement, or gate every outcome through the server registry.
- Client-side creation preloads the model (`RequestModel` + `HasModelLoaded`) and releases it (`SetModelAsNoLongerNeeded`); server-side creation takes the hash directly, no loading (`skills/common/native-rules.md` -> Performance).
- Delete every networked entity on state end, player drop and resource stop; guard deletes with `DoesEntityExist`.

## Debugging

- Before trusting a `0`/`nil`, confirm the entity exists on the side you read it from.
- A client cannot see what another sees: check routing bucket and scope first.
- Ownership-dependent bugs: log `NetworkGetEntityOwner` at the moment of use, not once at creation.
- Missing broadcast: check routing bucket and clients that left scope.
- General flow: `skills/common/debugging.md`.

## Review Questions

- Does the server decide buckets, broadcasts, creation and ownership outcomes (use, claim, delete), or is a client claim (including the current owner) trusted?
- Are client handles and net IDs validated (type, existence, model, owner, bucket, distance) before use?
- Are players and their entities moved into the same bucket, and reset on instance end?
- Is any `TriggerClientEvent(name, -1)` justified, or should it be scoped/targeted?
- Are built-in client events (`weaponDamageEvent` and friends) treated as untrusted input?
- Are networked entities server-created, registered and cleaned up?
