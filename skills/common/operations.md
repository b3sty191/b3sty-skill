# Operations Rules

Use this file when a resource has to behave well on a live, managed server:
save state before a scheduled restart, react to admin actions, and stay within a
performance budget operators actually watch. This is the running-in-production
side; the per-change performance rules are in
`skills/common/performance.md` -> Performance Rules and
`skills/common/network-performance.md`, and how to measure is in
`skills/common/debugging.md` -> Performance Debugging. Confirm event names
against the installed txAdmin version before relying on them.

## txAdmin Events

Most managed FXServers run under txAdmin, which dispatches server-side events to
resources as `txAdmin:events:<name>` via a server-local `TriggerEvent`. Listen
with `AddEventHandler`, never `RegisterNetEvent` - these are server-local, and
registering one as a net event lets any client forge it. The names below are
confirmed in the txAdmin source (`resource/sv_main.lua`, `core/modules/`); the
full set also includes `playerWarned`, `whitelistPlayer`, `actionRevoked`,
`announcement`, `playerDirectMessage`, and `healedPlayer`.

- `txAdmin:events:scheduledRestart` fires on each restart warning. Its
  `eventData` carries `secondsRemaining` and a `translatedMessage`. Use it as
  the signal to persist state before the server goes down.
- `txAdmin:events:playerKicked` / `playerBanned` fire with `eventData.target`
  (the server id), `author`, and `reason`. React when your resource must clean
  up or log that a player left involuntarily; do not re-implement the kick.

## Save Before The Restart, Not After

- A scheduled restart tears the process down. `onResourceStop` runs during that
  teardown with no time to yield (`memory/common/cfx-patterns.md` and
  `skills/common/runtime.md` -> Resource Lifecycle: an `onResourceStop` flush
  must not yield), so it is not where a reliable save happens.
- Flush dirty player/world state when `txAdmin:events:scheduledRestart` fires
  with enough `secondsRemaining` left to finish the writes - treat the first
  warning as the deadline, not the last.

```lua
AddEventHandler("txAdmin:events:scheduledRestart", function(eventData)
    if eventData.secondsRemaining and eventData.secondsRemaining <= 60 then
        Controller:FlushAllDirty()   -- persist before the process goes down
    end
end)
```

- Still save on `playerDropped` and keep the normal autosave/dirty-flag loop
  (`memory/common/cfx-patterns.md`); the restart hook is an extra guarantee, not
  the only save path.
- Do not assume the restart event means your data survived - verify a clean load
  after a real restart on a test server.
- Never `restart` a framework or any other dependency alone on a live server:
  FXServer stops every resource that lists it as a dependency and, on start
  again, only starts those still waiting for it - so the dependents stay
  stopped and their `onResourceStop` saves nothing. Dependents that cached an
  export such as `getSharedObject` also keep calling into the dead VM
  (`skills/common/runtime.md` -> Exports And Stale References). Restart every
  dependent too, or save everything and restart the whole server
  (verified: `ResourceDependencyLoader.cpp`, plus a live restart with 16
  dependents).
- Only txAdmin's Restart/Stop and an explicit save command leave a save window.
  txAdmin fires `txAdmin:events:serverShuttingDown` and kicks every player in
  the same call, then kills the process after `shutdownNoticeDelayMs` - default
  5000 ms, range 0-60000. A worst-case full-server save measured ~11 s, so that
  delay had to go to 15000 ms (verified: txAdmin 8.1.1 `resource/sv_main.lua`,
  live save timing).
- Console `stop`/`quit`, `kill`, a crash or power loss fire no event and give no
  save window at all. The safe procedure is: run the save-all command, wait for
  its completion log line, then restart.

## Detect Unclean Stops

On the next boot a crash looks exactly like a clean shutdown unless the server
recorded what it was doing.

- Keep a session marker in resource KVP: write `running` at start plus a
  heartbeat every few seconds, write `stopping` from
  `txAdmin:events:serverShuttingDown` before saving, and write `clean` only from
  the save-completion callback, only when the save really succeeded.
