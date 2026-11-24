---
description: Parallel divergent ideation for open-ended RedM/FiveM design decisions - resource architecture, sync strategy, anti-dupe and anti-cheat design, economy flows, framework bridges, migration plans, NUI architecture, naming exports and events, and hypothesis classes for fuzzy desync or hitch bugs. Isolated branches generate under different frames, then a separate critic scores, clusters, and rejects anything that breaks a b3sty rule before deepening the best survivors. Use on /b3sty-ideate or when asked to brainstorm, ideate, or explore design options for a FiveM or RedM problem; skip for native lookups, syntax, bugs with a known root cause, or anything an existing rule already decides.
argument-hint: [the design problem or fuzzy bug]
---

# b3sty Ideate

Target: $ARGUMENTS

Get past the textbook answer on design decisions where the obvious answer is expensive to get wrong, without letting a clever idea break a security or performance rule. Generators run free; the critic holds the rules. Paths under `skills/` below are relative to the b3sty-skill root (the folder holding the main `SKILL.md`; with the plugin install, the plugin root).

Method adapted from the ADHD divergent-ideation skill by UditAkhourii ([github.com/UditAkhourii/adhd](https://github.com/UditAkhourii/adhd), MIT) and rewritten for CFX: FiveM/RedM frames, and the b3sty rules as the critic's trap gate. The source's own benchmark is small (6 problems, LLM-judged, 5 wins and 1 loss); its loss was a "ship it tomorrow" problem where the direct answer was more useful. Treat this as a tool for decision points, not a default.

## 0. Gate - Run This First

If the user typed `/b3sty-ideate` or asked for ideation explicitly, skip to Phase 1.

Otherwise answer directly, without ideation, when any of these hold:

- A rule already decides it. "Where do I validate the price?" is `skills/common/security-performance.md` -> Server Authority, not a brainstorm. Name the rule.
- It is a lookup: a native signature or hash (search `references/natives/`), an ox_lib or framework API, a manifest key.
- The bug has a known root cause - fix it.
- The phrasing is closed: "quick", "just", "standard", "one-line", "the usual way".
- The stakes are low enough that a wrong first answer costs minutes.

When you skip, you may add one line: *"For a wider exploration with rule-checked trap detection, run `/b3sty-ideate <problem>`."*

Good fits: resource and data-model architecture, choosing events vs state bags vs latent events vs callbacks, anti-dupe and anti-cheat design, economy and item flows, framework bridge contracts, ESX/QBCore to Qbox migrations, NUI architecture, export and event naming, and hypothesis classes for desyncs, hitches, and "only on a full server" bugs.

## 1. Diverge - Generators, No Critic

1. Pick 5 frames from the tables below: 3 CFX frames that fit the problem, 1 general frame, and at least 1 marked wild. Always include **cheater with an executor** when the problem touches money, items, permissions, or any client-callable surface.
2. Spawn 5 Agent calls **in parallel, in one message**, one per frame. Each gets only the problem, the user's own context, the frame's vantage, and this instruction:

   > You are a generator, not a critic. Under this frame, write 6 short, distinct ideas - one phrase or one sentence each. Do not evaluate, rank, or hedge. The three answers everyone gives first are banned; push past them. Output only a JSON array: `[{"text": "...", "rationale": "..."}]`.

3. **Isolation is the method.** Do not run branches one after another in your own context, and never pass one branch's output to another - branches that see each other anchor on each other and collapse into one wider thought.
4. **Do not give the generators the b3sty rules.** Rules in the generator pull every branch back to the textbook answer. The rules belong to the critic in Phase 2, which is what keeps the final result safe.

### CFX frames

| Frame | Vantage | Tag |
|---|---|---|
| cheater with an executor | You run a Lua executor on your own client. You can trigger any net event with any arguments, POST to any NUI callback without the UI open, spawn and delete networked entities, and do it all in a loop. Break the obvious design every way you can, then turn each break into a design move. | security |
| OneSync entity owner | Think in network ownership. The entity's owner is some random client, ownership migrates mid-action, the entity is out of scope for the player who started the action, players sit in different routing buckets. What does the design assume about who owns what, and what if that flips? | sync |
| one server thread, every resource | Every resource shares one server thread and every client's bandwidth. Price the idea per tick and per client at full population. What disappears if you push instead of poll, batch, defer, or send deltas instead of snapshots? | perf |
| restart mid-action | The resource restarts, txAdmin restarts the server, or the player drops in the middle of the operation. What is left half-done, applied twice, or lost - and what design is safe to interrupt at any line? | lifecycle |
| owner who cannot read Lua | The person running this edits only config and `server.cfg`, starts resources in the wrong order, and runs a framework you did not test. What design still works, or fails loudly instead of silently? | ops |
| economy designer | Money and items flow through this. Every source can inflate, every transfer can dupe. Map sources, sinks, and transfers, then shape the flow so the totals always reconcile. | economy |
| RedM port | Ship the same feature on RDR3: different natives, some server-side reads unreliable, VORP or RSG instead of ESX or QBCore. Which assumptions are GTA-only, and what survives both games? | portability |
| bridge author | It must run unchanged on ESX, QBCore, and Qbox (and VORP or RSG on RedM). What is the smallest contract the core needs from a framework, and what moves behind the bridge? | design |

### General frames

| Frame | Vantage | Tag |
|---|---|---|
| inversion | Ask how to guarantee the opposite - a guaranteed dupe, guaranteed lag, a guaranteed desync - then negate each answer into a design move. | general |
| 3am on-call | You get woken when this breaks on a full server. What design lets you sleep: what is observable, what heals itself, what fails closed? | general |
| no budget, one hour | No new dependencies and one hour. What is the crudest version that still does the load-bearing thing? | general |
| remove the load-bearing assumption | Name what everyone treats as fixed here - one net event per action, the database, the framework, the client asking first - and remove it. What becomes possible? | wild |
| speedrunner | Find the skips: the abusive-but-legal shortcut through the engine, the framework, or the data model. | wild |
| biology | Transplant a mechanism from biology - immune response, quorum sensing, metabolism - and force-fit it onto the problem. | wild |
| logistics | Steal queues, batching, hub-and-spoke, just-in-time, and returns, and apply them literally. | wild |

Vary the picks between runs so a re-run explores different ground.

## 2. Focus - Critic With The Rules

Run this yourself after every branch returns, with the rule files below open.

1. **Score** each idea 0-10 on novelty (distance from the default), viability (could it ship on a live server), and fit (does it solve the stated problem).
2. **Trap gate.** An idea that needs any of these is a trap. Cite the rule; no novelty score rescues it:
   - A client-sent value or client-side check as the authority - price, amount, target id, identifier, coords, item name, "the client says it's done": `skills/common/security-performance.md` -> Server Authority, and Event Trust Boundary.
   - An NUI callback, an ox_target option, or a client menu as the permission check: `skills/common/nui.md` -> Security, and `skills/common/ox-ecosystem.md`.
   - `GetInvokingResource()` or a client-set flag as the gate on a client-callable event: `skills/common/multi-resource.md`.
   - Granting value without a capacity check, an atomic write, or replay protection: `skills/common/security-performance.md` -> Atomic State Changes And Replay Protection, and Give-Value Event Hardening.
   - SQL built by string concatenation: `skills/common/database.md` -> SQL Injection.
   - `Wait(0)` polling where an event, a state bag, or a zone would do: `skills/common/security-performance.md` -> Performance Rules.
   - Large payloads to `-1`, events per tick, or every client pulling a full snapshot on join: `skills/common/network-performance.md` -> Snapshot Then Deltas, and Audience.
   - A webhook, token, or key in a client or shared file: `skills/common/security-performance.md` -> Config, Convars, And Secrets.
   - Saving in `onResourceStop`, or yielding there: `skills/common/runtime.md` -> Resource Lifecycle, and `skills/common/operations.md` -> Save Before The Restart, Not After.
   - `load()` of fetched code, writing outside the resource, or an unsafe sandbox grant: `skills/common/security-performance.md` -> The Resource Sandbox.
   - General traps: premature abstraction, a cache with no owner or cleanup path, splitting into extra resources with no consumer that needs it (`skills/common/multi-resource.md`).

   **Repair before you discard.** When an idea's core is good and only the enforcement point is wrong - "the client checks the trade" becomes "the client predicts for UX, the server decides" - list the trap, then score the repaired version as its own candidate.
3. **Cluster** the survivors into 3-6 groups by underlying angle, not shared keywords ("push-not-poll plays", "escrow-the-value plays", "make the server own the entity plays").
4. **Deepen the top 3** by weighted score (novelty 0.35, viability 0.40, fit 0.25), traps excluded. Spawn 3 parallel Agent calls, one per idea, each with the idea and the rule files the critic cited for it. Each returns:
   - a 4-8 sentence sketch at CFX level: which side owns what, which events, exports, state bags, and tables;
   - the load-bearing risk;
   - the first concrete step (a file, an event, a schema change);
   - the b3sty rules it must satisfy, as paths;
   - 3-5 child ideas: variations, hybrids, or what it unlocks.

## 3. Output

Keep this structure - it is the point; do not flatten it into prose.

```text
Brief: the problem in one or two lines, and any reframe used.

Wide set (by cluster, each labeled by its angle)
    - idea  [N7 V8 F9]

Converge: 2-4 picks with the reason for each.
    ★ marks the non-obvious pick that is still viable.
    Each pick lists the b3sty rules it relies on.

Traps: each with the one-line reason and the rule it breaks
    (repaired versions, if any, appear under Converge or the Wide set).

Focus: the 3 deepened ideas - sketch, load-bearing risk, first step, rules, child ideas.

Provocation: one question or wildcard that opens a new direction if nothing landed.
```

Then commit to a recommendation. "Here are 30 ideas, you choose" is not an answer. When the user picks one, build it under the normal rules (`commands/b3sty-new-resource.md` for a new resource) and run `/b3sty-review` before it ships.

## Anti-Patterns

- **Decorated convergence.** Ten variations of one idea is not breadth; if every candidate shares the same assumption, you have not diverged.
- **Weirdness with no landing.** A pile of unsorted absurdities is as useless as one safe answer. Always converge.
- **Fake parallelism.** Writing the branches one after another in your own context is one wider thought, not this method.
- **Rules in the generator, or novelty past the gate.** The first kills breadth; the second ships an exploit. Generators get no rules; the critic gets all of them.
- **Ideating where a rule already answers.** That is a lookup with extra steps. Point to the rule.

## Calibration And Cost

- Scale to the stakes: naming an export is 3 frames × 4 ideas; a system design is the default 5 × 6; a whole-server architecture may justify 6 × 8.
- Stop diverging when new ideas repeat the shape of existing ones; do not pad to a number.
- One run is about 5 generator calls, the critic pass, and 3 deepen calls - roughly 5-10× a direct answer. Every branch reloads its own context, so keep each generator prompt to the problem and the frame.
