# Security And Performance Review Questions

Run this checklist over a feature, resource, or diff. Each question maps to a rule in `skills/common/security-performance.md` -> Contents and the files it indexes.

## Review Questions

- What can a malicious client fake here, and what rejects it server-side?
- Public net event, or should it be a local function (`AddEventHandler`)?
- Non-numeric/empty `source` (server-originated) and `source <= 0` rejected where only a real client may trigger?
- Recipient of any value taken from `source`, never from a payload field?
- Commands, exports, callbacks, NUI callbacks validated like server events?
- Every value resolved from server-held state (catalog, balance, permissions) - no client-sent price, reward, or count?
- Give-value handler passes the checklist (identity, catalog, bounded quantity, fresh afford check, atomic debit+grant, idempotency, ACE-gated admin path)?
- Admin/sensitive actions gated by `IsPlayerAceAllowed`, not by a client-side flag or a client-reported job/identifier?
- Throttle or cooldown present - could an unthrottled handler be a DoS or dupe vector?
- Request ID, in-flight flag, transaction, or duplicate-claim check on valuable actions?
- `source` re-validated after every yield (`.await`, `Wait`), pending state cleaned up on disconnect?
- Client coords, entity IDs, net IDs, jobs, permissions, ownership claims verified server-side; ownership rechecked against a server registry (it migrates)?
- RedM: any gate on a server-side `GetEntityHealth` read (it can return `0` for live entities - `skills/redm/rules.md`)?
- Built-in client events (`weaponDamageEvent`, `explosionEvent`, and friends) intercepted/validated, networked-event convars set where abuse matters?
- Any broadcast `TriggerClientEvent(name, -1)` justified, or should it be scoped/targeted?
- Every SQL query parameterized (`?`/`@name`)? Any client value concatenated into SQL or an identifier?
- Client strings and tables bounded (length, key count, depth) before decode, iteration, storage, or logging?
- `SetHttpHandler` endpoints authenticating, bounding, and rate-limiting like a public event?
- Audit trail on valuable mutations, enough to reconstruct a dupe after the fact?
- Hardening convars set (`sv_scriptHookAllowed 0`, `sv_pureLevel`, `sv_requestParanoia`, rcon off), FXServer artifact recent, third-party resources vetted?
- Secrets only in server-only `set` convars (never `setr`/`sets`/shared/client), nothing secret reachable by a client?
- Identity from `GetPlayerIdentifiers(source)` on the server, bans/whitelist checked in `playerConnecting` deferrals?
- Prices, rewards, drop rates, permission gates kept out of shared/client config or revalidated server-side?
- Can another resource call this interface with bad input?
- Is this loop necessary, or can it be event-driven - does any `Wait(0)` need to run every frame?
- Hot path scanning a large table that could be indexed once and read O(1)?
- Database writes debounced and dirty-tracked?
- Log payloads bounded and redacted?
