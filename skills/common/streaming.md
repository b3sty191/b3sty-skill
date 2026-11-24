# Streaming Assets

Use this file when a resource ships game assets (models, textures, anim dicts, maps, meta overrides) and they must reach clients, be referenced from the manifest, or be requested at runtime without leaking memory. Verify any native you touch against the matching native reference.

## The stream Folder

- Files in a `stream/` folder at the resource root are packaged and streamed to clients automatically — no manifest entry per asset, no `files { }` entry.
- Subfolders inside `stream/` are allowed and purely organizational; the engine walks the whole tree.
- This ships drawable/model assets — for FiveM `.ydr`, `.yft`, `.ytd`, `.ydd`, and map `.ymap`/`.ytyp`. RedM asset types differ; verify RDR3 formats before packaging.
- A resource that replaces or adds map data marks itself `this_is_a_map` in the manifest so the map store reloads when it starts.

## The data_file Directive

- `data_file` mounts a typed meta/data file into the game's extra-content system. Two string arguments: type key, then path. The path field globs, so one directive can cover many meta files:
  ```lua
  data_file 'HANDLING_FILE' 'metas/*_handling.meta'
  data_file 'VEHICLE_METADATA_FILE' 'myvehicles.meta'
  data_file 'CARCOLS_FILE' 'carcols.meta'
  data_file 'WEAPONINFO_FILE' 'weapons.meta'
  data_file 'AUDIO_WAVEPACK' 'audio/mywaves'
  ```
- Each key above is confirmed against the fivem-docs data-files table, as are the vehicle-layout, vehicle-variation, and weapon-animation file types. The reference lists many more — look the exact key up, never invent one.

## data_file vs files vs stream

- `stream/` assets need no `files { }` entry; packaging and client download are automatic.
- A `data_file` meta is *not* downloaded just by being declared: the referenced file and its glob matches must also appear in `files { }`, e.g. `files { 'myvehicles.meta', 'metas/*_handling.meta' }` beside the matching `data_file` lines.
- Any non-stream file a client reads at runtime (config, locale, a plain data file) must be in `files { }` too, same rule as the config-in-files note in the fxmanifest rules. Keep paths explicit; avoid globs wide enough to sweep in unintended files.

## Requesting Assets At Runtime

- Load a model before spawning an entity, then release it:
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
- Always bound the wait with a timeout: a bad or missing hash never loads and an unbounded `while ... do Wait(0) end` hangs the thread. Guard the hash with `IsModelValid` / `IsModelInCdimage` before requesting.
- Same shape for anim dicts (`RequestAnimDict` + `HasAnimDictLoaded`), streamed texture dicts (`RequestStreamedTextureDict` + `HasStreamedTextureDictLoaded`), and named particle assets (`RequestNamedPtfxAsset`).
- `SetModelAsNoLongerNeeded` does not delete a loaded entity; it drops the script's lock so the engine can unload the model once nothing uses it.

## Prefer ox_lib Request Helpers

- When the resource already loads ox_lib, use its request helpers: they wrap the request/poll/timeout loop and error on an invalid asset instead of hanging. Verified helpers: `lib.requestModel`, `lib.requestAnimDict`, `lib.requestStreamedTextureDict`, `lib.requestAnimSet`, `lib.requestWeaponAsset`, `lib.requestNamedPtfxAsset`, `lib.requestAudioBank`, `lib.requestScaleformMovie`.
- Each takes the asset and an optional timeout in ms and yields until loaded:
  ```lua
  local model = lib.requestModel(`prop_bench_01a`, 5000)
  ```
- Do not add ox_lib solely for this if the resource does not already use it — the raw request/timeout loop above is fine. Follow the ox_lib adoption rule.

## Cost And Cleanup

- Every file in `stream/` ships to every player and sits in memory: keep the set scoped to what the resource actually uses, with no unused or duplicate assets.
- Release every model/dict you request with the matching no-longer-needed native, or the engine keeps it pinned and memory climbs.
- Delete entities you created on resource stop and player drop, guarded with `DoesEntityExist`, same as the general cleanup rule; releasing the model is not a substitute for deleting the entity.

## RedM Caveats

- RDR3 asset types and some streaming natives differ from GTA V — do not reuse GTA type keys or assume a native exists on RedM; verify against the RDR3 native reference.
- RedM's `REQUEST_MODEL` takes an extra trailing BOOL argument GTA V's does not; pass it per the reference rather than copying a FiveM call verbatim.
- RedM also streams prop sets with their own natives (`_REQUEST_PROP_SET`, `_HAS_PROP_SET_LOADED`, `_RELEASE_PROP_SET`); the same request/poll/release discipline applies.

## Review Questions

- Are `stream/` assets actually used, or is dead weight shipping to every client?
- Does every `data_file` meta also appear in `files { }` so clients download it?
- Is each runtime request bounded by a timeout, with the hash validated before requesting?
- Is every requested model/dict released, and every created entity deleted on stop and player drop?
- For RedM, were asset types and native signatures verified against the RDR3 reference instead of assumed from GTA V?
