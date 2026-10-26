---
description: Find and fix CPU and network performance problems in a RedM/FiveM Lua resource - resmon cost, Wait(0) loops, entity pool scans, event spam, -1 broadcasts, payload size, repeated full fetches, state bag misuse - and report measured versus estimated results. Use when asked to optimize, profile, or fix lag, hitches, high resmon, or network overflow kicks in a FiveM or RedM resource.
argument-hint: [resource path or symptom]
---

# b3sty Performance Pass

Target: $ARGUMENTS

Lower CPU time and network traffic without changing gameplay or weakening server validation. Paths under `skills/` below are relative to the b3sty-skill root (the folder holding the main `SKILL.md`; with the plugin install, the plugin root).

Open these before proposing fixes:

- `skills/common/debugging.md` -> Performance Debugging - tools and how to measure.
- `skills/common/security-performance.md` -> Performance Rules - CPU hot paths.
- `skills/common/network-performance.md` - event cost, rate limits, latent events, snapshot-then-deltas, state bags.

## 1. Measure Or Mark Estimates

- Ask for (or use provided) numbers: client `resmon` idle and during the slow action, `netEventLog` if the complaint is network, server profiler or hitch warnings if the complaint is server-side.
- If nothing can be measured, continue, but every figure in the report is an estimate and labeled as one.

## 2. Find Candidates

```bash
rg -n "CreateThread|while true do|Wait\((0|1|5|10)\)" --type lua
rg -n "Trigger(Latent)?(Server|Client)Event|TriggerEvent|SendNUIMessage" --type lua
rg -n "TriggerClientEvent\([^,]+,\s*-1" --type lua
rg -n "GetGamePool|GetActivePlayers|GetPlayers\(\)|GetHashKey|json\.(en|de)code" --type lua
rg -n "MySQL\.|\.state\b|\.state\.|GlobalState|AddStateBagChangeHandler|lib\.callback" --type lua
```

For each hit record: side, loop or one-shot, how often it runs, payload shape, recipients.

## 3. Rank

- **Critical** - events or pool scans per frame, `-1` broadcast of large data, full fetch per UI open, SQL inside a loop.
- **High** - short-wait loops doing real work far from the player, large payloads, repeated `SELECT` on hot paths.
- **Medium** - allocations and repeated natives in loops, unthrottled HUD streams.
- **Low** - micro-optimizations `resmon` will not show. Do not touch Low while Critical remains.

## 4. Fix Safely

- Search the whole resource and its dependents before removing or renaming an event, export, or state key.
- Keep behavior of money, items, permissions, ownership, routing buckets, NUI, and framework state unchanged unless asked; if a fix must change behavior, say so.
- Keep every server check (`source`, amount, ownership, distance, bucket, cooldown) after the change.
- Change one class of problem at a time so each can be measured.

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
