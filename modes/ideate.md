# b3sty Ideate

Use when: asked to brainstorm, ideate, or explore design options for FiveM/RedM - resource and data-model architecture, events vs state bags vs latent events vs callbacks, anti-dupe and anti-cheat design, economy and item flows, framework bridge contracts, ESX/QBCore to Qbox migrations, NUI architecture, export and event naming, or hypothesis classes for desyncs, hitches, and "only on a full server" bugs. Skip for native lookups, syntax, bugs with a known root cause, or anything an existing rule already decides.

Target: the design problem or fuzzy bug the user named.

Get past the textbook answer where the obvious answer is expensive to get wrong, without a clever idea breaking a security or performance rule. Generators run free; the critic holds the rules. Paths are relative to the skill root (the main `SKILL.md`'s folder; the plugin root on a plugin install).

Method adapted from the ADHD divergent-ideation skill ([github.com/UditAkhourii/adhd](https://github.com/UditAkhourii/adhd), Copyright (c) 2026 ADHD contributors, MIT - full notice in `NOTICE.md`), rewritten for CFX: FiveM/RedM frames, b3sty rules as the critic's trap gate. Its benchmark is small (6 problems, LLM-judged, 5 wins and 1 loss; the loss, a CLI retry/timeout design, went to the direct answer on immediate shippability) - a tool for decision points, not a default.

## 0. Gate - Run This First

Ideation asked for explicitly? Go to Phase 1. Otherwise answer directly, no ideation, when any of these hold:

- A rule already decides it. "Where do I validate the price?" is `skills/common/security-performance.md` -> Server Authority, not a brainstorm. Name the rule.
- It is a lookup: a native signature or hash (search `references/natives/`), an ox_lib or framework API, a manifest key.
- The bug has a known root cause - fix it.
- The phrasing is closed: "quick", "just", "standard", "one-line", "the usual way".
- The stakes are low enough that a wrong first answer costs minutes.

When you skip, you may offer one line: a wider, rule-checked exploration on request.

## 1. Diverge - Generators, No Critic

1. Pick the size from Calibration below (default: 5 frames × 6 ideas) and that tier's frames. Always include **cheater with an executor** when the problem touches money, items, permissions, or any client-callable surface.
2. Spawn one Agent call per frame **in parallel, in one message**, each with only the problem, the user's context, the frame's vantage, and this instruction (fill in N):

   > Generate, do not judge. Under this frame write N short, distinct ideas, one phrase or sentence each. No evaluating, ranking, or hedging. The three answers anyone would give first are off limits - go past them. Do not read files, search, or load any skill: work only from this frame and the problem. Output only a JSON array: `[{"text": "...", "rationale": "..."}]`.

3. **Isolation is the method.** Never run branches one after another in your own context, never pass one branch's output to another - branches that see each other anchor and collapse into one wider thought.
4. **Keep the b3sty rules out of the generators.** Rules there pull every branch back to the textbook answer; they belong to the critic in Phase 2, which is what keeps the result safe. Prefer a minimal agent type with no file tools.

### CFX frames

| Frame | Vantage | Tag |
|---|---|---|
| cheater with an executor | A Lua executor on your own client: any net event with any arguments, any NUI callback with no UI open, spawn and delete networked entities, in a loop. Break the obvious design every way, then turn each break into a design move. | security |
| OneSync entity owner | Ownership belongs to some random client, migrates mid-action, the entity leaves the starting player's scope, players sit in different routing buckets. What does the design assume about who owns what, and what if that flips? | sync |
| one server thread, every resource | One server thread and every client's bandwidth, shared. Price the idea per tick and per client at full population. What disappears if you push instead of poll, batch, defer, or send deltas not snapshots? | perf |
| restart mid-action | The resource restarts, txAdmin restarts the server, or the player drops mid-operation. What is half-done, applied twice, or lost - and what design is safe to interrupt at any line? | lifecycle |
| owner who cannot read Lua | Edits only config and `server.cfg`, starts resources in the wrong order, runs a framework you did not test. What design still works, or fails loudly instead of silently? | ops |
| economy designer | Every source can inflate, every transfer can dupe. Map sources, sinks, and transfers, then shape the flow so totals always reconcile. | economy |
| RedM port | The same feature on RDR3: different natives, some server-side reads unreliable, VORP or RSG instead of ESX or QBCore. Which assumptions are GTA-only, what survives both games? | portability |
| bridge author | Must run unchanged on ESX, QBCore, and Qbox (VORP or RSG on RedM). What is the smallest contract the core needs from a framework, and what moves behind the bridge? | design |

### General frames

| Frame | Vantage | Tag |
|---|---|---|
| inversion | Guarantee the opposite - a guaranteed dupe, lag, or desync - then negate each answer into a design move. | general |
| 3am on-call | You get woken when this breaks on a full server. What design lets you sleep: what is observable, what heals itself, what fails closed? | general |
| no budget, one hour | No new dependencies, one hour. The roughest version that still does the one thing that matters. | general |
| remove the load-bearing assumption | Name what everyone treats as fixed - one net event per action, the database, the framework, the client asking first - and remove it. What becomes possible? | wild |
| speedrunner | Find the skips: the abusive-but-legal shortcut through the engine, the framework, or the data model. | wild |
| biology | Transplant a mechanism from biology - immune response, quorum sensing, metabolism - and force-fit it on the problem. | wild |
| logistics | Steal queues, batching, hub-and-spoke, just-in-time, and returns, and apply them literally. | wild |

A frame fills one slot only: a `general`-tagged frame the general slot, a `wild`-tagged frame the wild slot. Vary the picks between runs so a re-run explores different ground.

## 2. Focus - Critic With The Rules

Run this yourself after every branch returns, with the rule files below open.

1. **Score** each idea 0-10 on novelty (distance from the default), viability (could it ship on a live server), and fit (does it solve the stated problem).
2. **Trap gate.** An idea needing anything in the trap table is a trap: cite the rule, and no novelty score rescues it. **Repair before you discard** - when the core is good and only the enforcement point is wrong ("the client checks the trade" becomes "the client predicts for UX, the server decides"), list the trap, then score the repaired version as its own candidate.
3. **Cluster** survivors into 3-6 groups by underlying angle, not shared keywords ("push-not-poll plays", "escrow-the-value plays", "server-registry-decides plays").
4. **Deepen the top 3** by weighted score (novelty 0.35, viability 0.40, fit 0.25), traps excluded. For each, list the rule files for **every surface it touches** (events, NUI, DB, inventory, entities, state bags, lifecycle), not only files cited for traps. Spawn 3 parallel Agent calls, one per idea, each with the idea, the trap table, those files, and this instruction:

   > Deepen one idea; the b3sty rule files you were given are binding. In 4-8 sentences sketch how it works at CFX level: which side owns what, and which events, exports, state bags, tables, and inventory calls it uses. Name the load-bearing risk and the first concrete step (a file, an event, or a schema change). List the rule files the design satisfies, then add 3-5 child ideas: variations, hybrids, or what it unlocks. Output JSON only: `{"sketch": "...", "risk": "...", "first_step": "...", "rules": ["..."], "children": ["..."]}`.

5. **Re-gate.** Run every deepened sketch, child idea, and repaired candidate through the whole trap table again, against every rule file the sketch touches. Drop or repair anything that fails. Only ideas that pass the re-gate may appear under Converge, take the ★, or be the Recommendation.

| Trap | Rule |
|---|---|
| Client-sent value or client-side check as the authority: price, amount, target id, identifier, item name, "the client says it's done" | `skills/common/security-performance.md` -> Server Authority, and Event Trust Boundary; coords and distance: `skills/common/client-input-validation.md` -> Position And Interaction Checks |
| NUI callback, ox_target option, client menu, or client-set flag as the permission check | `skills/common/nui.md` -> Security, `skills/common/ox-ecosystem.md`, `skills/common/give-value-hardening.md` -> ACE Permissions And Admin Authority |
| `GetInvokingResource()` as the gate on a client-callable event | `skills/common/multi-resource.md` -> Events Across Resources |
| Client-supplied handle or net ID, the momentary entity owner, a cached net ID, or a cross-bucket reference as authority; a plan needing the server to own or assign an entity, which no server native can do | `skills/common/networking.md` -> Handles And Net IDs, Entity Ownership, and Routing Buckets; `skills/common/client-input-validation.md` -> Entity And Net ID Validation |
| Granting value with no capacity check, atomic write, or replay protection | `skills/common/security-performance.md` -> Atomic State Changes And Replay Protection, `skills/common/give-value-hardening.md` -> Give-Value Event Hardening |
| Two sources of truth for money or items - SQL plus a framework RAM cache, a custom table beside ox_inventory - or changing inventory outside ox_inventory's exports and hooks | `skills/common/give-value-hardening.md` -> Give-Value Event Hardening (step 6); `skills/common/ox-ecosystem.md` -> ox_inventory Is Server-Authoritative - Use Its Exports, and Hooks Are The Anti-Dupe Boundary |
| Generic event, export, or callback dispatching on a caller-supplied action, function, or config name; server-internal handler registered with `RegisterNetEvent` | `skills/common/security-performance.md` -> Network Exposure |
| Client-written replicated state bags treated as authoritative | `skills/common/client-input-validation.md` -> Sync Safety |
| SQL built by string concatenation | `skills/common/database.md` -> SQL Injection |
| `Wait(0)` polling where an event, a state bag, or a zone would do | `skills/common/performance.md` -> Performance Rules |
| Events per tick, large payloads to `-1`, re-fetching the full dataset per UI open or action instead of a snapshot once then deltas; a public event with no throttle | `skills/common/network-performance.md` -> Cost Model, Snapshot Then Deltas, and Audience; `skills/common/security-performance.md` -> Throttle And Cooldown |
| Webhook, token, or key in a client or shared file, a `setr`/`sets` convar, a state bag, or NUI | `skills/common/server-hardening.md` -> Config, Convars, And Secrets |
| Awaiting or yielding inside `onResourceStop`, or relying on it as the only save before a scheduled restart - a non-awaited force-save there is still required | `memory/common/cfx-patterns.md` -> Player Persistence Pattern, `skills/common/runtime.md` -> Yield Hazards, `skills/common/operations.md` -> Save Before The Restart, Not After |
| `load()` of fetched code, writing outside the resource, or an unsafe sandbox grant | `skills/common/server-hardening.md` -> The Resource Sandbox |
| Premature abstraction - a new framework, dispatcher, or generic validator for a small resource; a cache with no owner or cleanup path | `skills/common/performance.md` -> Anti-Overengineering, and Performance Rules |
| Hidden operational cost - a new `server.cfg` grant, a paid or external service, behavior tied to one artifact or game build; false economy - a saving that moves the cost somewhere worse | judgement, no rule file |

## 3. Output

Keep this structure - it is the point; do not flatten it into prose.

```text
Brief: the problem in one or two lines, and any reframe used.
Wide set, by cluster, each labeled by its angle:
    - idea  [N7 V8 F9]
Converge: 2-4 re-gated picks, the reason for each, and the b3sty rules each relies on.
    ★ marks the non-obvious pick that is still viable.
Traps: each with the one-line reason and the rule it breaks (repaired versions
    appear under Converge or the Wide set).
Focus: the 3 deepened ideas - sketch, load-bearing risk, first step, rules, child ideas.
Provocation: one question or wildcard that opens a new direction if nothing landed.
Recommendation: one deepened, re-gated idea (or a named combination), why it beats
    the others, and its first step.
```

Commit to the Recommendation - 30 ideas with "you choose" is not an answer. When the user picks one, build it under the normal rules (new-resource mode, `modes/new-resource.md`, for a new resource) and run review mode (`modes/review.md`) before it ships.

## Anti-Patterns

- **Decorated convergence.** Many variations of one idea is not breadth; if every candidate rests on the same assumption, nothing diverged.
- **Weirdness with no landing.** Unsorted wild ideas help no more than one safe answer does. Always converge and recommend.
- **Fake parallelism** (Phase 1.3), **rules in the generator or novelty past the gate** (Phase 1.4 and the re-gate: the first kills breadth, the second ships an exploit), and **ideating where a rule already answers** (the Gate: a lookup with extra steps - point to the rule).

## Calibration And Cost

| Tier | Frames × ideas (N) | Frame mix |
|---|---|---|
| small (naming an export or event) | 3 × 4 | 2 CFX (the cheater frame if required) + 1 wild |
| default (a system design) | 5 × 6 | 3 CFX + 1 general + 1 wild |
| large (whole-server architecture) | 6 × 8 | 4 CFX + 1 general + 1 wild |

- Stop diverging when new ideas repeat the shape of existing ones; do not pad to a number.
- A default run is about 5 generator calls, the critic pass, 3 deepen calls, and the re-gate - roughly 5-10× a direct answer. Every branch reloads its own context, so keep each generator prompt to the problem and the frame.
