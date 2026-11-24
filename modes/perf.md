# b3sty Performance Pass

Use when: asked to optimize, profile, or fix lag, hitches, high resmon, or network overflow kicks in a FiveM or RedM resource - `Wait(0)` loops, entity pool scans, event spam, `-1` broadcasts, payload size, repeated full fetches, state bag misuse.

Target: the resource path or symptom the user named.

Lower CPU time and network traffic without changing gameplay or weakening server validation. Paths are relative to the skill root (the main `SKILL.md`'s folder; the plugin root on a plugin install). Open before proposing fixes:

- `skills/common/debugging.md` -> Performance Debugging - tools and how to measure.
- `skills/common/performance.md` -> Performance Rules - CPU hot paths.
- `skills/common/network-performance.md` - event cost, rate limits, latent events, snapshot-then-deltas, state bags.

## 1. Measure Or Mark Estimates

Ask for (or use the provided) numbers: client `resmon` idle and during the slow action, `netEventLog` for a network complaint, the server profiler or hitch warnings for a server-side one. If nothing can be measured, continue - but label every figure in the report an estimate.

## 2. Find Candidates

```bash
rg -n "CreateThread|while true do|Wait\((0|1|5|10)\)" --type lua
rg -n "Trigger(Latent)?(Server|Client)Event|TriggerEvent|SendNUIMessage" --type lua
rg -n "TriggerClientEvent\([^,]+,\s*-1" --type lua
rg -n "GetGamePool|GetActivePlayers|GetPlayers\(\)|GetHashKey|json\.(en|de)code" --type lua
rg -n "MySQL\.|\.state\b|\.state\.|GlobalState|AddStateBagChangeHandler|lib\.callback" --type lua
```

Record per hit: side, loop or one-shot, how often it runs, payload shape, recipients.

## 3. Rank

- **Critical** - events or pool scans per frame, `-1` broadcast of large data, full fetch per UI open, SQL inside a loop.
- **High** - short-wait loops doing real work far from the player, large payloads, repeated `SELECT` on hot paths.
- **Medium** - allocations and repeated natives in loops, unthrottled HUD streams.
- **Low** - micro-optimizations `resmon` will not show. Never touch Low while Critical remains.

## 4. Fix Safely

- Search the whole resource and its dependents before removing or renaming an event, export, or state key.
- Keep money, item, permission, ownership, routing-bucket, NUI, and framework behavior unchanged unless asked; if a fix must change behavior, say so.
- Keep every server check (`source`, amount, ownership, distance, bucket, cooldown) after the change.
- Change one class of problem at a time, so each can be measured.

## 5. Report

```text
Summary: the main bottlenecks in two or three lines.

Performance
    Before: <value> (measured | estimate)
    After:  <value> (measured | estimate)

Network (per changed event)
    Event / frequency / payload / recipients / bytes per second (measured | estimate)

Changes: what changed and the reason for each.
Risks: anything that could affect sync, gameplay, or server checks.
Remaining: what to measure next - never claim "fully optimized".
Verify: resmon idle + action, netEventLog, server profiler, and the gameplay paths to retest.
```
