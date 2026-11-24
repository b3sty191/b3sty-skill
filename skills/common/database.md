# Database Rules

Use this file when a RedM/FiveM resource reads or writes SQL, owns persisted player/resource state, changes schema, or depends on OxMySQL/mysql-async style APIs.

## Defaults

- Keep database access server-side only.
- Prefer `oxmysql` for new SQL work when the project accepts that dependency.
- Do not add a database dependency to a resource that can stay config-only or framework-state-only.
- Keep query code close to the feature unless the same query is reused enough to justify a small helper.
- Validate public event, callback, command, export, and NUI input before it reaches SQL.
- Run the game database as a dedicated user with grants limited to the game schema (no `SUPER`/`FILE`/`GRANT`, never root), reachable only from the server host or a private network. See `skills/common/server-hardening.md` -> Server Hardening And Operations.
- Use `skills/common/security-performance.md` with this file for event validation, throttles, replay protection, and dirty saves.

## Manifest And Startup

- For OxMySQL Lua resources, import the library before any server scripts that use `MySQL`:
  ```lua
  server_scripts {
      '@oxmysql/lib/MySQL.lua',
      'core/server.lua',
  }
  ```
- Declare `dependency 'oxmysql'` when the resource requires OxMySQL to function.
- Make sure `oxmysql` starts before resources that query the database.
- Configure the connection string in server config before database-backed resources start.
- Keep database credentials, webhooks, and private tokens out of shared/client files.

## Query Safety

