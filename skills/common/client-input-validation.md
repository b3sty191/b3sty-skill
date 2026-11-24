# Client-Reported Input Validation

Server-side validation of what the client reports: state bags and custom sync, NUI callback payloads, entity handles and net IDs, built-in game events, and coordinates. Core event-security rules and the index of every section named "above"/"below": `skills/common/security-performance.md` -> Contents.

## Sync Safety

- State bags are fine for visual state; important state must be changed server-side. Client-side non-replicated entity state is local client state, never authoritative replicated state.
- Prefer `setr sv_stateBagStrictMode true` when the target artifact supports it: only the server may then modify networked entity and player state bags, so clients request changes through validated server events/callbacks. Audit dependencies first - resources that set replicated state from the client must move server-side. Clients may still read state bags and react with `AddStateBagChangeHandler`.
- For custom sync events, use sequence numbers to reject old packets.
- Where spoofing matters for client-side local sync, add a per-player sync secret/signature and reject invalid ones - but client-held secrets are tamper resistance only. The server must never trust a client action just because it carries a client-visible secret/signature.
- Keep sync payloads small (never full player data when one field changed), and never send secrets, tokens, webhooks, or private config to clients.

## NUI Callback Hardening

- A `RegisterNUICallback` handler receives fully untrusted input: the browser can be devtooled or scripted, so a NUI callback is exactly as hostile as any client `:server:` event. Validate the schema (type, range, existence) before the payload drives behavior or reaches the server, and treat it like the naive handler in Event Trust Boundary - same field validation, same bounds, same throttle. Bridge mechanics, and the XSS sinks (`innerHTML`, `{@html}`, `v-html`) that player-controlled strings must never reach, are in `skills/common/nui.md`.
- Never round-trip authority through NUI. The UI must not decide money, items, permissions, or access - it only requests them; forward valuable actions to a validated `:server:` event.
- Never grant money/items/permissions from a NUI response: `cb({ success = true })` is a display signal, not a grant. Grants happen server-side (see Give-Value Event Hardening), and the recipient is still `source` - a NUI payload must not pick a target player.

## Entity And Net ID Validation

- Client-provided entity handles, net IDs, vehicle/object/ped IDs are untrusted: confirm the entity exists, then validate type, model, owner, routing bucket, health/alive state, and distance wherever those matter to the action.
- Check against a server-owned spawned-entity registry or server-side state instead of accepting arbitrary world entities. Never trust a client claim that an entity is theirs, nearby, empty, damaged, or reward-eligible; for destructive or valuable actions reject entities that are not server-created, not in the expected registry, or not owned/controlled by the expected player.
- Entity ownership migrates between clients; a recovered owner (`NetworkGetEntityOwner`) is momentary, not permanent. Spawn requests, loot/pickup claims, and ownership migration are attack surfaces - validate against a server-side registry before trusting entity state. See `skills/common/networking.md` -> Entity Ownership and Creating Networked Entities.

## Built-in Client Events

The game/OneSync routes client->server events that attackers use as free exploit surfaces. Treat every one as attacker-callable with attacker-chosen fields. ([server-events](https://docs.fivem.net/docs/scripting-reference/events/server-events/), [Secure your events](https://docs.fivem.net/docs/developers/server-security/))

- Documented core events: `weaponDamageEvent(sender, data)`, `startProjectileEvent(sender, data)`, `ptFxEvent(sender, data)`, `removeAllWeaponsEvent(sender, data)` (fields in the [server-events reference](https://docs.fivem.net/docs/scripting-reference/events/server-events/)). `data.weaponType` on `weaponDamageEvent` is an unsigned 32-bit hash while `GetHashKey`/backticks return signed values (citizenfx/fivem#3827: 2982836145 vs -1312131151 for `weapon_rpg`), so normalize before comparing: `local h = data.weaponType; if h > 0x7FFFFFFF then h = h - 0x100000000 end`. It is still client-reported - check it against server-side weapon/entity state.
- `explosionEvent` is interceptable server-side with OneSync: `AddEventHandler('explosionEvent', function(sender, ev) ...)`, inspect `ev` (`explosionType`, `posX/Y/Z`, `damageScale`, `ownerNetId`, ...), and `CancelEvent()` to stop the server routing the explosion to other clients - the documented mitigation. ([cookbook](https://docs.fivem.net/docs/cookbook/2019/08/19/onesync-intercepting-game-events-such-as-explosions/))
- `CancelEvent()` does not stop other handlers for the same event, and for some game events (e.g. `weaponDamageEvent`, citizenfx/fivem#2395) cancellation does not reliably sync to clients. Never rely on cancel as the only control for damage that may already have applied; validate the outcome server-side.
- `sender` is the reporting player: `sender`-controlled fields (weapon hash, damage amount, target entity, owner net ID) must never grant money, items, kills, or eligibility. It arrives as a string (server net ID), so `tonumber(sender)` before comparing it or keying a table - on `weaponDamageEvent`, `startProjectileEvent`, `ptFxEvent`, `removeAllWeaponsEvent` and `explosionEvent`.
- Prefer the built-in server controls over hand-rolled filters for networked-event abuse: `sv_filterRequestControl` (FiveM only; blocks `REQUEST_CONTROL_EVENT` routing - the main entity-control/explosion-by-proxy vector), `sv_enableNetworkedPhoneExplosions` (off by default), `sv_enableNetworkedSounds`, `sv_enableNetworkedScriptEntityStates`, and `block_net_game_event "EVENT_NAME"` for a specific net game event. ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/))
- Bound and rate-limit per `sender` (particles, projectiles, explosions). Reject, cancel, or log; do not auto-punish a player on a single unverified event.

```lua
-- intercept explosions; rate-limit per sender; cancel routing of bad explosions
local lastExplosion = {}

AddEventHandler("explosionEvent", function(sender, ev)
    local src = tonumber(sender)                     -- string net ID; key by number so playerDropped cleans up
    if not src or src <= 0 then return end
    local now = GetGameTimer()
    if now - (lastExplosion[src] or 0) < 250 then    -- flood: stop relaying
        CancelEvent()
        return
    end
    lastExplosion[src] = now

    if (tonumber(ev.damageScale) or 0) > 1.0 then    -- server rule, not the client's claim
        CancelEvent()
    end
end)

AddEventHandler("playerDropped", function()
    lastExplosion[source] = nil                      -- per-player tables always clean up on drop
end)
```

- Full OneSync context (ownership, routing buckets, `entityCreating`/`CancelEvent` to reject entity creation) is in `skills/common/networking.md` -> Built-in Client Events and Entity Lifecycle Events.

## Position And Interaction Checks

- Client coordinates are hints; never award money, items, progress, or access on them alone.
- For shops, crafting, rewards, gathering, storage, doors, and interactions, compare the player's server-side position against server-side config coordinates with an explicit max-distance check and reject requests outside the radius.
- For delayed interactions, recheck that the player is still valid, alive when required, and near the target before applying the result.
- Reject stale position snapshots and movement exceeding reasonable distance or speed thresholds.
