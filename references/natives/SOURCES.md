# Native Reference Sources

Generated native references are kept here for lookup. They should be searched with `rg` and regenerated from their upstream/source data instead of edited by hand.

## `fivem-gta5-natives.md`

- Scope: GTA V / FiveM native reference.
- Current file: `references/natives/fivem-gta5-natives.md`
- Previous filename: `NATIVES_GTA5.md`
- Declared source in file header: `https://github.com/citizenfx/natives` branch `main` and `https://docs.fivem.net/natives/`
- Content note: the file header says the per-native documentation is taken verbatim from the source repo.
- License note: GitHub's repository license API returned no license file for `citizenfx/natives` during the 2026-07-02 pre-publication check (re-checked 2026-11-20, still none). Do not assume this repository's MIT license covers this generated reference.
- Regenerate with `build_natives_doc.py` (pure standard library, no network of its own):
  ```bash
  git clone --depth 1 https://github.com/citizenfx/natives /tmp/cfx-natives
  python3 -I references/natives/build_natives_doc.py /tmp/cfx-natives \
      -o references/natives/fivem-gta5-natives.md
  ```
  The script rebuilds the single-file reference from the upstream per-native
  markdown; `--selftest` runs its parser/emit fixtures. The committed
  `fivem-gta5-natives.md` is this script's output as of 2026-11-20 (6437
  natives, 44 namespaces), so a re-run against a fresh clone produces a clean,
  minimal diff limited to genuine upstream churn. The script resolves the real
  return type and parameter types through CFX `cs_type(...)` marshalling hints
  (e.g. `cs_type(int) BOOL FOO()` returns `BOOL`), takes the name from an empty
  `##` heading's signature, and drops empty sections.
  Because upstream ships no confirmed redistribution terms (above), the
  Publication Policy below governs whether the regenerated file stays in a
  public package; the committed file predates this script and is kept current
  with it.

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