- Use parameterized queries only.
- Never build SQL by concatenating player input, NUI input, item names, identifiers, job names, or config keys.
- Validate and normalize values before passing them as query parameters.
- Keep dynamic table/column names out of public input. If dynamic names are unavoidable, choose from a server-side allowlist.
- Prefer `?` placeholders for ordinary OxMySQL queries. Named placeholders (`@name`/`:name` with a keyed table) still work and are on unless `mysql_connection_string` sets `namedPlaceholders=false`, but oxmysql marks them deprecated; use `?` in new code. ([oxmysql placeholders](https://overextended.dev/docs/oxmysql/placeholders))
- Backtick fixed table and column names when they may conflict with reserved words.
- Check affected row counts for updates that are expected to mutate exactly one row.

### SQL Injection

A bound parameter is treated as data, never as SQL. A concatenated string lets one quote break out. ([oxmysql](https://overextended.dev/docs/oxmysql), [Secure your events](https://docs.fivem.net/docs/developers/server-security/))

```lua
-- BAD: item is spliced into the query; a value like  x'; DROP TABLE logs;--  runs arbitrary SQL
MySQL.query("INSERT INTO logs (item) VALUES ('" .. item .. "')")

-- GOOD: the ? placeholder is bound by the engine; item is data
MySQL.insert.await("INSERT INTO logs (item) VALUES (?)", { item })
```

- Bind every value. For a dynamic identifier (table/column name) choose from a server-side allowlist and interpolate only the allowlisted constant - never the raw input.
- Wrap multi-step valuable writes in one transaction, but know that `MySQL.transaction` rolls back only when a statement throws ([oxmysql transaction](https://overextended.dev/docs/oxmysql/Functions/transaction)). A conditional `UPDATE ... WHERE money >= ?` that matches 0 rows is not an error: the remaining statements still commit and the call returns `true`. When a conditional statement must gate the grant, use one of these:
  - Run the conditional debit alone with `MySQL.update.await`, grant only if it changed exactly 1 row, and refund with a compensating update if the grant fails (wrap the grant in `pcall`, since `.await` raises on an SQL error).
  - Use `MySQL.startTransaction`, where returning `false` from the function rolls back. oxmysql marks it experimental:
    ```lua
    local committed = MySQL.startTransaction(function(query)
        local res = query('UPDATE characters SET money = money - ? WHERE owner = ? AND money >= ?', { cost, owner, cost })
        if not res or res.affectedRows ~= 1 then return false end
        query('INSERT INTO inventory (owner, item, count) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE count = count + ?', { owner, item, amount, amount })
    end)
    ```
- See `skills/common/give-value-hardening.md` -> Give-Value Event Hardening (`PurchaseSql`) for the full hardened handler around the conditional debit (validation, throttle, in-flight lock).

## OxMySQL API Shape

- Use the narrowest function that matches the expected result:
  - `MySQL.scalar.await(...)` for one column from one row.
  - `MySQL.single.await(...)` for one row.
  - `MySQL.query.await(...)` for multiple rows.
  - `MySQL.insert.await(...)` when an insert ID matters.
  - `MySQL.update.await(...)` when affected row count matters.
  - `MySQL.prepare.await(...)` for frequently repeated prepared queries or multiple parameter sets.
- Prefer `.await` in coroutine-friendly server code when it keeps the flow clearer.
- Use callback style when the surrounding project already uses callbacks heavily.
- Avoid legacy alias names in new code unless maintaining an existing mysql-async compatibility layer.
- Handle `nil`/empty results and zero affected rows explicitly, and know how errors surface:
  - `MySQL.*.await` (except `MySQL.transaction.await`, which returns `false`) raises a Lua error on SQL failure. Wrap it in `pcall` wherever a lock, in-flight flag, or dirty flag must be restored afterwards.
  - Callback-style queries never invoke the callback on error unless the manifest declares `mysql_option 'return_callback_errors'`, in which case the callback receives `(nil, err)` (except `MySQL.transaction`, whose callback always runs and receives `false` on an SQL error).

## Transactions And Atomic Writes

- Use a transaction for multi-query valuable state changes such as transfers, purchases, crafting, inventories, ownership changes, and claim rewards.
- Treat a transaction result of `false` as a rejected mutation and do not apply in-memory success state. A `true` result does not mean every conditional statement matched a row.
- Prefer one conditional update over check-then-update when one row can enforce the rule.
- For money and inventory, avoid flows that read a balance, yield, and then write a new balance without locking, a transaction, or a conditional update.
- Use unique constraints plus `INSERT ... ON DUPLICATE KEY UPDATE` for upsert behavior, but only where this resource owns row creation: on a save path ODKU recreates rows deleted while the owner was online and can collide with other unique keys. For saves of existing rows use a plain `UPDATE` (see Performance).
- Do not use `REPLACE INTO` for normal upserts because it deletes and reinserts the row.
- Add request IDs, claim IDs, or in-flight markers when client retries could grant twice.

## Persistence Pattern

- Keep active player/resource state in RAM when it is read often.
- Dirty-track changed fields instead of writing every small mutation immediately.
- Debounce autosaves and spread them over time.
- Force-save dirty data on `playerDropped` and `onResourceStop`.
- Clear RAM caches, dirty flags, in-flight saves, and retry state when the player/resource lifetime ends.
- Store only the data the resource owns; do not mirror large framework state unless the resource is authoritative for it.
- Prefer updating specific columns/JSON fields when practical instead of rewriting large blobs for every change.
- See `memory/common/cfx-patterns.md` -> Player Persistence Pattern for a concrete cache + dirty save shape.
- See `memory/common/cfx-patterns.md` -> Save Sequence Guard Pattern when saves of one row can overlap (retry, late autosave, second writer), and -> Linked Trade Save Pattern when value moves between two owners.

## Schema And Migrations

- Put initial schema and migrations in a predictable server-side folder such as `sql/` or `migrations/`.
- Keep migration files ordered and append-only.
- Add a resource schema version table when the resource needs to apply migrations automatically.
- Do not auto-run destructive migrations without an explicit operator action or backup path.
- Write migrations to be idempotent when possible.
- Add indexes for identifiers, owner columns, foreign keys, lookup keys, and high-frequency filters.
- Avoid storing searchable gameplay fields only inside JSON blobs.
- Check `SHOW GRANTS` for the game user before releasing a migration: an `ALTER TABLE ... ADD COLUMN` that fails for lack of privilege leaves every join failing with `ERROR 1054` on the missing column. Gate joins on the column existing (an information_schema check), refuse with a "retry shortly" message, and log loudly (verified: live boot + offline harness).

## Performance

- Select only the columns needed by the feature.
- Avoid N+1 query loops; batch with `IN (...)`, joins, or one query per resource operation.
- Cache hot reference data in RAM when it is stable and has a cleanup/reload path.
- Do not run database queries in `Wait(0)` loops or every client position/UI update.
- Coalesce frequent state changes into one save.
- Use slow-query/debug logging temporarily while diagnosing, then turn it off or scope it to the resource.
- Treat startup slow queries differently from gameplay slow queries; gameplay stalls matter more.
- Batch saves of existing rows with one multi-row `UPDATE t JOIN (SELECT ? AS pk, ? AS col UNION ALL SELECT ?, ?) v ON t.pk = v.pk SET t.col = v.col` per statement shape instead of N single-row updates in a transaction: 0.25-0.28 s -> 0.14-0.15 s per 10k rows and 499 fewer round-trips per batch (verified: MariaDB 12.3.3 benchmark).
  - Collapse duplicate keys to the newest row before building the statement; with a duplicate key in the derived table MariaDB picks the winning value non-deterministically.
  - Send variable row counts through the text protocol (`MySQL.update`), not `MySQL.prepare`: every batch size is another prepared statement and fills the per-connection cache up to `max_prepared_stmt_count` (16382).
  - Cap rows per statement in gameplay-time lanes (about 16): parameter binding runs on svMain, ~29 us per row at 2048 players.
- Do not build every player's save row in one frame: at 2048 players that was a 222 ms svMain frame; 150 players per frame with `Wait(0)` between chunks cut the worst frame to 69 ms (wall time 0.36 s -> 0.86 s). Prefer a time budget (~8 ms per frame) measured with `os.nanotime` over a fixed count (verified: 2048-player save waves).
- Calling oxmysql (or any JS resource) from Lua packs the arguments with msgpack on svMain before the query exists: ~31 ms of a ~45-50 ms save burst at 2048 players, of which 15.7 ms was packing 3.8 MB of rows inside the JS `msgpack.js`. Split large parameter arrays across frames; this cost never shows up as database time (verified: measured benchmark, 2048 players).
- Server `SetResourceKvp*`/`DeleteResourceKvp` fsync the WAL on every call (~0.6 ms each, so 500 writes in a loop stall the tick ~300 ms). For bulk writes use the `*NoSync` variants plus one `FlushResourceKvp()`; NoSync data survives `kill -9` but not power loss before that flush (verified: `ServerKVScriptFunctions.cpp`, FXServer 35945).

## Error Handling And Logging

- Log database failures with resource name, query purpose, source/identifier when relevant, and a bounded error message.
- Do not log full payloads containing secrets, tokens, webhooks, passwords, authorization headers, or large JSON blobs.
- Use retry windows for transient save failures, but cap retries and keep failure visible.
- Make failed persistence behavior explicit: retry, mark dirty again, reject the action, or roll back in-memory state. Put that recovery in a path that actually runs on error: a `pcall` around `.await`, or a callback with `mysql_option 'return_callback_errors'` declared (see OxMySQL API Shape above).
- A MariaDB outage is silent in resource logs: oxmysql queues the queries and runs them when the connection returns, so `.await` simply hangs, nothing errors and nothing rolls back. Bound long awaits with your own watchdog and confirm the outage in the oxmysql/MariaDB logs (verified: live connection-loss test).
- Do not silently create missing critical rows in response to untrusted client input.

## Review Questions

- Can any player-controlled value reach SQL without validation?
- Does this action need a transaction, conditional update, or in-flight marker?
- Is this query called in a loop, tick, callback spam path, or NUI spam path?
- Is the database dependency declared and loaded before this server file?
- Does a failed save keep data dirty or otherwise recover?
- Are migrations safe to rerun and safe for existing production data?
- Are indexes present for the columns used in frequent filters and joins?
