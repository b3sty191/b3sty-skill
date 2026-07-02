# b3sty-skill

Reusable rules and working memory for b3sty RedM/FiveM Lua development.

## Install

Ask Codex to install this skill from GitHub:

```text
Use $skill-installer to install from repo b3sty191/b3sty-skill path . with name b3sty-skill
```

Then restart Codex so the new skill is loaded.

After restart, use it by asking Codex to work on b3sty RedM/FiveM Lua resources, or invoke it explicitly:

```text
Use $b3sty-skill to review this FiveM resource for event naming, server validation, natives, and performance.
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
- `skills/common/native-rules.md` - native call usage rules.
- `skills/common/resource-structure.md` - shared resource structure, events, state, and cleanup shape.
- `skills/common/security-performance.md` - server validation, anti-spam, optimization, persistence, and cleanup rules.

## Game-Specific Skills

- `skills/fivem/rules.md` - FiveM-only defaults and compatibility checks.
- `skills/redm/rules.md` - RedM-only defaults and compatibility checks.

## Native References

- `references/natives/fivem-gta5-natives.md` - GTA V / FiveM native reference. Formerly `NATIVES_GTA5.md`.
- `references/natives/redm-rdr3-natives.md` - RDR3 / RedM native reference. Formerly `REDM_NATIVES.md`.
- `references/natives/SOURCES.md` - source attribution and publication notes for generated native references.

These files are generated lookup references and are intentionally kept outside `skills/` and `memory/`.

## License

Original b3sty skill rules, memory notes, and packaging metadata are MIT licensed. Generated native references keep their upstream terms; see `NOTICE.md` and `references/natives/SOURCES.md`.

## Memory

- `memory/common/common-errors.md` - common shared errors and fixes.
- `memory/common/native-bugs.md` - known shared native issues and workarounds.
- `memory/common/cfx-patterns.md` - reusable shared FXServer/CfxLua patterns.
- `memory/common/security-performance.md` - learned shared security and performance patterns.
- `memory/fivem/README.md` - FiveM-specific memory namespace.
- `memory/redm/README.md` - RedM-specific memory namespace.

`skills/` holds stable rules; `memory/` holds learned facts with date and game build; `references/` holds large generated source material. See `SKILL.md` for which file to open for each task.
