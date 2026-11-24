# Network Performance Rules

Use when a RedM/FiveM resource sends events, syncs state or ships data between client, server and NUI, and the problem is bandwidth, event spam, hitches, or "Reliable network event overflow" disconnects. CPU hot paths: `skills/common/performance.md` -> Performance Rules. How to measure: `skills/common/debugging.md` -> Performance Debugging. Security still wins: never drop a server check to save bytes.

## Cost Model

- A net event costs roughly `(name + packed args) x sends per second x recipients`, plus handler CPU on every receiver; the name rides along on every send.
- A tiny payload is still Critical from a per-frame loop: one client at `Wait(0)` sends dozens of events a second, hits the `netEvent` limit, and a hundred clients make that thousands for the server to handle.
- `Wait(0)` is "next frame", not a fixed rate - label any events-per-second figure not taken from `netEventLog` or a profiler as an estimate.
- A resource can sit at `0.00ms` in `resmon` and still flood the network, or send nothing and burn CPU - check both before calling it optimized.

## OneSync Send Cadence

- Per-entity send delay: 50 ms, 150 ms while the entity is outside that client's view frustum, 250 ms past 250 m, 500 ms past 500 m, divided by 4 within 35 m; players and occupied vehicles stay at 50 ms (so ~12 ms within 35 m). Compiled constants - no convar or script changes them. (verified: ServerGameState.cpp, FXServer 35945)
- One OneSync pass runs every 24 ms (48 ms with `sv_useAccurateSends 0`) and each delay rounds up to whole passes, so a 12 ms delay really sends every 24 ms. Clients send their own state about 61 Hz (measured) - a faster pass carries no newer data.
- Close-range desync at these rates is the engine, not the resource: fix it with server-side authority over the outcome, not a faster sender loop.

## Rate Limits

FXServer keeps per-client token buckets (tune with `set rateLimiter_<name>_rate` / `_burst`). Fix the sender; raising limits only hides a spammy resource.

| Limiter (rate / burst) | Over the limit |
|---|---|
| `netEvent` (50 / 200 events) | Event silently dropped |
| `netEventFlood` (75 / 300) | Also empty: kick "Reliable network event overflow." |
| `netEventSize` (128 KiB / 384 KiB of name + payload) | Kick "Reliable network event size overflow: <event>" |
| `stateBag` (75 / 125 updates) | Update dropped, logged on `sbag-update-dropped` |
| `stateBagFlood` (150 / 175) | Also exceeded: kick "Reliable state bag packet overflow." |
| `stateBagSize` (128 KiB / 256 KiB) | Kick |
| `latentEvent` (75 / 125) / `latentEventFlood` (150 / 175) | Fragment dropped / kick "latent event packet overflow." |
| `netGameEvent` (200 / 300 engine game events) | Kick "Reliable netGameEvent overflow." |
| `http_<resource>` (10 / 25 per IP, each `SetHttpHandler` endpoint) | Request rejected |
| `http_info`, `http_players` (4 / 10), `http_perf` (2 / 5), `getstatus` (1 / 5), all per IP | Request rejected |

- A dropped event looks like a random gameplay bug ("sometimes the item never arrives") - when a handler "sometimes doesn't fire", check the sender's rate before the handler's logic.
- The overflow kick is count-based: too many events, not too many bytes. Find the event in `netEventLog` and stop the flood at the source.

## Choosing The Channel

| Need | Use |
|---|---|
| Same machine, two scripts or resources | `TriggerEvent` or an export - never a server round-trip to talk to yourself |
| Small, latency-sensitive action (use item, open door, fire) | `TriggerServerEvent` / `TriggerClientEvent` |
| Visible state other clients render (cuffed, fuel, outfit id) | State bag + `AddStateBagChangeHandler` |
| Large one-off transfer (catalog, outfit pack, bulk sync) | `TriggerLatentClientEvent` / `TriggerLatentServerEvent` |
| Lua to the NUI page | `SendNUIMessage` - no game network, but JSON and CEF cost show in `resmon` |

- Request/response callbacks (`lib.callback`, framework callbacks) are two net messages per call - same payload, throttle and validation rules as events.

## Latent Events

- Latent events split a large payload into fragments sent at a capped rate (`bps` is bytes per second, not bits, despite the name; `0` or negative means 25000 B/s) so the transfer does not choke the connection. Multi-KB transfers only - never small gameplay actions where the added latency matters.
- `bps` is per recipient: a latent event to `-1` sends about `bps x players` from the server. Very high values (around 10,000,000) defeat the point and cause connection problems.
- They ride on net event reassembly (`sv_enableNetEventReassembly`, on by default) - a server that turned it off cannot send them.
- A normal client-to-server event is capped at 384 KiB per packet and by `netEventSize`; server-to-client events have no hard cap, so a huge normal event can stall that client long enough to time it out. That is the case latent events exist for.

## Payload Shape

- Arguments are packed with msgpack: `json.encode` first only adds CPU and a larger string - send the table.
- Send only the fields the receiver reads; shipping a whole player (job, inventory, weapons) to update coords is the classic waste.
- Never send entity handles - send net IDs and resolve them on the other side (`skills/common/networking.md` -> Handles And Net IDs).
- Build the payload when state changes, not every tick: an unchanged table encoded every frame is pure waste.

## Snapshot Then Deltas

The expensive mistake is fetching the same full data again and again.

- Send full data once per cache lifetime: static catalogs at resource start, player data when the character loads, UI data the first time it is needed this session.
- Keep it where it is read: server RAM for authority (`skills/common/database.md` persistence pattern), a client table for display.
- After the snapshot, send only what changed (`itemChanged(name, count)`), never the whole inventory.
- Reopening a UI is no reason to ask the server again - the client already holds the snapshot and pushes it to NUI locally. A server callback running `SELECT` on every menu open is a full fetch on a path that should read RAM.
- Invalidate on player drop, character switch (load a fresh snapshot rather than merging into the old one) and resource stop.
- The client copy is display-only; the server still validates every action against its own state.

## Audience

- Pick the smallest audience that needs the data: the one player, then server-computed nearby players, then the routing bucket, then a job/role set, and `-1` only when every client truly needs it (`skills/common/networking.md` -> Broadcasting And Scoped Messages). `-1` ignores routing buckets - players in other instances receive it too.
- Batch small updates from the same short window into one event when the extra delay does not change gameplay. Never batch or throttle hits, shots, or anything where arrival order decides an outcome.
- Throttle non-critical streams (HUD position, idle stats) by time (`GetGameTimer()` gate), not by frame.

## State Bags

- Server writes replicate; client writes stay local unless set with `state:set(key, value, true)`, and strict mode (`setr sv_stateBagStrictMode true`) blocks client writes entirely.
- Bags are shallow: `Entity(x).state.data.field = v` does not replicate - reassign the whole value or use a flat key such as `state['data:field']`.
- Each read returns a fresh copy: read a large value once per tick into a local, and keep large blobs out of bags (use a latent event).
- React with `AddStateBagChangeHandler` instead of polling a bag in a loop.

## Review Questions

- Does any `Trigger*Event` run inside a per-frame or short-wait loop?
- Does any event go to `-1` when a smaller audience would do?
- Is the full dataset fetched more than once per cache lifetime?
- Are payloads trimmed to what the receiver reads, with no extra `json.encode`?
- Are multi-KB transfers latent, and small gameplay events not latent?
- Are state bag values small, flat, and written by the server?
- Was the change measured with `netEventLog` before and after, or labeled as an estimate?
