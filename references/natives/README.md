# Native References

Generated single-file native lookup documents.

## Files

- `fivem-gta5-natives.md` - GTA V / FiveM native reference. Formerly `NATIVES_GTA5.md`.
- `redm-rdr3-natives.md` - RDR3 / RedM native reference. Formerly `REDM_NATIVES.md`.
- `SOURCES.md` - source attribution, license notes, and publication policy for generated native references.

## Usage

- Search only the matching file for the target game.
- Use these files to verify native names, hashes, signatures, namespaces, parameters, return values, and behavior notes.
- Use `skills/common/native-usage.md` for how to turn an entry into a Lua call (name conversion, `Citizen.InvokeNative`, marshalling, struct natives) and for `rg` search recipes.
- Do not copy large native reference content into `skills/` or `memory/`.
- Record recurring bugs or workarounds in `memory/common/native-bugs.md`, `memory/fivem/`, or `memory/redm/` instead.
- Check `SOURCES.md` before publishing packages that redistribute the generated reference files.
