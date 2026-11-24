# Operations Rules

Use when a resource has to behave on a live, managed server: save state before a scheduled restart, react to admin actions, stay inside a performance budget operators watch. Per-change performance rules are in `skills/common/performance.md` -> Performance Rules and `skills/common/network-performance.md`; how to measure is in `skills/common/debugging.md` -> Performance Debugging. Confirm event names against the installed txAdmin version.

## txAdmin Events

Most managed FXServers run txAdmin, which dispatches `txAdmin:events:<name>` to resources with a server-local `TriggerEvent`. Listen with `AddEventHandler`, never `RegisterNetEvent` - they are server-local, and a net registration lets any client forge them. Names below are confirmed in the txAdmin source (`resource/sv_main.lua`, `core/modules/`); the full set also has `playerWarned`, `whitelistPlayer`, `actionRevoked`, `announcement`, `playerDirectMessage`, `healedPlayer`.

- `txAdmin:events:scheduledRestart` fires on each restart warning, `eventData` carrying `secondsRemaining` and a `translatedMessage`: the signal to persist state before the server goes down.
- `txAdmin:events:playerKicked` / `playerBanned` fire with `eventData.target` (server id), `author` and `reason`. React when your resource must clean up or log an involuntary leave; do not re-implement the kick.

## Save Before The Restart, Not After

- A scheduled restart tears the process down, and `onResourceStop` runs during that teardown with no time to yield (`memory/common/cfx-patterns.md` and `skills/common/runtime.md` -> Resource Lifecycle: an `onResourceStop` flush must not yield), so it is not where a reliable save happens.
- Flush dirty player/world state on `txAdmin:events:scheduledRestart` while enough `secondsRemaining` is left to finish the writes - the first warning is the deadline, not the last.

```lua
AddEventHandler("txAdmin:events:scheduledRestart", function(eventData)
    if eventData.secondsRemaining and eventData.secondsRemaining <= 60 then
        Controller:FlushAllDirty()   -- persist before the process goes down
    end
end)
```

- Still save on `playerDropped` and keep the normal autosave/dirty-flag loop (`memory/common/cfx-patterns.md`): the restart hook is an extra guarantee, not the only save path.
- The event firing does not mean your data survived - verify a clean load after a real restart on a test server.
- Never `restart` a framework or any other dependency alone on a live server: FXServer stops every resource that lists it as a dependency and, on start again, only starts those still waiting for it, so dependents stay stopped and their `onResourceStop` saves nothing. Dependents that cached an export such as `getSharedObject` also keep calling into the dead VM (`skills/common/runtime.md` -> Exports And Stale References). Restart every dependent too, or save everything and restart the whole server (verified: `ResourceDependencyLoader.cpp`, plus a live restart with 16 dependents).
- Only txAdmin's Restart/Stop and an explicit save command leave a save window. txAdmin fires `txAdmin:events:serverShuttingDown` and kicks every player in the same call, then kills the process after `shutdownNoticeDelayMs` - default 5000 ms, range 0-60000. A worst-case full-server save measured ~11 s, so that delay had to go to 15000 ms (verified: txAdmin 8.1.1 `resource/sv_main.lua`, live save timing).
- Console `stop`/`quit`, `kill`, a crash or power loss fire no event and give no save window at all. Safe procedure: run the save-all command, wait for its completion log line, then restart.

## Detect Unclean Stops

On the next boot a crash looks exactly like a clean shutdown unless the server recorded what it was doing.

- Keep a session marker in resource KVP: `running` at start plus a heartbeat every few seconds, `stopping` from `txAdmin:events:serverShuttingDown` before saving, `clean` only from the save-completion callback and only when the save really succeeded.
- `running` at the next start means the process died outright; `stopping` means the shutdown save never finished. In both cases report the transfers since the heartbeat watermark.
- `onResourceStop` must never mark the session clean: a resource restart saves nobody. A `stopping` marker older than ~120 s while the server is still alive is a cancelled restart - put it back to `running` (verified: offline regression suite over this state machine).

## Performance Operations

Measure on the side that is slow, and label every number measured or estimated. The tools - client `resmon` (F8), `profiler record`/`profiler view` down to file:line, the ~0.10ms idle rule of thumb, no server `resmon` outside the Windows GUI - are in `skills/common/debugging.md` -> Performance Debugging; run them before optimizing so you fix the real hot path.

- Compare against this server's own baseline, idle and during the action, not an absolute number.
- txAdmin's performance chart shows server tick-time over hours: use it for slow leaks and restart-correlated stalls a short snapshot misses.

## Operator Hygiene

- Pin the game build with `sv_enforceGameBuild` and pin the artifact version; an unpinned build changes native behavior and DLC availability under you.
- Keep secrets in `server.cfg` / `secrets.cfg` convars, never in a resource (`skills/common/server-hardening.md` -> Config, Convars, And Secrets); the hardening baseline is `references/server.cfg.example`.
- Watch the console for `server thread hitch warning` and `network thread hitch warning`: each names a side to profile (`skills/common/debugging.md` -> Performance Debugging), and a recurring hitch is a resource to fix, not noise.
- Vet third-party resources before adding them (`skills/common/server-hardening.md` -> Server Hardening And Operations); one you cannot read or audit is a risk whatever it promises.

## Artifact Upgrade And Rollback

An artifact upgrade is a directory swap, not an in-place update. Track releases via `https://changelogs-live.fivem.net/api/changelog/versions/linux/server` (`latest`/`recommended`; the download URL also contains the source commit).

- Extract each `fx.tar.xz` into its own pristine directory and never write into it. Deploy by moving the live directory aside and copying the candidate into place, then carry over the runtime files the artifact does not ship: `server-tls.crt`/`.key`, `server-monitor-token.key`, `crashes/`.
- Gate the swap on a trustworthy "nobody online, nobody connecting" signal from code you control - a resource can override `players.json` and hide real players.
- Verify the boot by grepping the log for named markers (license OK, framework started) and roll back to the saved directory automatically on a miss. Strip ANSI colour codes first (`sed 's/\x1b\[[0-9;]*m//g'`): FXServer emits them mid-line, so an unstripped grep misses every marker.
- Prune old artifact directories by mtime, not by name, or the newest rollback target sorts first and gets deleted (verified: both bugs hit live, then fixed).
- Under txAdmin, Restart only respawns the child FXServer; picking up a new artifact needs the parent process restarted.
- A `screen -dmS` launched from a systemd oneshot unit or a timer lives in that unit's cgroup and dies the moment the unit ends. Give it its own transient unit: `systemd-run --collect --unit=fxserver-screen -p Type=forking screen -dmS fxserver ...` (verified: live outage, then a simulated oneshot where the old launch died and the new one survived the unit).

## Review Questions

- State persisted on `txAdmin:events:scheduledRestart` with lead time, not left to `onResourceStop`?
- txAdmin events handled with `AddEventHandler`, never `RegisterNetEvent`?
- A baseline resmon/profiler reading, or is "it feels fine" the only evidence?
- Game build and artifact pinned, secrets in convars rather than a resource file?
- Console hitch warnings chased to the resource that causes them?
- Any dependency restarted alone on a live server, and does the shutdown notice delay cover the measured worst-case save?
