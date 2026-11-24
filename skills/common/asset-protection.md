# Asset Protection Rules

Use when an author protects a resource they sell or distribute - against leaks, cracks, and unpaid use. Protects **your own** work with FiveM/RedM-sanctioned mechanisms; it never hides a resource from the server owner running it, and never helps bypass another author's protection.

Order of strength: architecture (value server-side) > CFX Asset Escrow (the sanctioned packaging protection) > own Lua obfuscation, which is discouraged: it stops no determined attacker, breaks the owner's audit, and a hand-obfuscated non-escrow resource reads as a backdoor here.

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

Escrow encrypts the resource server-side so others cannot read or modify protected files, and ties it to buyers through Tebex. From CFX's Asset Escrow page and the resource-manifest reference; confirm current details there.

- **Protects** `Lua`, `YFT`, `YDD`, and `YDR` files. NUI (HTML/CSS/JS) is **not** covered - never hide a secret in NUI and assume escrow covers it.
- **Create**: zip the resource, upload it as an asset at CFX Portal (portal.cfx.re) for encryption; max asset size 1GB. Updates are a re-upload; buyers get it through a Tebex package, subscriptions supported (the asset is removed when the subscription lapses).
- **Entitlement**: an unauthorized server gets `You lack the required entitlement` and the resource does not start.
- **Keep config and locale editable** with `escrow_ignore` in `fxmanifest.lua`, so buyers configure without touching protected logic:
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

- CFX documents obfuscation of an escrowed resource as **not necessary** - escrow already encrypts the protected files; source-level Lua obfuscation raises effort, not a barrier.
- Cost: an owner who legitimately runs it cannot read what it does - the shape of a backdoored or data-stealing resource, and good owners refuse what they cannot audit (buyer-side vetting: `skills/common/server-hardening.md` -> Server Hardening And Operations).
- So: escrow what must ship, keep value server-side, leave shipped Lua readable. No decoy logic, anti-analysis traps, or opaque predicates in code other people run.

## Secret Hygiene

- Never ship API keys, webhook URLs, tokens, database strings, or license secrets anywhere - not client files, not NUI, not even escrowed Lua; a leaked or cracked resource leaks them all. Keep them in `server.cfg` / `secrets.cfg` convars read at runtime (`skills/common/server-hardening.md` -> Config, Convars, And Secrets, `references/server.cfg.example`).
- NUI is not escrow-protected and ships in the clear: every value the browser sees is public.
- Before packaging, grep the build for secret shapes (keys, bearer tokens, Discord webhook URLs); move hits server-side.

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

- Could a leaked client bundle reconstruct the server logic or run without the entitlement? Then move value server-side.
- Any secret shipped in a file a buyer or leaker can read?
- Config and locale `escrow_ignore`d, so buyers never touch protected code?
- Any custom obfuscation blocking an honest owner's audit? Remove it; rely on escrow and server authority.
