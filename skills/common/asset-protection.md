# Asset Protection Rules

Use this file when a resource author wants to protect a resource they built and
sell or distribute - stop it from being leaked, cracked, or re-used on servers
that did not pay. This is about protecting **your own** work with the mechanisms
the FiveM/RedM ecosystem sanctions. It is not about hiding what a resource does
from the server owner who runs it, and it does not help anyone bypass another
author's protection.

The honest summary: the strongest protection is architectural (keep the value
server-side), the sanctioned packaging protection is CFX Asset Escrow, and
rolling your own Lua obfuscation is discouraged - it does not stop a determined
attacker, it breaks the server owner's ability to audit what they run, and in
this ecosystem a hand-obfuscated non-escrow resource reads as a backdoor.

## Server Authority Is The Real Protection

- The code worth stealing is the logic, and the logic belongs on the server. A
  client file that only renders UI and sends validated `:server:` events is
  worth little when leaked, because the decisions live where the attacker cannot
  read them. This is the same server-authority rule the skill already enforces
  for security (`skills/common/security-performance.md` -> Server Authority); it
  doubles as anti-leak design.
- Keep prices, rewards, drop tables, business rules, and anything you consider
  the "secret sauce" in server scripts, not shipped to clients.
- A leaked client bundle should let no one reconstruct the server behavior or
  run the resource without the entitlement.

## CFX Asset Escrow (the sanctioned mechanism)

Asset Escrow encrypts your resource server-side so other people cannot read or
modify the protected files, and it ties the resource to buyers through Tebex.
Confirm the current details against the official docs before relying on them;
the facts below are from CFX's Asset Escrow page and the resource-manifest
reference.

- **What it protects**: Escrow currently encrypts `Lua`, `YFT`, `YDD`, and `YDR`
  files. NUI (HTML/CSS/JS) is **not** covered - do not put a secret in NUI and
  assume escrow hides it.
- **How to create one**: zip the resource and upload it at CFX Portal
  (portal.cfx.re) as an asset; it is processed for encryption. Max asset size is
  1GB. Updates are a re-upload; distribution to buyers is through a Tebex
  package, and subscription access is supported (the asset is removed when the
  subscription lapses).
- **Entitlement**: an unauthorized server that tries to start the resource gets
  `You lack the required entitlement` and the resource does not start. The buyer
  must own it to run it.
- **Leave config and locale editable** with `escrow_ignore` in `fxmanifest.lua`
  so buyers can configure the resource without touching protected logic:
  ```lua
  escrow_ignore {
      'config.lua',
      'configs/*.lua',
      'locales/*.lua',
      'shared/config/**/*.lua',
  }
  ```
  Patterns support a single file, a folder glob (`stream/*.yft`), and a
  recursive glob (`stream/**/*.yft`). Manifest rules are in
  `skills/common/fxserver.md` -> fxmanifest.
- Escrow is a Portal/web upload step; there is no documented public API to
  automate the encryption or upload. CI can prepare the zip (strip dev files,
  run lint, check `escrow_ignore`), but the upload is manual.

## Do Not Roll Your Own Obfuscation

- CFX's own documentation states that obfuscating code in an escrowed resource
  is **not necessary** - escrow already encrypts the protected files. Adding a
  custom Lua obfuscator on top buys little.
- Against a determined attacker, source-level Lua obfuscation does not hold; it
  raises effort, not a real barrier.
- It has a real cost: the server owner who legitimately runs your resource can
  no longer read what it does. In this ecosystem that is exactly the shape of a
  backdoored or data-stealing resource, and good server owners refuse resources
  they cannot audit. `skills/common/server-hardening.md` -> Server Hardening And Operations
  covers vetting third-party resources from the buyer's side.
- So: protect the parts that must ship with escrow, keep the value on the
  server, and leave the shipped Lua readable. Do not inject decoy logic,
  anti-analysis traps, or opaque predicates into a resource other people run.

## Secret Hygiene

A leaked or cracked resource leaks whatever secrets you shipped inside it.

- Never ship API keys, webhook URLs, tokens, database strings, or license
  secrets inside the resource - not in client files, not in NUI, not even in
  escrowed Lua. Keep them in `server.cfg` / `secrets.cfg` convars read at
  runtime. See `skills/common/server-hardening.md` -> Config, Convars, And Secrets
  and `references/server.cfg.example`.
- NUI assets are not escrow-protected and ship in the clear; treat every value
  the browser can see as public.
- Before packaging, grep the build for obvious secret shapes (keys, bearer
  tokens, Discord webhook URLs) and move any hit server-side.

## Packaging Checklist

Before uploading a paid resource:

- The valuable logic runs server-side; the client only renders and sends
  validated events.
- `config.lua`, `configs/`, and locale files are in `escrow_ignore` so buyers
  can configure without cracking.
- No secret is shipped in any file (client, NUI, or escrowed Lua).
- Dev-only files are removed from the zip (tests, `.git`, editor configs,
  internal docs).
- The resource starts cleanly from the escrowed build, and a functional smoke
  test passes against it, not only against the unescrowed source.

## Review Questions

- Would a leaked client bundle let someone reconstruct the server logic or run
  the resource without the entitlement? If yes, move value server-side.
- Is anything secret shipped in a file the buyer or a leaker can read?
- Are config and locale `escrow_ignore`d so legitimate buyers never need to
  touch protected code?
- Is any custom obfuscation present that would stop the honest server owner from
  auditing the resource? Remove it; rely on escrow and server authority.
