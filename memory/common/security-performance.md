# Security And Performance Memory

What worked in practice on b3sty RedM/FiveM resources - confirmations, not the rule text. Full rules: `skills/common/security-performance.md`.

## Learned Patterns

Proven repeatedly in real b3sty resources:

- Reverse indexes for config lists make runtime lookups O(1).
- Rate-limiting callback requests per player and per callback name stops abuse.
- `pendingByTarget[source][id]` makes callback cleanup O(1) on player drop.
- Verifying that client callback responses come from the originally targeted player prevents spoofed replies.
- Per-key server throttles for state update requests plus action throttles for item use cover the common spam surface.
- Optimistic client state works only when paired with a rejection/rollback path.
- Sequence numbers and signatures help reject old/spoofed client sync packets, but client-held secrets are tamper resistance only - never real security.
- `setr sv_stateBagStrictMode true` keeps replicated player/entity state bag writes server-side and forces clients to request changes through validated server paths; local-only entity state stays local and is not gameplay authority.
- Dirty-tracking player data and debouncing database saves cuts write load; keep raw encoded JSON for unchanged fields to skip re-encoding large data every save.
- Batching/capping logs and redacting secret-looking fields before logging keeps logs safe.

## Keep It Simple

- No framework structure when a smaller direct b3sty-style resource is enough.
- Do not eager-load config modules a runtime does not need.
- Keep the security/performance ideas; keep the code shape simple and readable.

## Quick-Reference Checklists

Condensed reminders; full rules and examples in `skills/common/security-performance.md`.

### Security
- Server owns important state.
- Every `:server:` event validates payload type and bounds.
- Internal server logic stays local unless it must be network-callable.
- Every public command, callback, export, and NUI callback validates input.
- Spam-prone events have server-side throttles.
- Valuable actions have duplicate/replay protection, not just cooldowns.
- Rewards, money, items, jobs, permissions, and ownership are checked server-side.
- Replicated state bag writes are server-side; clients only request changes and render from state.
- Client-provided coords, entity IDs, and net IDs are validated against server state or ignored.
- Shared/client config is public; secrets and authoritative economy logic stay server-side.
- Public inter-resource interfaces validate bad input at the boundary.
- Secrets are server-only; logs redact and cap.

### Performance
- Cache/index only hot paths or expensive repeated work; every cache has an owner and a cleanup path.
- No unnecessary `Wait(0)`; idle loops sleep long.
- Hot loops cache natives and table lookups.
- Large config lists have index maps; repeated `for` searches become direct lookups.
- Large config modules are required only where used.
- Database writes are debounced or dirty-tracked.
- State/sync payloads are small.
- Player/resource-scoped caches are cleared on disconnect or resource stop.

### Cleanup
- Entities, objects, peds, and vehicles are deleted or released.
- Blips, zones, NUI focus, timers, callback pending tables, throttle/cooldown/cache tables are cleared.
- State bag/local state is reset when needed.
- Resource-stop cleanup checks `resourceName == GetCurrentResourceName()`.
