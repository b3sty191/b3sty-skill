# Client-Reported Input Validation

Server-side validation of what the client reports: state bags and custom sync, NUI callback payloads, entity handles and net IDs, built-in game events, and coordinates. The core event-security rules, and the index of every section a rule below names as "above" or "below", are in `skills/common/security-performance.md` -> Contents.

## Sync Safety

- State bags are fine for visual state, but important state must be changed server-side.
- Prefer enabling `setr sv_stateBagStrictMode true` in server config when the target artifact supports it.
- With strict state bag mode enabled, only the server can modify networked entity and player state bags; clients should request changes through validated server events/callbacks.
- Client-side non-replicated entity state is still local client state and must not be used as authoritative replicated state.
- Clients may still read state bags and react with `AddStateBagChangeHandler`.
- Audit dependencies before enabling strict mode because resources that set replicated state from the client must be moved server-side.
- For custom sync events, prefer sequence numbers to reject old packets.
- When spoofing would matter for client-side local sync, add a per-player sync secret/signature and reject messages with invalid signatures.
- Treat client-held sync secrets as tamper resistance only, not real server-side security.
- The server must never trust a client action just because it includes a client-visible secret/signature.
- Keep sync payloads small; do not send full player data when only one field changed.
- Do not send secrets, tokens, webhooks, or private config to clients.

## NUI Callback Hardening

- A `RegisterNUICallback` handler receives fully untrusted input. The browser can be devtooled or scripted, so a NUI callback is exactly as hostile as any client `:server:` event. Validate the schema (type, range, existence) before the payload drives behavior or is forwarded to the server. Full bridge mechanics in `skills/common/nui.md`.
- Never round-trip authority through NUI. The UI must not be the thing that decides money, items, permissions, or access - it only requests them. Forward valuable actions to a validated `:server:` event and let the server decide.
- Never grant money/items/permissions directly from a NUI response. A `cb({ success = true })` is a display signal, not a grant. Grants happen server-side (see Give-Value Event Hardening).
- The recipient of any value is still `source`; do not let a NUI payload pick a target player.
- Treat a NUI callback like the naive handler in Event Trust Boundary: same field validation, same bounds, same throttle.

## Entity And Net ID Validation

- Treat client-provided entity handles, net IDs, vehicle IDs, object IDs, and ped IDs as untrusted.
- Validate that the entity exists before using it.
- Validate entity type, model, owner, routing bucket, health/alive state, and distance when those fields matter to the action.
- Prefer checking against a server-owned spawned entity registry or server-side state instead of accepting arbitrary world entities.
- Do not trust a client claim that an entity belongs to them, is nearby, is empty, is damaged, or is eligible for a reward.
- For destructive or valuable actions, reject entities that are not server-created, not in the expected registry, or not owned/controlled by the expected player.
- Entity ownership migrates between clients; treat a recovered owner (`NetworkGetEntityOwner`) as momentary, not permanent. Spawn requests, loot/pickup claims, and ownership migration are attack surfaces - validate against a server-side registry before trusting entity state. See `skills/common/networking.md` -> Entity Ownership and Creating Networked Entities.

## Built-in Client Events

The game/OneSync routes client->server events that attackers use as free exploit surfaces. Treat every one as attacker-callable with attacker-chosen fields. ([server-events](https://docs.fivem.net/docs/scripting-reference/events/server-events/), [Secure your events](https://docs.fivem.net/docs/developers/server-security/))

- Documented core events: `weaponDamageEvent(sender, data)`, `startProjectileEvent(sender, data)`, `ptFxEvent(sender, data)`, `removeAllWeaponsEvent(sender, data)` (full fields in the [server-events reference](https://docs.fivem.net/docs/scripting-reference/events/server-events/)). `data.weaponType` on `weaponDamageEvent` is an unsigned 32-bit hash, while `GetHashKey`/backticks return signed values (citizenfx/fivem#3827: 2982836145 vs -1312131151 for `weapon_rpg`). Normalize before comparing: `local h = data.weaponType; if h > 0x7FFFFFFF then h = h - 0x100000000 end`. It is still client-reported, so check it against server-side weapon/entity state.
- `explosionEvent` is interceptable server-side with OneSync: register `AddEventHandler('explosionEvent', function(sender, ev) ...)` and inspect `ev` (`explosionType`, `posX/Y/Z`, `damageScale`, `ownerNetId`, ...). `CancelEvent()` here stops the server from routing the explosion to other clients - the documented mitigation. ([cookbook](https://docs.fivem.net/docs/cookbook/2019/08/19/onesync-intercepting-game-events-such-as-explosions/))
- `CancelEvent()` does not stop other handlers for the same event, and for some game events (e.g. `weaponDamageEvent`, see citizenfx/fivem#2395) cancellation does not reliably sync to clients. Do not rely on cancel as your only control for damage that may already have applied; validate the outcome server-side.
- `sender` is the reporting player. Never let `sender`-controlled fields (weapon hash, damage amount, target entity, owner net ID) grant money, items, kills, or eligibility.
- `sender` arrives as a string (server net ID); call `tonumber(sender)` before comparing it or using it as a table key. This applies to `weaponDamageEvent`, `startProjectileEvent`, `ptFxEvent`, `removeAllWeaponsEvent` and `explosionEvent`.
- Prefer the built-in server controls over hand-rolled filters for networked-event abuse: `sv_filterRequestControl` (FiveM only; blocks `REQUEST_CONTROL_EVENT` routing - the main entity-control/explosion-by-proxy vector), `sv_enableNetworkedPhoneExplosions` (off by default), `sv_enableNetworkedSounds`, `sv_enableNetworkedScriptEntityStates`, and `block_net_game_event "EVENT_NAME"` for a specific net game event. ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/))
- Bound and rate-limit per `sender` (particles, projectiles, explosions). Reject, cancel, or log; do not auto-punish a player on a single unverified event.

```lua
-- intercept explosions; rate-limit per sender; cancel routing of bad explosions
local lastExplosion = {}

AddEventHandler("explosionEvent", function(sender, ev)
    local src = tonumber(sender)                          -- sender is a string; key by number so playerDropped can clean up
    if not src or src <= 0 then return end
    local now = GetGameTimer()
    if now - (lastExplosion[src] or 0) < 250 then        -- flood: stop relaying
        CancelEvent()
        return
    end
    lastExplosion[src] = now

    if (tonumber(ev.damageScale) or 0) > 1.0 then         -- server rule, not the client's claim
        CancelEvent()
    end
end)

AddEventHandler("playerDropped", function()
    lastExplosion[source] = nil                           -- per-player tables always clean up on drop
end)
```

- Full OneSync context (ownership, routing buckets, `entityCreating`/`CancelEvent` to reject entity creation) is in `skills/common/networking.md` -> Built-in Client Events and Entity Lifecycle Events.

## Position And Interaction Checks

- Treat client coordinates as hints; never use them alone to award money, items, progress, or access.
- For shops, crafting, rewards, gathering, storage, doors, and interactions, compare the player's server-side position to server-side config coordinates.
- Use explicit max-distance checks and reject requests outside the allowed radius.
- For delayed interactions, check that the player is still valid, alive when required, and near the target before applying the result.
- When accepting position snapshots, reject stale snapshots and movement that exceeds reasonable distance or speed thresholds.

