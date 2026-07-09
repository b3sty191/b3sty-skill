# b3sty-skill

[![skills.sh](https://skills.sh/b/b3sty191/b3sty-skill)](https://skills.sh/b3sty191/b3sty-skill)

Reusable rules and working memory for b3sty RedM/FiveM Lua development.

## Install

`SKILL.md` is the skill manifest. It works as a first-class skill in **Claude Code**, **OpenAI Codex**, and on **skills.sh**. Pick your platform.

### Claude Code - plugin (easiest)

Run these two commands inside Claude Code:

```text
/plugin marketplace add b3sty191/b3sty-skill
/plugin install b3sty-skill@b3sty
```

Done - the skill auto-triggers on RedM/FiveM Lua work. Manage or update it later from the `/plugin` menu.

### Claude Code - git clone

Clone straight into a skills directory (personal, all projects):

```bash
# macOS / Linux
git clone https://github.com/b3sty191/b3sty-skill.git ~/.claude/skills/b3sty-skill

# Windows (PowerShell)
git clone https://github.com/b3sty191/b3sty-skill.git "$env:USERPROFILE\.claude\skills\b3sty-skill"

# project-local (this project only)
git clone https://github.com/b3sty191/b3sty-skill.git .claude/skills/b3sty-skill
```

Restart Claude Code (or open a new session) so the skill is loaded. Update any time with:

```bash
git -C ~/.claude/skills/b3sty-skill pull
```

Clone rather than copy: a copied snapshot goes stale silently and misses security fixes, while a clone updates with one `git pull`.

Use it by asking Claude Code to work on b3sty RedM/FiveM Lua resources (it auto-triggers from the description), or invoke it directly:

```text
Use the b3sty-skill skill to implement or review this FiveM resource for server authority, events, natives, persistence, cleanup, and performance.
```

### OpenAI Codex

Ask Codex to install this skill from GitHub:

```text
Use $skill-installer to install from repo b3sty191/b3sty-skill path . with name b3sty-skill
```

Then restart Codex so the new skill is loaded, and invoke it with `$b3sty-skill`.

### Private Repo Install

If this repository is private, the installer needs existing GitHub credentials or `GITHUB_TOKEN` / `GH_TOKEN` with access to the repo. Public installs do not need a token.

## Structure

- `SKILL.md` - skill entry point: trigger metadata, core defaults, and load guidance.
- `AGENTS.md` - agent-facing overview; points to `SKILL.md`.
- `skills/common/` - stable rules shared by RedM and FiveM.
- `skills/fivem/` - FiveM-only rules and compatibility guidance.
- `skills/redm/` - RedM-only rules and compatibility guidance.
- `memory/common/` - learned facts shared by RedM and FiveM.
- `memory/fivem/` - FiveM-only learned facts.
- `memory/redm/` - RedM-only learned facts.
- `references/natives/` - large generated native reference files.

## Common Skills

- `skills/common/style.md` - coding and communication style.
- `skills/common/fxserver.md` - FXServer resource and manifest rules.
- `skills/common/native-rules.md` - native call policy: safety, caching, wrappers.
- `skills/common/native-usage.md` - calling natives from Lua: doc-entry translation, `Citizen.InvokeNative`, marshalling, RDR3 struct natives, build gates.
- `skills/common/resource-structure.md` - shared resource structure, events, state, and cleanup shape.
- `skills/common/networking.md` - OneSync, net IDs vs handles, entity ownership, routing buckets, scoped vs broadcast messages, player scope, entity lifecycle events, and built-in client events.
- `skills/common/nui.md` - in-game browser UI (NUI): Lua<->browser bridge, focus, JSON contracts, validation, frontend hygiene, performance, and security.
- `skills/common/runtime.md` - threads/waits, the `source` variable, exports and stale references, identifiers, convars, resource lifecycle, yield hazards, and game builds.
- `skills/common/security-performance.md` - client-hostile/server-authoritative security: event trust boundary, give-value (give-item/give-money) hardening, ACE permissions, built-in client event exploits, SQL injection, secrets/convars, identifier trust, throttles, persistence, cleanup, and the security review checklist.
- `skills/common/database.md` - SQL, OxMySQL/mysql-async, migrations, transactions, and persistence rules.
- `skills/common/debugging.md` - reproducible debugging flow for resource, native, NUI, DB, and performance failures.
- `skills/common/ox-lib.md` - ox_lib usage rules when the project already depends on ox_lib or explicitly accepts it.
- `skills/common/multi-resource.md` - exports, dependencies, state bags, convars, shared scripts, and cross-resource contracts.

## Game-Specific Skills

- `skills/fivem/rules.md` - FiveM-only defaults and compatibility checks.
- `skills/redm/rules.md` - RedM-only defaults and compatibility checks.

## Native References

- `references/natives/fivem-gta5-natives.md` - GTA V / FiveM native reference. Formerly `NATIVES_GTA5.md`.
- `references/natives/redm-rdr3-natives.md` - RDR3 / RedM native reference. Formerly `REDM_NATIVES.md`.
- `references/natives/SOURCES.md` - source attribution and publication notes for generated native references.

These files are generated lookup references and are intentionally kept outside `skills/` and `memory/`.

## Agent Configs

- **Claude Code** - uses `SKILL.md` directly as the skill manifest (frontmatter `name` + `description`); no separate config file.
- `.claude-plugin/marketplace.json` - Claude Code plugin marketplace manifest for `/plugin` install.
- `agents/openai.yaml` - OpenAI Codex agent configuration; points Codex to `SKILL.md` and `AGENTS.md`.
- `skills.sh.json` - skills.sh grouping/visibility.

## Maintenance

Run the package checks before publishing changes:

```powershell
python scripts/validate_b3sty_skill.py
python C:\Users\b3sty191\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
```

## License

Original b3sty skill rules, memory notes, and packaging metadata are MIT licensed. Generated native references keep their upstream terms; see `NOTICE.md` and `references/natives/SOURCES.md`.

## Memory

- `memory/common/common-errors.md` - common shared errors and fixes.
- `memory/common/native-bugs.md` - known shared native issues and workarounds.
- `memory/common/cfx-patterns.md` - reusable shared FXServer/CfxLua patterns.
- `memory/common/security-performance.md` - learned shared security and performance patterns.
- `memory/fivem/README.md` - FiveM-specific memory namespace.
- `memory/fivem/native-bugs.md` - FiveM-only native issues and workarounds.
- `memory/redm/README.md` - RedM-specific memory namespace.
- `memory/redm/native-bugs.md` - RedM-only native issues and workarounds.

`skills/` holds stable rules; `memory/` holds learned facts with date and game build; `references/` holds large generated source material. See `SKILL.md` for which file to open for each task.
