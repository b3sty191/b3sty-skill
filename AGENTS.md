# b3sty-skill Agent Guide

Reusable rules and working memory for b3sty RedM/FiveM Lua development.

`SKILL.md` is the single source of truth: trigger scope, modes, workflow, core defaults, and which file to open for which task. Start there. There are no slash commands - the user asks in plain words and `SKILL.md` routes the request.

The rest of the repo:

- `modes/` - one file per workflow, loaded when the request matches: review/audit, new resource, performance, ideation.
- `skills/common/` - stable rules shared by RedM and FiveM; `skills/fivem/`, `skills/redm/` - game-only rules.
- `memory/common/` - learned facts shared by both games; `memory/fivem/`, `memory/redm/` - game-only learned facts.
- `evals/` - planted-bug resource fixtures and `score.py`, which benchmark review mode's recall and false positives on decoys.
- `trigger-evals/` - `claude plugin eval` cases checking the skill loads for RedM/FiveM work and stays out of everything else.
- `references/natives/` - generated native lookup files for FiveM/GTA V and RedM/RDR3.
- `scripts/` - package validators plus the audit ledger and findings checkers.

## Working Rules

- Prefer existing project patterns before adding new abstractions.
- Keep changes small, direct, and easy to review.
- Record recurring fixes or patterns in the right `memory/` namespace (include date and game build).
- Keep `skills/` focused on rules reused across projects; keep `memory/` focused on learned facts, cross-linking to `skills/` instead of duplicating rule text.
- Keep large generated reference files in `references/`; do not duplicate their content into `skills/` or `memory/`.
- Run `scripts/validate_b3sty_skill.py` and the `skill-creator` `quick_validate.py` check before publishing changes.

## Communication

- Be direct and practical.
- Explain tradeoffs only when they affect the implementation.
- Mention verification steps and any remaining risks.

## Agent Configs

- `agents/openai.yaml` - OpenAI Codex skill UI metadata (display name, short description, default prompt); Codex loads the skill itself from `SKILL.md`.
- `.claude-plugin/marketplace.json` - Claude Code plugin manifest; `skills.sh.json` - skills.sh grouping.
