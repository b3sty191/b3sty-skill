# Localization And Locale Files

Use when a resource shows translatable player-facing text: shop prompts, notifications, menu labels, errors, chat output, NUI copy. Whichever backend, strings live in locale files under stable keys, never hardcoded in gameplay logic, so translators and owners change wording without touching code.

## Separate Strings From Logic

- Player-visible strings live in a locale file or shared locale table under a stable key; code references the key, not the words. What a player reads is data: a price check, ownership test, or cooldown must not have English baked in.
- Insert runtime values with `string.format` placeholders (`%s`, `%d`) through `locale(key, value)`, never by concatenating translated fragments - word order differs across languages. ox_lib's `${otherKey}` inside a locale string references another locale entry (composition between strings), not a runtime argument.
- Keys stay descriptive and namespaced by feature (`shop.opened`, `shop.not_enough_money`), mapping the resource's surface; never duplicate one sentence under many keys.

## ox_lib Locale

With ox_lib as a dependency, use its locale module, not a hand-rolled table. Verified against overextended/ox_lib `imports/locale/shared.lua` and `resource/locale/*.lua` (master, 2026-11-20).

- `locale(key, ...)` is a global returning the translated string, `string.format`ting extra args. A missing key returns the key itself: nothing crashes, the gap shows on screen.
- Load from the manifest so it initializes once (the maintainer's documented preference over calling the loader by hand):
  ```lua
  shared_scripts { '@ox_lib/init.lua' }
  ox_lib 'locale'
  files { 'locales/*.json' }
  ```
- `files { 'locales/*.json' }` is required: the client reads locale JSON with `LoadResourceFile`, which only sees client files declared in `files`. ([citizenfx/fivem `ext/native-decls/LoadResourceFile.md`](https://raw.githubusercontent.com/citizenfx/fivem/master/ext/native-decls/LoadResourceFile.md))
- Files are `locales/<key>.json` (`locales/en.json`, `locales/fr.json`); the `locales_path` manifest metadata entry overrides the folder. Nested JSON flattens to dotted keys (`{"shop":{"opened":"..."}}` -> `shop.opened`).
- `en.json` loads first and the active language merges over it: English is the built-in per-key fallback.
- `lib.locale(key?)` reloads a language's dict; `lib.getLocales()` returns the flattened dict; `lib.getLocale(resource, key)` reads one string from another resource.
- Active language: the `ox:locale` convar (default `en`); the client honors a per-player choice when `ox:userLocales` is `1`. Server and client resolve independently.

## No-ox_lib Fallback

Same shape without ox_lib: a plain shared table selected by a resource-prefixed convar.

- Strings in a shared-script table keyed by language, `en` always present as default:
  ```lua
  Locales = Locales or {}
  Locales["en"] = {
      ["shop.opened"] = "Shop opened",
      ["shop.not_enough_money"] = "You cannot afford %s",
  }
  ```
- Select the language once from a convar, falling through to `en` then to the key, so a miss is never a nil error:
  ```lua
  local lang = GetConvar("myres:locale", "en")
  function L(key, ...)
      local str = (Locales[lang] and Locales[lang][key]) or (Locales["en"] and Locales["en"][key])
      if not str then return key end
      return ... and str:format(...) or str
  end
  ```
- `GetConvar(name, default)` is a shared CFX native; use a resource-prefixed convar name, not an engine one. ([citizenfx/fivem `ext/native-decls/GetConvar.md`](https://raw.githubusercontent.com/citizenfx/fivem/master/ext/native-decls/GetConvar.md))
- Load locale tables as `shared_scripts` so both sides see them; never rebuild per call. Returning the key on a miss mirrors ox_lib - keep it, so untranslated strings surface in play and logs instead of erroring.

## Client vs Server

- Resolve on the side owning the context: client for notifications, menus, prompts; server for chat broadcasts, admin logs, kick/ban reasons. Each side loads its own locale - never round-trip to translate.
- Never send whole locale tables per event. For NUI, push the set once at UI init (ox_lib sends one `setLocale` message), then reference keys in the browser.
- When only the server knows the value, format server-side and send the one finished string, not the table.
- Per-side footprint: the server needs only the keys it prints, the client only the keys it shows.

## Keys And Missing Keys

- Keys are a stable contract: a rename breaks every translation file and NUI reference at once - add a new key, never repurpose an old one.
- Missing keys stay visible, never fatal: return the key (both backends do), never throw or blank the UI.
- Ship a complete `en` baseline so partial translations degrade to English per key, not to a crash.
- No hard error per missing key in a hot path; one warning on load or first use surfaces the gap.

## Review Questions

- Any player-facing string hardcoded in business logic instead of a locale key?
- Does a missing key return the key rather than nil-erroring or blanking the screen?
- Complete `en` fallback that every language degrades to per key?
- Runtime values via placeholders, not concatenated translated fragments?
- Any whole locale table sent per event instead of resolving the string or pushing the set to NUI once?
- Active language from a convar (`ox:locale` or resource-prefixed) with a safe default?
