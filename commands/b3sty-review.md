---
description: Review a RedM/FiveM Lua resource against the b3sty rules and report findings ranked by severity. Use when asked to review, audit, check, or security-check a FiveM or RedM resource, a server event, an NUI bridge, or a pull request touching CFX Lua code, or before releasing/selling a resource. Covers server authority, give-item/give-money exploits, event and NUI trust boundaries, SQL injection, XSS, networking, lifecycle cleanup, framework usage, and performance.
argument-hint: [resource path, files, or PR]
---

# b3sty Resource Review

Target: $ARGUMENTS

Review a RedM/FiveM resource and report verified findings, most severe first. This command drives the process; the rules themselves live in the b3sty-skill package. Paths under `skills/`, `memory/` and `references/` below are relative to the b3sty-skill root (the folder holding the main `SKILL.md`; with the plugin install, the plugin root).

Do not edit code during the review. Offer fixes at the end; apply them only when asked.

## 1. Scope

- Identify the game (`games` in `fxmanifest.lua`), the framework (ESX, QBCore, Qbox, VORP, RSG, or none), ox_lib usage, NUI (`ui_page`), and database use (oxmysql).
- If the request names specific files or a diff, review those plus whatever they call; otherwise review the whole resource.

## 2. Inventory Entry Points

List every place untrusted input enters before reading logic in depth:

```bash
rg -n "RegisterNetEvent|RegisterServerEvent|AddEventHandler\(\"(weaponDamageEvent|explosionEvent|startProjectileEvent|ptFxEvent|removeAllWeaponsEvent|entityCreating)" --type lua
rg -n "RegisterNUICallback|RegisterCommand|exports\(|lib\.callback\.register|CreateCallback|RegisterServerCallback|SetHttpHandler" --type lua
rg -n "MySQL\.|oxmysql|exports\.ghmattimysql|exports\['mysql-async'\]" --type lua
rg -n "innerHTML|v-html|\{@html|dangerouslySetInnerHTML|insertAdjacentHTML" -g "!*.lua"
rg -n "Wait\(0\)|while true do" --type lua
```

Record each entry point with file:line and what it can change (money, items, jobs, entities, saved data, UI only).

## 3. Review In Priority Order

Follow the order in the main `SKILL.md` -> Review Priorities. Open only the rule files the resource needs:

| Surface found | Open |
|---|---|
| Any server event, callback, command, export | `skills/common/security-performance.md` (Required Event Pattern, Give-Value Event Hardening, Review Questions) |
| Money, items, rewards, shops | `skills/common/security-performance.md` -> Give-value event checklist |
| Framework calls | `skills/common/frameworks.md` |
| NUI | `skills/common/nui.md` |
| Networked entities, net IDs, buckets, built-in client events | `skills/common/networking.md` |
| SQL | `skills/common/database.md` |
| Threads, `source` across yields, exports, lifecycle | `skills/common/runtime.md` |
| Natives | `skills/common/native-usage.md`, then `references/natives/` to confirm names and hashes |
| Game-specific code | `skills/fivem/rules.md` or `skills/redm/rules.md` |
| Cross-resource calls | `skills/common/multi-resource.md` |

For each entry point check, in this order:

1. **Authority** - does the server decide the price, amount, reward, target, and permission, or does it trust the client payload?
2. **Input** - type, range, integer, NaN, string length, table depth; `local source = source` captured before any yield.
3. **Abuse** - throttle, in-flight lock, replay, distance/ownership checks, audit log.
4. **Lifecycle** - cleanup on `playerDropped`, character unload, and `onResourceStop`; NUI focus released; entities guarded with `DoesEntityExist`.
5. **Portability** - RedM/FiveM-specific natives or behavior in shared files.
6. **Performance** - hot loops, `Wait(0)`, repeated lookups, broadcasts to `-1`.
7. **Style** - only after everything above, and only where it hurts readability.

Check `memory/` for known engine quirks before reporting something as a bug in the resource.

## 4. Verify Before Reporting

- Re-read the code around every candidate finding. Drop it if another line already handles it.
- For exploit findings, write the concrete abuse: which event a cheater triggers, with what payload, and what they gain.
- Confirm native names, hashes, and signatures against `references/natives/` instead of memory.
- Do not report taste or formatting preferences as defects.

## 5. Report

Group by severity:

- **Critical** - duplication or free money/items, arbitrary SQL, NUI XSS reachable by other players, admin actions without permission checks, remote crash of the server.
- **High** - exploitable with effort or under a race, missing ownership/distance checks on valuable actions, unbounded payloads.
- **Medium** - leaks (entities, handlers, per-player tables), stuck NUI focus, missing cleanup, noticeable performance cost.
- **Low** - portability risks, minor performance, readability that hides bugs.

For each finding give:

```text
[Severity] file.lua:123 - one-line summary
Abuse / impact: how it is triggered and what happens.
Fix: the concrete change (short code when it helps), citing the rule file section.
```

End with: entry points reviewed, what was not reviewed and why, and the manual repro steps worth running in-game. If the review surfaced a new engine quirk or a recurring mistake, propose a `memory/` entry (date and game build included).
