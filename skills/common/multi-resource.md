# Multi-Resource Rules

Use when a RedM/FiveM feature crosses resource boundaries: exports, events, callbacks, dependencies, shared libraries, state bags, convars, framework integration.

## Defaults

- Explicit dependencies, narrow interfaces, obvious boundaries; validate at every public/shared boundary, even from a local caller.
- No dispatcher calling arbitrary exports/functions/event names/config keys/methods from a caller-provided string.
- No circular dependencies; a shared resource only for real reuse.

## Choosing The Interface

- Local function: same file/resource. Export: request/response from another resource. Server event: fire-and-forget notification. Callback: caller needs a response and a callback system exists.
- State bags: replicated visible state, never hidden authority or secrets. Convars: operator/server config, not per-player gameplay state. Shared scripts: constants/helpers safe on both sides.

## Exports

- Small specific names; LuaDoc when a parameter's meaning is unclear; return copies or narrow values, never internal tables callers could mutate.
- Validate every argument (`source`, item names, amounts, coords, entity/net IDs, job/group names, permission flags) as strictly as the matching server event/callback; exports mutating player state also check the source is a real player allowed to act.
- Return explicit success/failure, not side effects or thrown errors. Never `return nil, reason`: returns unpack with `table.unpack`, so a `nil` first value drops the rest (`skills/common/runtime.md` -> Exports And Stale References).

## Events Across Resources

- Resource-prefixed names with side markers: `provider_resource:server:action`, `provider_resource:client:action`; payloads explicit and bounded.
- `RegisterNetEvent` only when the event must cross network context; same-side server-to-server traffic uses non-networked local events or direct exports.
- `GetInvokingResource()` for events meant only for another server resource, rejecting unknown callers where the allowed set is known - not the only control for client-callable net events.

## Dependencies And Load Order

- Declare required resources in `fxmanifest.lua` (`dependency`/`dependencies`); never assume one started unless it is declared or checked with `GetResourceState(resourceName)` before optional integration calls, and never race startup with `Wait(...)`.
- Missing required dependency: fail loudly at startup. Missing optional one: degrade cleanly.
- Manifest paths and dependency names exact - resource folder names are the runtime names.

## Optional Integrations

- Isolate optional framework/dependency code in one small section or file; check dependency state before registering integration exports, targets, zones or menus.
- The default path stays framework-free unless the project requires a framework; integration never changes the core event contract, and no-ops or errors clearly when its dependency is unavailable.

## Shared Libraries And Config

- Shared scripts: constants/helpers both sides need, client-safe only; server-only prices, rewards, drop rates, permission gates, secrets, SQL details and webhook data stay out.
- Large datasets split into config files, required only where needed; no shared utility becoming a hidden framework for unrelated resources.
- Version shared exports, or ship compatibility shims, when several resources depend on them.

## State Bags

- The server writes important replicated player/entity state; clients read it and render local visuals. Strict state bag mode invalidates client replicated writes - route changes through validated server events/callbacks.
- Payloads small and stable, no secrets or server-only economy rules, keys cleaned when resource-owned state ends.

## Versioning And Compatibility

- A version export or convar only when dependents must check behavior; document required dependency versions when a feature relies on a specific API.
- Keep changes backward-compatible where possible; a breaking export/event contract updates every in-repo caller in the same change, and legacy payload shapes get migrated off, not kept forever.

## Failure Handling

- Handle missing resources, stopped dependencies, nil exports, callback timeouts, malformed responses; never crash a hot gameplay path for an absent optional dependency.
- Log boundary failures with caller, provider, interface name, bounded payload metadata; rate-limit when a missing dependency triggers repeated calls.
- Explicit fallback: reject action, no-op, default data, or queued retry.

## Review Questions

- Is this interface narrow enough for another resource to call safely?
- Is the dependency required, optional or accidental - and load order declared, not guessed with waits?
- Can a malicious client reach this server event through a shared event name?
- Are exports validating as strictly as server events?
- Does optional integration fail cleanly when the dependency is stopped?
- Are shared configs free of secrets and server-only authority?
