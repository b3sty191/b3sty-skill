# b3sty-skill Agent Guide

This repository stores reusable rules and working memory for b3sty RedM/FiveM Lua development.

`SKILL.md` is the single source of truth for trigger scope, core defaults, and load guidance. Start there - it tells you which file to open for which task.

The rest of the repo:

- `skills/common/` - stable rules shared by RedM and FiveM.
- `skills/fivem/` - FiveM-only rules.
- `skills/redm/` - RedM-only rules.
- `memory/common/` - learned facts shared by RedM and FiveM.
- `memory/fivem/` - FiveM-only learned facts.
- `memory/redm/` - RedM-only learned facts.
- `references/natives/` - generated native lookup files for FiveM/GTA V and RedM/RDR3.

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

- `agents/openai.yaml` - OpenAI Codex agent configuration; points Codex to `SKILL.md` and `AGENTS.md`.
