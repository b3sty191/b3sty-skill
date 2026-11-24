# Server Hardening And Secrets

Operator-level rules around the resource rules: secrets and convar exposure, `server.cfg` hardening, txAdmin and database access, HTTP handlers, the resource sandbox, third-party vetting. Core event-security rules and the index of every section named "above"/"below": `skills/common/security-performance.md` -> Contents.

## Config, Convars, And Secrets

- Shared and client config is public data: clients read `config.lua`, `ui_page` bundles, state bags, networked tables. No webhook URLs, API keys, DB connection strings, admin secrets, or hidden reward logic there.
- Convar exposure by command ([convars reference](https://docs.fivem.net/docs/scripting-reference/convars/)):
  - `set name value` - standard convar, server-side only; clients cannot read it.
  - `setr name value` - server replicated; readable by clients via `GetConvar`, changeable only server-side. Anything in `setr` is public to clients.
  - `sets name "value"` - server information; exposed publicly in `info.json` and the server list. Never use `sets` for anything sensitive.
- Secrets (DB strings, tokens, webhooks) live in server-only `set` convars (or env), read once with `GetConvar`/`GetConvarInt` - never `setr`/`sets`/shared/client files. See `skills/common/runtime.md` -> Convars.
- `set` hides a convar from clients, not from resources: server-side `GetConvar` returns any plain `set` convar (DB string, webhook, API key) to every resource unless the engine flagged it `ScriptRestricted`. For a credential only one resource needs, make reads opt-in with `add_convar_permission <resource> read <convar>` - accepted only in the startup cfg, rejected once startup has finished. (verified: ConsoleScriptFunctions.cpp)
- Authoritative prices, rewards, drop rates, permission gates, and item mutation rules stay in server config, or are validated again server-side.
- Validate server events and exports even when they are meant for another local resource: running on the same server is not trust. For cross-resource APIs prefer explicit exports with narrow params over generic event payloads that can trigger arbitrary behavior.

## Logging And Secrets

- Log rejected security-sensitive actions with enough context to debug, but never secrets: redact fields whose names include `password`, `secret`, `token`, `apikey`, `authorization`, `bearer`, `cookie`, `webhook`, or `licensekey`.
- Bound log payload depth, string length, item count, and key count.
- Queue and batch logs instead of one request per event; cap the queue and drop or compact safely when it grows too large.
- Real tokens and webhook keys live in server-only `set` convars (not `setr`/`sets`), never in client/shared files. See Config, Convars, And Secrets above.

## Server Hardening And Operations

Resource-level validation cannot compensate for a soft server platform. These are `server.cfg`/operator-level controls; they complement, never replace, the per-event rules above. Copyable baseline: `references/server.cfg.example`. ([Server Commands](https://docs.fivem.net/docs/server-manual/server-commands/))

### Convar checklist

- `sv_scriptHookAllowed 0` - keeps ScriptHook-style client plugins blocked (default off; never enable on a public server).
- `sv_pureLevel 1` (or `2`) - rejects clients running modified game files; `2` is strictest. Test against your player base before enforcing.
- `sv_requestParanoia 0..3` - counters proxy-based HTTP floods against the server's HTTP endpoints (1 blocks IPs sending a `Via` header; 2 also blocks browser-style requests with `Upgrade-Insecure-Requests`, and info/dynamic/players.json then answer "Nope."; 3 also closes the socket). Default 0. Start at 1 and check that server-list and monitoring tools still work before raising it.
- `sv_endpointPrivacy` - removed on current artifacts: FXServer ignores it (and warns if set) because player endpoint addresses are no longer exposed on any HTTP endpoint. On old artifacts it only hid player IPs in the public HTTP reports (`players.json`), not from other clients; the real fix there is updating the artifact (see Operator access).
- `rcon_password` unset (rcon disabled) unless genuinely needed; if used, a long unique password never reused anywhere.
- OneSync - required for the server-side entity gates used above (`entityCreating`, ownership, routing buckets). Artifacts built from 2026-08-17 force it on (`onesync` became an internal convar, citizenfx/fivem `19fa3d5`); keep `set onesync on` for older artifacts.
- Verify the convars covered elsewhere in this file are actually set: `setr sv_stateBagStrictMode true` (Sync Safety), `sv_filterRequestControl` (Built-in Client Events / `skills/common/networking.md` -> Entity Ownership), `sv_enableNetworkedPhoneExplosions`/`sv_enableNetworkedSounds`/`sv_enableNetworkedScriptEntityStates` (Built-in Client Events), `sv_authMaxVariance` (Identifier Trust; `sv_authMinTrust` is effectively a no-op).
- `sv_prometheusBasicAuthUser` + `sv_prometheusBasicAuthPassword` - set both (password in `secrets.cfg`) or the stock `/perf` endpoint serves Prometheus tick/thread timings to anyone on the game HTTP port, limited only by a per-IP limiter (2/s, burst 5). With both set it answers 401. (verified: PerfHttpHandler.cpp, FXServer 35945; 401/200 checked live)

### Operator access

- Run a recent FXServer artifact; old ones carry known, already-patched security issues.
- txAdmin port (default `40120`): firewall to admin IPs, strong unique password, keep txAdmin updated - never open it to the whole internet.
- Keep `server.cfg` out of public git - it holds the license key, DB string, and admin identifiers. Commit a placeholder `server.cfg.example` and `exec` a `.gitignore`d `secrets.cfg` for real values. A committed secret is compromised the moment it is pushed: rotate first, then purge history.
- A tool that forwards console commands (admin panel, Discord bot, MCP server) is a remote root shell: one command per call (reject `;`, `\r`, `\n` - the console splits on them), a block list (`quit`, `exec`, `add_ace`, `add_principal`, `set`, ...) and a protected-resource list for `start`/`stop`/`restart`/`ensure`. Check `IsPrincipalAceAllowed('resource.<name>', 'command.<cmd>')` before running - false for nonexistent commands too - and capture the console output, treating `Access denied`/`No such command` as failure. (verified live on FXServer)
- Cap money and items per call; audit refused calls as well as successful ones.
- Give it a SELECT-only DB user, run reads in a `READ ONLY` transaction with a timeout and row cap, and bind its HTTP handler to localhost behind a token.

### HTTP handlers

- `SetHttpHandler` publishes an unauthenticated, internet-reachable endpoint on the server's public port (`http://host:30120/<resource>/...`). Harden it exactly like a public net event: allowlist method + path, bound body size before parsing, require a server-held token for anything privileged, rate-limit per caller, 404 everything else.
- No stack traces, file paths, or config values in HTTP error responses.
- Each endpoint also sits behind a per-IP limiter (`http_<resource>`; numbers in `skills/common/network-performance.md` -> Rate Limits) that blunts floods only - it is not authentication.
- Prefer not exposing HTTP at all when events/exports can carry the traffic.

### Database and supply chain

- Game database: a dedicated MySQL user with grants limited to the game schema (no `SUPER`/`FILE`/`GRANT`, never root), reachable only from the server host or a private network.
- Third-party resources are untrusted code about to run with full server trust. Red flags: obfuscated/encrypted Lua, `PerformHttpRequest` to unknown domains, remote loaders (`load(...)`/`assert(load(...))` on fetched strings), `os.execute`/`io.popen` on the server, giant base64 blobs. "Leaked"/cracked scripts are a known backdoor vector - do not run them.
- Prefer resources whose source you can read; code that must hide itself is a risk signal on a server you own.

### The Resource Sandbox

FXServer runs resource Lua in a sandbox, so some "red flag" calls cannot do what they look like - which changes what to worry about when auditing a resource. ([Sandbox](https://docs.fivem.net/docs/developers/sandbox/))

- Blocked by default: `os.execute` (all commands), `io.tmpfile()`, `io.popen` (only emulated `ls`/`dir`). `SaveResourceFile` writes only inside the calling resource - `..` traversal and symlinks rejected - so a plain `os.execute` on the server is refused unless a grant opened it.
- `load()` is **not** blocked. A resource that `load()`s a string fetched over HTTP is a live backdoor even inside the sandbox; that, not a blocked `os.execute`, is the real remote-code red flag (see the red-flags list above).
- `server.cfg` grants widen the sandbox and are what to audit before adding a resource that ships them: `add_filesystem_permission A write B` (write into another resource), `add_convar_permission A read <convar>` (read a convar once reads are opt-in), `add_unsafe_worker_permission`, `add_unsafe_child_process_permission` - child processes escape the sandbox entirely. Treat an unexplained unsafe grant like obfuscated code.
- For persistence, write inside the resource or go to the database (`skills/common/database.md`); do not expect to write elsewhere on disk.
