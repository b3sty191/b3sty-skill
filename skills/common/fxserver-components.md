# FXServer Native Components

Rules for native C++ server components added to an official FXServer artifact through `components.json`: portability, artifact/build pinning, and never replacing the stock `citizen-server-impl`.

## Installing A Component

- A component is `lib<name>.so` plus `lib<name>.json` next to the `FXServer` binary (Windows: a DLL with the component JSON embedded), with its id appended to the artifact's `components.json`. Removing that line uninstalls it.
- Components load only at process boot - neither a resource restart nor a txAdmin Restart picks up a new or changed one.
- Never ship a rebuilt `libcitizen-server-impl.so`: the official one contains private escrow code and the license-key callback asserts without it, so any impl built from public source kills the server at the license check (verified: boot crash bisected and disassembled on artifact 35945).

## Portability And Build Pins

- Build from the artifact's exact upstream commit - it is in the artifact download URL. Anything else guesses at layouts you cannot see.
- Exported-symbol mismatches fail loudly at `dlopen` ("symbol not found"), for example a component linked against a fork-only `http-client` overload loaded into an official artifact. Inlined class layouts fail silently: 37850 inserted a field into `ResourceEventManagerComponent`, so a component compiled against 35945 headers corrupts memory on 37850.
- Pin the GNU build-id (`readelf -n`) or PDB GUID + age of every library whose headers you inline, check them at load, and refuse to initialise on a mismatch. Accept a pin profile only as a whole set, never library by library, and re-pin on every artifact update (verified: between 37850 and 37872 only `libcitizen-server-impl.so` changed id).
- A component that patches bytes must require each search pattern to match exactly once and write a byte only if it still holds the expected value - compiler output differs between builds of the same source.

## Hooks And Process Lifecycle

Verified on artifact 38781 (2026-11-26) unless noted; line numbers are citizenfx/fivem `8cbec36a`.

- The txAdmin host is an FXServer too: it loads every component in `components.json` and starts its own `monitor` resource, but never fires `fx::ServerInstanceBase::OnServerCreate` (only `citizen-server-main/src/ServerInstance.cpp` does). Anything a component creates there - convars, pointers, the root path - is still null in the host process, so every `fx::Resource` / `ResourceManager` hook must check it before use. Missing that check crashed the host in `luv_svMain` before the first log line, so the whole server stayed down (a convar dereferenced in a resource `OnStart` handler).
- `fwEvent` runs handlers in ascending `order` (`client/shared/EventCore.h:341`); a handler returning `false` stops the chain. `ServerResources` scans `resources/` inside its own `OnServerCreate` handler at order 50 (`ServerResources.cpp:653`, `:848`), so a component at a lower order can add or move resource folders that this boot's scan picks up, with no `refresh`.
- On a server without a licence key the licence component stops the `OnServerCreate` chain (it sits between order 100 and 1000) and no resource ever starts. A keyless boot test therefore proves only that the component loads and its guard matches; start hooks, later `OnServerCreate` handlers and console commands need a keyed test server.
- `fx::Resource::OnBeforeStart` handlers returning `false` cancel the start and put the resource back to Stopped (`Resource.cpp:92`) - the hook for a pre-start gate. Order it below the dependency loader's handler (default order) to run before dependencies are started.
- Manifest metadata: `dependencies { ... }` entries are stored under the key `dependencie` (`resource_init.lua` drops one trailing `s` from table-form keys), `dependency 'x'` under `dependency`; read both, as `ResourceDependencyLoader.cpp:88` does. Plural script keys (`server_scripts`) do land under the singular key.
- Export calls reach the dispatcher as the event `__cfx_export_<resource>_<name>` only on a consumer's first access - `scheduler.lua` caches the function. Inside `ResourceEventManagerComponent::OnTriggerEvent`, `fx::GetCurrentScriptRuntime` -> `GetParentObject()` is the calling resource (as `HttpScriptFunctions.cpp:74-76` does). JS runtimes do not push onto that stack, so JS callers are not attributable this way.
- The official `libcitizen-server-impl.so` is stripped and built with `-fvisibility=hidden`: only virtual calls and header inlines of its classes are usable, never non-virtual out-of-line members (`ServerGameState::GetEntity`, ...). A fork that edits impl headers (for example swapping a mutex type in `ServerGameState.h`) must build impl-coupled add-ons from the official commit's tree, not from the fork, because the impl that runs is the official one.