- Finding `running` at the next start means the process died outright, and
  `stopping` means the shutdown save never finished - in both cases report the
  transfers since the heartbeat watermark.
- `onResourceStop` must never mark the session clean: a resource restart saves
  nobody. A `stopping` marker older than ~120 s while the server is still alive
  is a cancelled restart - put it back to `running`
  (verified: offline regression suite over this state machine).

## Performance Operations

Measure on the side that is slow, and treat every number as measured or an
estimate (`skills/common/debugging.md` -> Performance Debugging has the tools).

- Client `resmon` (F8) finds the resource eating frame time; server-side
  `resmon` exists only in the Windows FXServer GUI, so on Linux use the server
  profiler.
- `profiler record <frames>` then `profiler view` gives a tick-level trace to
  the file:line; use it before optimizing so you fix the real hot path.
- txAdmin's performance chart shows server tick-time over hours - use it to
  catch slow leaks and restart-correlated stalls a short snapshot misses.
- Community rule of thumb (not an engine guarantee): a resource idling much
  above ~0.10ms deserves a look. Compare against this server's baseline, idle
  and during the action, not an absolute number.

## Operator Hygiene

- Pin the game build with `sv_enforceGameBuild` and pin the artifact version;
  an unpinned build changes native behavior and DLC availability under you.
- Keep secrets in `server.cfg` / `secrets.cfg` convars, never in a resource
  (`skills/common/server-hardening.md` -> Config, Convars, And Secrets);
  the hardening baseline is `references/server.cfg.example`.
- Watch the server console for `server thread hitch warning` and
  `network thread hitch warning`; each names a side to profile
  (`skills/common/debugging.md` -> Performance Debugging). A recurring hitch is
  a resource to fix, not noise to ignore.
- Vet third-party resources before adding them
  (`skills/common/server-hardening.md` -> Server Hardening And Operations);
  a resource you cannot read or audit is a risk whatever it promises.

## Artifact Upgrade And Rollback

An artifact upgrade is a directory swap, not an in-place update. Track releases
via `https://changelogs-live.fivem.net/api/changelog/versions/linux/server`
(`latest`/`recommended`; the download URL also contains the source commit).

- Extract each `fx.tar.xz` into its own pristine directory and never write into
  it. Deploy by moving the live directory aside and copying the candidate into
  place, then carry over the runtime files the artifact does not ship:
  `server-tls.crt`/`.key`, `server-monitor-token.key`, `crashes/`.
- Gate the swap on a trustworthy "nobody online, nobody connecting" signal from
  code you control - a resource can override `players.json` and hide real
  players.
- Verify the boot by grepping the log for named markers (license OK, framework
  started) and roll back to the saved directory automatically on a miss. Strip
  ANSI colour codes first (`sed 's/\x1b\[[0-9;]*m//g'`): FXServer emits them
  mid-line, so an unstripped grep misses every marker.
- Prune old artifact directories by mtime, not by name, or the newest rollback
  target sorts first and gets deleted (verified: both bugs hit live, then fixed).
- Under txAdmin, Restart only respawns the child FXServer; picking up a new
  artifact needs the parent process restarted.
- A `screen -dmS` launched from a systemd oneshot unit or a timer lives in that
  unit's cgroup and dies the moment the unit ends. Give it its own transient
  unit: `systemd-run --collect --unit=fxserver-screen -p Type=forking screen
  -dmS fxserver ...` (verified: live outage, then a simulated oneshot where the
  old launch died and the new one survived the unit).

## Review Questions

- Does the resource persist state on `txAdmin:events:scheduledRestart` with
  lead time, rather than trusting `onResourceStop` during a restart?
- Are txAdmin events handled with `AddEventHandler`, never `RegisterNetEvent`?
- Is there a baseline resmon/profiler reading, or is "it feels fine" the only
  evidence?
- Is the game build and artifact pinned, and are secrets in convars rather than
  in a resource file?
- Are console hitch warnings investigated to the resource that causes them?
- Is a dependency ever restarted alone on a live server, and does the shutdown
  notice delay cover the measured worst-case save?
