# FXServer Native Components

Rules for native C++ server components added to an official FXServer artifact through `components.json`: portability, artifact/build pinning, and never replacing the stock `citizen-server-impl`.

## Installing A Component

- A component is `lib<name>.so` plus `lib<name>.json` next to the `FXServer`
  binary (Windows: a DLL with the component JSON embedded), with its id appended
  to the artifact's `components.json`. Removing that line uninstalls it.
- Components are loaded only at process boot - neither a resource restart nor a
  txAdmin Restart picks up a new or changed one.
- Never ship a rebuilt `libcitizen-server-impl.so`. The official one contains
  private escrow code, and the license-key callback asserts without it, so any
  impl built from public source kills the server at the license check
  (verified: boot crash bisected and disassembled on artifact 35945).

## Portability And Build Pins

- Build from the artifact's exact upstream commit - it is in the artifact
  download URL. Anything else is a guess about layouts you cannot see.
- Exported-symbol mismatches fail loudly at `dlopen` ("symbol not found"), for
  example a component linked against a fork-only `http-client` overload loaded
  into an official artifact. Inlined class layouts fail silently: 37850 inserted
  a field into `ResourceEventManagerComponent`, so a component compiled against
  35945 headers corrupts memory on 37850.
- Pin the GNU build-id (`readelf -n`) or PDB GUID + age of every library whose
  headers you inline, check them at load, and refuse to initialise on a
  mismatch. Accept a pin profile only as a whole set, never library by library,
  and re-pin on every artifact update (verified: between 37850 and 37872 only
  `libcitizen-server-impl.so` changed id).
- A component that patches bytes must require each search pattern to match
  exactly once and write a byte only if it still holds the expected value -
  compiler output differs between builds of the same source.
