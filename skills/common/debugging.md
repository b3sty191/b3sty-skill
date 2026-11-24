# Debugging Rules

Use when diagnosing RedM/FiveM resource failures, crashes, bad state, native behavior, events, callbacks, NUI, database writes, load order or performance.

## Defaults

- Reproduce first, then change code; one hypothesis at a time, never a broad rewrite.
- Identify the failing side: server, client, NUI/browser, database, dependency, game native.
- Keep debug edits small; remove or gate noisy logging before finishing.
- Check `memory/` for recurring or native-specific problems, and record new recurring fixes in the right `memory/` namespace with date and game build.

## First Pass

- Capture the failing action, expected vs actual result, and whether it fails every time.
- Note the game (RedM, FiveM, shared) and the side: server console, client F8 console, NUI devtools, database.
- Note resource name, branch/change set, dependency versions, artifact/game build.
- Read the first stack trace line that points into the resource, not only the final symptom.
- Check recent edits before blaming the engine or a dependency.

## Isolation

- Confirm the resource starts cleanly before debugging gameplay behavior.
- Check `fxmanifest.lua`: missing scripts, wrong side or path, missing `files`/`ui_page`/`dependency`, load order.
- Reduce the repro to one command, event, item, zone, player or database row.
- Disable optional addons only when they are likely involved.
- Do not restructure to isolate a bug: add temporary guards/logs at the failing boundary.

## Logging

- `print` for quick local debugging, project logging helpers where they exist, `lib.print` only when ox_lib is already a dependency - never add ox_lib for logging.
- Prefix logs with resource/feature, plus the side when useful.
- Log bounded values: source, identifier, event name, key names, counts, entity/net IDs, coords at sane precision. Never secrets, full tokens, webhooks, large payloads or player data blobs.
- Rate-limit logs inside loops, state bag handlers, NUI callbacks and spam-prone events.

## Client And Server Split

- Store `source` in a local at the top of server event/callback handlers before async work.
- Confirm the registered names match `resource_name:server:action` / `resource_name:client:action`.
- Client-side checks are UX only; repeat important validation server-side.
- When client and server state differ, settle which side is authoritative before fixing.
- For state bags, check whether strict state bag mode is on and which side writes replicated state.

## Native And Entity Bugs

- Read `skills/common/native-rules.md` before changing native-heavy code, and `skills/common/native-usage.md` when a native compiles but misbehaves - wrong float subtype, BOOL `0` treated as truthy, missing `Citizen.ResultAs*`, wrong struct layout or a build/apiset mismatch.
- Use the native reference to verify name, hash, namespace, signature or game-specific behavior, and `memory/common/native-bugs.md`, `memory/fivem/native-bugs.md`, `memory/redm/native-bugs.md` for known behavior.
- Guard entity handles with existence checks before reads, writes, deletes, attachments.
- Log entity handle, net ID, model, owner, coords, routing bucket, existence only when those values matter.
- Reproduce on the correct game: RedM and FiveM native behavior differs.

## Events, Callbacks, And Exports

- Verify what the failing call is: net event, local event, framework callback, ox_lib callback, NUI callback or export.
- `RegisterNetEvent` only for handlers that must be callable across network context.
- Validate payload type and bounds before doing work in public events/callbacks/exports.
- Check throttles and cooldowns when an action silently does nothing.
- Check pending callback cleanup when failures follow a player drop, retry or resource restart.
- For inter-resource calls, confirm dependency order and that the provider is started.

## Database Debugging

- Open `skills/common/database.md` when SQL, persistence, migrations or saved state is involved.
- Verify the connection string, `oxmysql` startup order and manifest import before debugging query logic.
- Log query purpose and parameters as bounded metadata, not raw SQL with player data.
- Use OxMySQL debug/slow-query tools temporarily, scoped to the resource.
- Check nil rows, zero affected rows, transaction failure, duplicate key errors and JSON decode errors separately.

## NUI Debugging

