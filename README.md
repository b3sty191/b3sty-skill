# b3sty-skill

[![skills.sh](https://skills.sh/b/b3sty191/b3sty-skill)](https://skills.sh/b3sty191/b3sty-skill)

Reusable rules and working memory for b3sty RedM/FiveM Lua development.

## Install

Ask Codex to install this skill from GitHub:

```text
Use $skill-installer to install from repo b3sty191/b3sty-skill path . with name b3sty-skill
```

Then restart Codex so the new skill is loaded.

After restart, use it by asking Codex to work on b3sty RedM/FiveM Lua resources, or invoke it explicitly:

```text
Use $b3sty-skill to implement or review this FiveM resource for server authority, events, natives, persistence, cleanup, and performance.
```

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
- `skills/common/security-performance.md` - server validation, anti-spam, optimization, persistence, and cleanup rules.
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

- `agents/openai.yaml` - OpenAI Codex agent configuration; points Codex to `SKILL.md` and `AGENTS.md`.

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
