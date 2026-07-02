# Debugging Rules

Use this file when diagnosing RedM/FiveM resource failures, crashes, bad state, native behavior, events, callbacks, NUI, database writes, load order, or performance issues.

## Defaults

- Reproduce first, then change code.
- Identify the failing side: server, client, NUI/browser, database, dependency, or game native.
- Keep debug edits small and remove or gate noisy logging before finishing.
- Prefer one focused hypothesis at a time over broad rewrites.
- Check `memory/` when a problem looks recurring or native-specific.
- Record new recurring fixes in the correct `memory/` namespace with date and game build.

## First Pass

- Capture the exact action that fails, expected result, actual result, and whether it fails every time.
- Note game target: RedM, FiveM, or shared.
- Note runtime side: server console, client F8 console, NUI devtools, or database.
- Note resource name, current branch/change set, dependency versions when relevant, and artifact/game build when known.
- Read the first useful stack trace line that points into the resource, not only the final symptom.
- Check recent edits before assuming an engine or dependency bug.

## Isolation

- Confirm the resource starts cleanly before debugging gameplay behavior.
- Check `fxmanifest.lua` for missing scripts, wrong side, wrong path, missing `files`, missing `ui_page`, missing `dependency`, or load order mistakes.
- Reduce the repro to one command, one event, one item, one zone, one player, or one database row when possible.
- Disable optional addons only when they are likely involved.
- Do not rewrite structure just to isolate a bug; add temporary guards/logs near the failing boundary.

## Logging

- Use `print` for quick local debugging.
- Use existing project logging helpers when the resource already has them.
- Use `lib.print` only when ox_lib is already a dependency; do not add ox_lib solely for logging.
- Prefix logs with the resource/feature and include the side when useful.
- Log bounded values: source, identifier, event name, key names, counts, entity/net IDs, coords rounded to sane precision.
- Do not log secrets, full tokens, webhooks, large payloads, or full player data blobs.
- Rate-limit logs inside loops, state bag handlers, NUI callbacks, and spam-prone events.

## Client And Server Split

- Store `source` in a local at the top of server event/callback handlers before async work.
- Confirm server events are registered with the expected `resource_name:server:action` name.
- Confirm client events are registered with the expected `resource_name:client:action` name.
- Treat successful client-side checks as UX only; repeat important validation server-side.
- When state differs between client and server, identify which side is authoritative before fixing.
- For state bags, confirm whether strict state bag mode is enabled and which side writes replicated state.

## Native And Entity Bugs

- Check `skills/common/native-rules.md` before changing native-heavy code.
- Check the matching native reference only when verifying name, hash, namespace, signature, or game-specific behavior.
- Check `memory/common/native-bugs.md`, `memory/fivem/native-bugs.md`, or `memory/redm/native-bugs.md` for known behavior.
- Guard entity handles with existence checks before reads, writes, deletes, and attachments.
- Log entity handle, net ID, model, owner, coords, routing bucket, and existence only when those values matter.
- Reproduce native issues on the correct game because RedM and FiveM behavior can differ.

## Events, Callbacks, And Exports

- Verify whether the failing call is a net event, local event, framework callback, ox_lib callback, NUI callback, or export.
- Use `RegisterNetEvent` only for handlers that must be callable across network context.
- Validate payload type and bounds before doing work in public events/callbacks/exports.
- Check throttles and cooldowns when an action silently does nothing.
- Check pending callback cleanup when failures happen after player drop, retry, or resource restart.
- For inter-resource calls, confirm dependency order and whether the provider resource is started.

## Database Debugging

- Open `skills/common/database.md` when SQL, persistence, migrations, or saved state is involved.
- Verify the connection string, `oxmysql` startup order, and manifest import before debugging query logic.
- Log the query purpose and parameters as bounded metadata, not raw SQL with player data.
- Use OxMySQL debug/slow-query tools temporarily, scoped to the resource when possible.
- Check nil rows, zero affected rows, transaction failure, duplicate key errors, and JSON decode errors separately.

## NUI Debugging

- Confirm `ui_page` and every HTML/CSS/JS/font/image file are listed in `fxmanifest.lua`.
- Confirm Lua sends the message shape the browser expects.
- Confirm browser callbacks call the Lua callback exactly once.
- Clear NUI focus on close, player drop, and resource stop.
- Treat NUI callback payloads as untrusted input even though they originate from the resource UI.
- Use browser devtools for JS errors instead of guessing from Lua logs.

## Performance Debugging

- Find the hot path before optimizing.
- Look for `Wait(0)` loops, repeated natives, table scans, repeated config requires, N+1 SQL, and spammy NUI messages.
- Increase waits based on distance/active state before adding complex caches.
- Cache only values that are expensive or hot enough to justify ownership and cleanup.
- Check `skills/common/security-performance.md` before performance changes in events, callbacks, sync, DB writes, or loops.

## Finishing A Fix

- Remove temporary logs or guard them behind a config/convar debug flag.
- Keep useful diagnostics that would help future operators but avoid console spam.
- Add a focused regression test or manual verification step when the project has no test harness.
- Update `memory/` only for recurring facts learned from real debugging, not for one-off implementation details.
- Mention remaining risk when the fix depends on timing, dependency version, game build, or unverified native behavior.