- Confirm `ui_page` and every HTML/CSS/JS/font/image file are listed in `fxmanifest.lua`, and that Lua sends the message shape the browser expects.
- Confirm every Lua `RegisterNUICallback` handler calls its `cb` exactly once on every path, early-return validation failures included: a missing `cb` makes the browser `fetch` time out and reject with an error (`skills/common/nui.md` -> Browser To Lua).
- Clear NUI focus on close, player drop and resource stop.
- NUI callback payloads are untrusted even though they come from the resource UI.
- Use browser devtools for JS errors instead of guessing from Lua logs.

## Performance Debugging

- Find the hot path before optimizing - measure, do not guess:
  - `resmon 1` in the client F8 console shows per-resource frame time (ms) and memory; a resource idling above ~0.10ms or spiking on interaction is the place to look (a community rule of thumb, not an engine limit - compare against the same server's baseline, idle and during the action). Server-side `resmon` exists only in the Windows FXServer GUI; on Linux use the server profiler.
  - `profiler record 500` then `profiler view` (client F8 or server console) captures a tick-level trace of every resource; `profiler saveJSON <file>` exports it for `chrome://tracing` / Perfetto when the in-game view is not enough.
  - `netEventLog 1` (client F8) lists recent net events with direction (`C->S` / `S->C`), name and payload bytes; state bags are not listed. `netgraph` shows live packets/bytes, `net_statsFile <file>` logs net stats, and `cl_drawPerf 1` overlays FPS/ping/loss.
  - `set onesync_logFile <path>` writes a OneSync sync log - per-client packet rates and which entity owners send most. It grows fast, so enable it for a 1-30 s capture and turn it off again (verified: `ServerGameState.cpp`, FXServer 35945).
  - Client `resmon`, `netEventLog` and `profiler` are developer commands: on the production channel they print "Access denied" until the game is launched with `+set moo 31337`. `cl_drawPerf` works without it.
  - Match the tool to the hitch. "server thread hitch warning" means the 50 ms server tick ran late - slow scripts, synchronous loops, heavy handlers; profile the server. A network thread hitch is the network/send loop falling behind - check event and state bag volume with `netEventLog`, and host load; raising an unrelated `Wait` fixes neither.
  - txAdmin's performance chart shows server tick-time trends over hours - use it to catch slow leaks and load-correlated stalls that a live snapshot misses.
- Measure once before changing anything and once after, one class of change at a time; an optimization that does not move the number gets reverted. Label every figure as measured or estimated - an estimate must never read like a profiler number.
- Look for `Wait(0)` loops, repeated natives, table scans, repeated config requires, N+1 SQL and spammy NUI messages.
- Increase waits based on distance/active state before adding complex caches, and cache only values expensive or hot enough to justify ownership and cleanup.
- Check `skills/common/security-performance.md` before performance changes in events, callbacks, sync, DB writes or loops.

## Offline Tests And Crash Harnesses

- Server Lua can be tested without FXServer: preprocess CfxLua to Lua 5.4 (rewrite compound assignment, and rewrite backtick hashes only for UPPERCASE names - lowercase backticks are SQL identifiers), then load the real resource files into a per-test environment instead of copying logic into the test.
- Drive them with a cooperative scheduler on a virtual clock: `Wait` yields, time advances only when nothing is runnable, promise resolution re-queues the waiting thread, and a step cap catches loops that never wait. Pair it with a fake `oxmysql` that really applies the shipped SQL, then assert on resulting DB state and on value conservation, not on prints.
- Prove a save pipeline is dupe-safe with a crash harness: a throwaway FXServer and MariaDB on other ports (schema only, via `mariadb-dump --no-data` - never the live DB), synthetic players, a fixed mint of items/money, trades that neither create nor destroy value, and `kill -9` mid-trade. Pass = roster sum minus the mint is 0 and no save sequence went backwards.
- Keep the harness ledger in a DB table, not a file: CfxLua sandboxes `io`, and a committed row survives the kill. Run it at realistic size - 64 synthetic players came out clean where 512 duped items (verified: kill -9 harness, 512 players).

## Finishing A Fix

- Remove temporary logs or guard them behind a config/convar debug flag, keeping diagnostics that would help future operators without console spam.
- Add a focused regression test or manual verification step when the project has no test harness.
- Update `memory/` only for recurring facts learned from real debugging, not one-off implementation details.
- Mention remaining risk when the fix depends on timing, dependency version, game build or unverified native behavior.
