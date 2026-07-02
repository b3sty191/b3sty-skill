# Multi-Resource Rules

Use this file when a RedM/FiveM feature crosses resource boundaries through exports, events, callbacks, dependencies, shared libraries, state bags, convars, or framework integration.

## Defaults

- Prefer explicit dependencies and narrow interfaces.
- Keep resource boundaries obvious while reading code.
- Validate data at every public/shared boundary, even when the caller is another local resource.
- Do not create generic dispatchers that call arbitrary exports, functions, event names, config keys, or methods from a caller-provided string.
- Avoid circular dependencies; move shared data into a small shared resource only when there is real reuse.

## Choosing The Interface

- Use a local function when the caller is inside the same file/resource.
- Use an export for explicit request/response calls from another resource.
- Use a server event only when a fire-and-forget notification is appropriate.
- Use a callback when the caller needs a response and the project already has a callback system.
- Use state bags for replicated visible state, not for hidden authority or secrets.
- Use convars for operator/server configuration, not for per-player gameplay state.
- Use shared scripts for constants/helpers that are safe on both client and server.

## Exports

- Keep export names small and specific.
- Validate every export argument, especially `source`, item names, amounts, coords, entity/net IDs, job/group names, and permission flags.
- Public exports that mutate player state must check that the source is a real player and is allowed to perform the action.
- Return explicit success/failure values instead of relying on side effects or thrown errors.
- Do not expose internal tables directly; return copies or narrow values when callers should not mutate state.
- Do not let an export bypass validation used by the matching server event/callback.
- Add LuaDoc annotations when export parameter meaning is not obvious.

## Events Across Resources

- Use resource-prefixed event names with side markers:
  - `provider_resource:server:action`
  - `provider_resource:client:action`
- Use `RegisterNetEvent` only when the event must be callable across network context.
- Use non-networked local events or direct exports for same-side server-to-server communication when possible.
- Check `GetInvokingResource()` when an event is intended only for another server resource, but do not treat it as the only security control for client-callable net events.
- Reject unknown caller resources for internal server-resource events when the allowed caller set is known.
- Keep event payloads explicit and bounded.

## Dependencies And Load Order

- Declare required resources in `fxmanifest.lua` with `dependency` or `dependencies`.
- Do not assume another resource has started unless it is declared or checked.
- Use `GetResourceState(resourceName)` before optional integration calls.
- Fail loudly at startup when a required dependency is missing.
- Degrade cleanly when an optional dependency is missing.
- Avoid `Wait(...)` startup races as a substitute for dependencies or resource state checks.
- Keep manifest paths and dependency names exact; resource folder names are the runtime names.

## Optional Integrations

- Isolate optional framework/dependency code in one small section or file.
- Check dependency state before registering integration-specific exports, targets, zones, or menus.
- Keep the default resource path framework-free when the project does not require a framework.
- Do not let optional integration code change the core event contract unexpectedly.
- Provide clear no-op or error behavior when a dependency is not available.

## Shared Libraries And Config

- Put shared constants/helpers in a shared script only if both sides need them and the data is safe for clients.
- Keep server-only prices, rewards, drop rates, permission gates, secrets, SQL details, and webhook data out of shared config.
- Use split config files for large datasets and require only what each script needs.
- Avoid one shared utility resource becoming a hidden framework for unrelated resources.
- Version shared exports or provide compatibility shims when multiple resources depend on them.

## State Bags

- Let the server write important replicated player/entity state.
- Let clients read state bags and render local visuals from state.
- With strict state bag mode enabled, client replicated writes will not be valid; route changes through validated server events/callbacks.
- Keep state bag payloads small and stable.
- Do not store secrets or server-only economy rules in state bags.
- Clean state bag keys when resource-owned state ends.

## Versioning And Compatibility

- Add a simple version export or convar only when dependent resources need to check behavior.
- Keep interface changes backward-compatible when possible.
- When breaking an export/event contract, update every in-repo caller in the same change.
- Avoid accepting multiple legacy payload shapes forever; migrate callers and remove old paths when practical.
- Document required dependency versions when a feature relies on a specific API.

## Failure Handling

- Handle missing resources, stopped dependencies, nil exports, callback timeouts, and malformed responses.
- Do not crash a hot gameplay path because an optional dependency is absent.
- Log boundary failures with caller, provider, interface name, and bounded payload metadata.
- Rate-limit boundary failure logs when a missing dependency can trigger repeated calls.
- Keep fallback behavior explicit: reject action, no-op, use default data, or queue retry.

## Review Questions

- Is this interface narrow enough for another resource to call safely?
- Is the dependency required, optional, or accidental?
- Is load order declared instead of guessed with waits?
- Can a malicious client reach this server event through a shared event name?
- Are exports validating as strictly as server events?
- Does optional integration fail cleanly when the dependency is stopped?
- Are shared configs free of secrets and server-only authority?
