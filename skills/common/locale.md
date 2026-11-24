# Localization And Locale Files


## Separate Strings From Logic

- Keep every player-visible string in a locale file or a shared locale table, addressed by a stable key. Business code references the key, not the words.
- A string a player reads is data, not logic - a price check, an ownership test, or a cooldown must not have English baked into it.
- Build runtime values with `string.format` placeholders (`%s`, `%d`) passed through `locale(key, value)`, not by concatenating translated fragments; word order differs across languages. In ox_lib, `${otherKey}` inside a locale string references another locale entry (composition between strings), not a runtime argument.
- Keep keys descriptive and namespaced by feature (`shop.opened`, `shop.not_enough_money`), so the file reads as a map of the resource's surface.
- Do not duplicate the same string under many keys; reuse one key where the same sentence appears.

## ox_lib Locale

When the resource already depends on ox_lib, use its locale module rather than a hand-rolled table. Names below are verified against overextended/ox_lib `imports/locale/shared.lua` and `resource/locale/*.lua` (master, 2026-11-20).

- `locale(key, ...)` is a global - it returns the translated string for `key`, applying `string.format` when extra args are passed. On a missing key it returns the key itself, so nothing crashes and the gap is visible on screen.
- Load the module from the manifest so it initializes once; this is the maintainer's documented preference over calling the loader by hand:
  ```lua
  shared_scripts { '@ox_lib/init.lua' }
  ox_lib 'locale'
  files { 'locales/*.json' }
  ```
- `files { 'locales/*.json' }` is required because the client reads locale JSON with `LoadResourceFile`, which only sees client files declared in `files`. ([citizenfx/fivem `ext/native-decls/LoadResourceFile.md`](https://raw.githubusercontent.com/citizenfx/fivem/master/ext/native-decls/LoadResourceFile.md))
- Locale files are `locales/<key>.json` (e.g. `locales/en.json`, `locales/fr.json`); override the folder with a `locales_path` manifest metadata entry. Nested JSON objects flatten to dotted keys (`{"shop":{"opened":"..."}}` -> `shop.opened`).
- `en.json` always loads first and the active language merges over it, so English is the built-in fallback for any key a translation omits.
- `lib.locale(key?)` reloads the dict for a language; `lib.getLocales()` returns the flattened dict; `lib.getLocale(resource, key)` pulls one string from another resource's locale.
- The active language comes from the `ox:locale` convar (default `en`); the client honors a per-player choice when the `ox:userLocales` convar is `1`. Server and client each resolve their own language independently.

## No-ox_lib Fallback

Same shape without ox_lib: a plain shared table selected by a resource-prefixed convar.

- Put strings in a shared-script table keyed by language, with `en` always present as the default:
  ```lua
  Locales = Locales or {}
  Locales["en"] = {
      ["shop.opened"] = "Shop opened",
      ["shop.not_enough_money"] = "You cannot afford %s",
  }
  ```
- Select the language once from a convar and fall through to `en`, then to the key, so a missing string is never a nil error:
  ```lua
  local lang = GetConvar("myres:locale", "en")
  function L(key, ...)
      local str = (Locales[lang] and Locales[lang][key]) or (Locales["en"] and Locales["en"][key])
      if not str then return key end
      return ... and str:format(...) or str
  end
  ```
- `GetConvar(name, default)` is a shared CFX native; use a resource-prefixed convar name, not an engine one. ([citizenfx/fivem `ext/native-decls/GetConvar.md`](https://raw.githubusercontent.com/citizenfx/fivem/master/ext/native-decls/GetConvar.md))

## Client vs Server

- Resolve a string on the side that owns the context: client for notifications, menus, and prompts; server for chat broadcasts, admin logs, and kick/ban reasons.
- Each side loads its own locale from files or the shared table - do not round-trip to the other side to translate.
- Do not send whole locale tables across the network on every event. For NUI, push the locale set once at UI init (ox_lib does this with a single `setLocale` message), then reference keys in the browser.
- When only the server knows the value, format the final string server-side and send that one string, rather than shipping the table so the client can format it.
- Keep a resource's locale footprint per-side: the server needs only the keys it prints, the client only the keys it shows.

## Keys And Missing Keys

- Treat keys as a stable contract. Renaming a key breaks every translation file and any NUI reference at once - add a new key instead of silently repurposing an old one.
- Missing-key behavior must be visible, never fatal: return the key (both backends above do). Never let an absent translation throw or blank the UI.
- Ship a complete `en` baseline; partial translations then degrade to English per key, not to a crash.
- Do not log a hard error for every missing key in a hot path; a single warning on load or first use is enough to surface the gap.

## Review Questions

- Is any player-facing string hardcoded inside business logic instead of a locale key?
- Does a missing key return the key (visible) rather than nil-erroring or blanking the screen?
- Is there a complete `en` fallback that every other language degrades to per key?
- Are runtime values inserted with placeholders rather than concatenated translated fragments?
- Does any code send a whole locale table over the network per event instead of resolving the string or pushing the set to NUI once?
- Is the active language chosen from a convar (`ox:locale`, or a resource-prefixed one) with a safe default?
