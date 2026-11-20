# Streaming Assets

Use this file when a FiveM/RedM resource ships game assets - models, textures,
anim dicts, maps, or meta overrides - and you need them to load on clients, be
referenced from the manifest, or be requested at runtime without leaking memory.
It covers the `stream/` folder, the `data_file` directive, when assets also need
listing in `files { }`, runtime requests with a timeout, and cleanup. Verify any
native you touch against the matching native reference before relying on it.

## The stream Folder

- Files placed in a `stream/` folder at the resource root are packaged and
  streamed to clients automatically - no manifest entry per asset is needed.
- Subfolders inside `stream/` are allowed and purely organizational; the engine
  walks the whole tree. Use them to group assets, not to change behavior.
- This ships drawable/model assets (for FiveM: `.ydr`, `.yft`, `.ytd`, `.ydd`,
  and map `.ymap`/`.ytyp`). Do not assume RedM uses the same asset types -
  verify RDR3 formats before packaging, they differ.
- A resource that replaces or adds map data marks itself with `this_is_a_map`
  in the manifest so the map store reloads when it starts.

## The data_file Directive

- `data_file` adds a typed meta/data file to the game's extra-content mounting
  system. Syntax is two string arguments - the type key, then the path. The
  path field supports globbing, so one directive can cover many meta files:
  ```lua
  data_file 'HANDLING_FILE' 'metas/*_handling.meta'
  data_file 'VEHICLE_METADATA_FILE' 'myvehicles.meta'
  data_file 'CARCOLS_FILE' 'carcols.meta'
  data_file 'WEAPONINFO_FILE' 'weapons.meta'
  data_file 'AUDIO_WAVEPACK' 'audio/mywaves'
  ```
- Each key above is confirmed against the fivem-docs data-files table, as are
  the vehicle-layout, vehicle-variation, and weapon-animation file types. The
  reference lists many more - look the exact key up, never invent one.

## data_file vs files vs stream

- `stream/` assets need no `files { }` entry - packaging and client download are
  automatic.
- A `data_file` meta is not downloaded just by being declared. The referenced
  file (and its glob matches) must also appear in `files { }` so clients get it:
  ```lua
  files {
      'myvehicles.meta',
      'metas/*_handling.meta',
  }
  data_file 'VEHICLE_METADATA_FILE' 'myvehicles.meta'
  data_file 'HANDLING_FILE' 'metas/*_handling.meta'
  ```
- Any non-stream file a client reads at runtime (config, locale, a plain data
  file read from the resource) must be in `files { }`, same rule as the
  config-in-files note in the fxmanifest rules. Keep paths explicit and avoid
  globs so wide they sweep in unintended files.

## Requesting Assets At Runtime

- To spawn an entity you must load its model first, then release it. Pattern:
  ```lua
  RequestModel(model)
  local deadline = GetGameTimer() + 10000
  while not HasModelLoaded(model) do
      if GetGameTimer() > deadline then return end
      Wait(0)
  end
  -- create the entity, then:
  SetModelAsNoLongerNeeded(model)
  ```
- Always bound the wait with a timeout - a bad or missing hash never loads and
  an unbounded `while ... do Wait(0) end` hangs the thread. Guard the hash with
  `IsModelValid` / `IsModelInCdimage` before requesting.
- Same shape for anim dicts (`RequestAnimDict` + `HasAnimDictLoaded`), streamed
  texture dicts (`RequestStreamedTextureDict` + `HasStreamedTextureDictLoaded`),
  and named particle assets (`RequestNamedPtfxAsset`).
- `SetModelAsNoLongerNeeded` does not delete a loaded entity; it drops the
  script's lock so the engine can unload the model once nothing uses it.

## Prefer ox_lib Request Helpers

- When the resource already loads ox_lib, use its request helpers - they wrap
  the request/poll/timeout loop and error on an invalid asset instead of
  hanging. Verified helpers: `lib.requestModel`, `lib.requestAnimDict`,
  `lib.requestStreamedTextureDict`, `lib.requestAnimSet`, `lib.requestWeaponAsset`,
  `lib.requestNamedPtfxAsset`, `lib.requestAudioBank`, `lib.requestScaleformMovie`.
- Each takes the asset and an optional timeout in ms and yields until loaded:
  ```lua
  local model = lib.requestModel(`prop_bench_01a`, 5000)
  ```
- Do not add ox_lib solely for this if the resource does not already use it -
  the raw request/timeout loop above is fine. Follow the ox_lib adoption rule.

## Cost And Cleanup

- Streamed assets grow the client download and sit in memory - every file in
  `stream/` ships to every player. Keep the set scoped to what the resource
  actually uses; do not bundle unused or duplicate assets.
- Release every model/dict you request with the matching no-longer-needed native
  once you are done, or the engine keeps it pinned and memory climbs.
- Delete entities you created on resource stop and player drop, guarded with
  `DoesEntityExist`, same as the general cleanup rule; releasing the model is
  not a substitute for deleting the entity.

## RedM Caveats

- RDR3 asset types and some streaming natives differ from GTA V - do not reuse
  GTA type keys or assume a native exists on RedM. Verify against the RDR3
  native reference.
- RedM's `REQUEST_MODEL` takes an extra trailing BOOL argument not present in
  GTA V's; pass it per the reference rather than copying a FiveM call verbatim.
- RedM also streams prop sets with their own natives (`_REQUEST_PROP_SET`,
  `_HAS_PROP_SET_LOADED`, `_RELEASE_PROP_SET`) - the same request/poll/release
  discipline applies.

## Review Questions

- Are `stream/` assets actually used by the resource, or is dead weight shipping
  to every client?
- Does every `data_file` meta also appear in `files { }` so clients download it?
- Is each runtime request bounded by a timeout, with the hash validated before
  requesting?
- Is every requested model/dict released, and every created entity deleted on
  stop and player drop?
- For RedM, were the asset types and native signatures verified against the RDR3
  reference instead of assumed from GTA V?
