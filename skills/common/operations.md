# Operations Rules

Use this file when a resource has to behave well on a live, managed server:
save state before a scheduled restart, react to admin actions, and stay within a
performance budget operators actually watch. This is the running-in-production
side; the per-change performance rules are in
`skills/common/security-performance.md` -> Performance Rules and
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
  (`skills/common/security-performance.md` -> Config, Convars, And Secrets);
  the hardening baseline is `references/server.cfg.example`.
- Watch the server console for `server thread hitch warning` and
  `network thread hitch warning`; each names a side to profile
  (`skills/common/debugging.md` -> Performance Debugging). A recurring hitch is
  a resource to fix, not noise to ignore.
- Vet third-party resources before adding them
  (`skills/common/security-performance.md` -> Server Hardening And Operations);
  a resource you cannot read or audit is a risk whatever it promises.

## Review Questions

- Does the resource persist state on `txAdmin:events:scheduledRestart` with
  lead time, rather than trusting `onResourceStop` during a restart?
- Are txAdmin events handled with `AddEventHandler`, never `RegisterNetEvent`?
- Is there a baseline resmon/profiler reading, or is "it feels fine" the only
  evidence?
- Is the game build and artifact pinned, and are secrets in convars rather than
  in a resource file?
- Are console hitch warnings investigated to the resource that causes them?
