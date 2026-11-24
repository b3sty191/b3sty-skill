# Security And Performance Review Questions

Run this checklist over a feature, resource, or diff. Each question maps to a rule in `skills/common/security-performance.md` -> Contents and the files it indexes.

## Review Questions

- What can a malicious client fake in this feature?
- Which server-side checks reject fake values?
- Is this network event actually meant to be public, or should it be a local function (`AddEventHandler`)?
- Does the handler reject a non-numeric/empty `source` (server-originated) or `source <= 0` when only a real client may trigger it?
- Does the recipient of any value come from `source`, never from a payload field?
- Do commands, exports, callbacks, and NUI callbacks validate the same things as server events?
- Is every value resolved from server-held state (catalog, balance, permissions), not the payload?
- Does this give-value event pass the give-value checklist (identity, catalog, bounded quantity, fresh afford check, atomic debit+grant, idempotency, ACE-gated admin path)?
- Are admin/sensitive actions gated by `IsPlayerAceAllowed`, not by a client-side flag or a client-reported job/identifier?
- Does this event need a throttle or cooldown? Could an unthrottled handler be a DoS or dupe vector?
- Does this valuable action need a request ID, in-flight flag, transaction, or duplicate-claim check?
- Does this callback/event clean up pending state on disconnect?
- Are client-provided coords, entity IDs, net IDs, jobs, permissions, and ownership claims verified server-side?
- Is entity ownership rechecked against a server registry (ownership migrates)?
- Are built-in client events (`weaponDamageEvent`, `explosionEvent`, and friends) intercepted/validated, and are the networked-event convars set where abuse matters?
- Is any broadcast `TriggerClientEvent(name, -1)` justified, or should it be scoped/targeted?
- Is every SQL query parameterized (`?`/`@name`)? Any client value concatenated into SQL or an identifier?
- Are client strings and tables bounded (length, key count, depth) before they are decoded, iterated, stored, or logged?
- Does any `SetHttpHandler` endpoint exist, and does it authenticate, bound, and rate-limit like a public event?
- Do valuable mutations write an audit trail that could reconstruct a dupe after the fact?
- Are the platform hardening convars set (`sv_scriptHookAllowed 0`, `sv_pureLevel`, `sv_requestParanoia`, rcon off), is the FXServer artifact recent, and are third-party resources vetted before install?
- Are secrets in server-only `set` convars (never `setr`/`sets`/shared/client)?
- Does identity come from `GetPlayerIdentifiers(source)` on the server, and are bans/whitelist checked in `playerConnecting` deferrals?
- Are prices, rewards, drop rates, and permission gates kept out of shared/client config or revalidated server-side?
- Can another resource call this interface with bad input?
- Is any secret or webhook visible to the client?
- Is this loop always necessary, or can it be event-driven?
- Is any hot path scanning a large table repeatedly?
- Can this data be indexed once and read O(1)?
- Are database writes debounced and dirty-tracked?
- Are log payloads bounded and redacted?
