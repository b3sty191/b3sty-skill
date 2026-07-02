# Native Reference Sources

Generated native references are kept here for lookup. They should be searched with `rg` and regenerated from their upstream/source data instead of edited by hand.

## `fivem-gta5-natives.md`

- Scope: GTA V / FiveM native reference.
- Current file: `references/natives/fivem-gta5-natives.md`
- Previous filename: `NATIVES_GTA5.md`
- Declared source in file header: `https://github.com/citizenfx/natives` branch `main` and `https://docs.fivem.net/natives/`
- Content note: the file header says the per-native documentation is taken verbatim from the source repo.
- License note: GitHub's repository license API returned no license file for `citizenfx/natives` during the 2026-07-02 pre-publication check. Do not assume this repository's MIT license covers this generated reference.

## `redm-rdr3-natives.md`

- Scope: RDR3 / RedM native reference.
- Current file: `references/natives/redm-rdr3-natives.md`
- Previous filename: `REDM_NATIVES.md`
- Declared source in file header: local/generated `index/natives_enriched.json` via `build_single_doc.py`
- Content note: entries include generated analysis plus references to community resources such as alloc8or RDR3 docs, femga/rdr3_discoveries, and Halen84 RDR3 native flags/enums.
- License note: the exact upstream license for the generated source data was not confirmed during the 2026-07-02 pre-publication check. Do not assume this repository's MIT license covers this generated reference.

## Publication Policy

- Keep source attribution with generated native references.
- Do not copy large native reference content into `skills/` or `memory/`.
- If upstream redistribution terms cannot be confirmed, remove generated native reference files from public packages and keep only source/regeneration instructions.
