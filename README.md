# b3sty-skill

[![skills.sh](https://skills.sh/b/b3sty191/b3sty-skill)](https://skills.sh/b3sty191/b3sty-skill)

A skill that makes your AI assistant write, review, debug, and speed up RedM/FiveM Lua resources the way an experienced FXServer developer would.

What each update changes: [CHANGELOG.md](CHANGELOG.md).

## Install

**Claude Code plugin** (easiest) - run these two commands inside Claude Code:

```text
/plugin marketplace add b3sty191/b3sty-skill
/plugin install b3sty-skill@b3sty
```

**skills.sh** - from any terminal:

```bash
npx skills add b3sty191/b3sty-skill --skill b3sty-skill
```

**OpenAI Codex** - ask Codex: `Use $skill-installer to install from repo b3sty191/b3sty-skill path . with name b3sty-skill`, restart it, then invoke `$b3sty-skill`.

**Git clone** (any agent that reads skill folders) - clone into your skills directory, e.g. `git clone https://github.com/b3sty191/b3sty-skill.git ~/.claude/skills/b3sty-skill`, then restart the agent. Clone rather than copy: a copy goes stale silently and misses security fixes. If the repo is private, the install needs GitHub credentials or `GITHUB_TOKEN` / `GH_TOKEN`.

## Use

No commands to remember. Ask in plain words and the skill triggers itself, picking the right mode for the request:

```text
Review this resource before I put it on my server
Make me a shop script with a NUI menu and ESX money
Why does my server drop to 20 FPS near the market?
Give me ideas for a bounty-hunter job in RedM
Fix this error: attempt to index a nil value (local 'xPlayer')
```

## What's inside

| Path | What it is |
|---|---|
| `SKILL.md` | entry point: triggers, workflow, core defaults, and which file to open per task |
| `modes/` | one file per workflow - review/audit, new resource, performance, ideation |
| `skills/` | the stable rules: common, plus FiveM-only and RedM-only |
| `memory/` | learned facts with date and game build (native bugs, errors, patterns) |
| `references/` | generated native dumps, `server.cfg.example`, the audit findings schema |
| `scripts/` | package validators and the audit ledger/findings checkers |
| `evals/` | planted-bug resources and a scorer that measure the auditor's recall |

## Updating

```bash
npx skills update                      # skills.sh install
git -C ~/.claude/skills/b3sty-skill pull   # git clone install
```

Plugin installs update from the `/plugin` menu in Claude Code.

## Maintenance

Before publishing changes:

```bash
python scripts/validate_b3sty_skill.py
python scripts/check_lua_examples.py
python scripts/b3sty_audit_ledger.py --selftest
python scripts/validate_audit_findings.py --selftest
python <skill-creator>/scripts/quick_validate.py .
```

`<skill-creator>` is your local skill-creator install (Codex on Windows: `%USERPROFILE%\.codex\skills\.system\skill-creator`).

To measure review quality, audit an eval case in review mode and score the findings: `python3 evals/score.py --expectations evals/EXPECTATIONS.json --case fivem_shop --findings <out>/findings.json`. See `evals/README.md`.

## License

Original b3sty skill rules, memory notes, and packaging metadata are MIT licensed. Generated native references keep their upstream terms; see [NOTICE.md](NOTICE.md) and `references/natives/SOURCES.md`.
