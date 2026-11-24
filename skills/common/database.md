# Database Rules

Use when a resource reads or writes SQL, owns persisted player/resource state, changes schema, or uses OxMySQL/mysql-async APIs.

## Defaults

- SQL is server-side only. Prefer `oxmysql` for new work the project accepts; no database dependency on a resource that can stay config-only or framework-state-only.
- Query code lives next to its feature; extract a helper only for a query reused enough to justify it. Validate public event/callback/command/export/NUI input before it reaches SQL.
- Run the game database as a dedicated user granted only the game schema (no `SUPER`/`FILE`/`GRANT`, never root), reachable only from the server host or a private network (`skills/common/server-hardening.md` -> Server Hardening And Operations).
- Pair with `skills/common/security-performance.md` for event validation, throttles, replay protection, dirty saves.

## Manifest And Startup

- OxMySQL Lua resources import the library before any server script that uses `MySQL`:
  ```lua
  server_scripts { '@oxmysql/lib/MySQL.lua', 'core/server.lua' }
  ```
- Declare `dependency 'oxmysql'` when needed, start `oxmysql` before resources that query, set the connection string in server config before database-backed resources start.
- Credentials, webhooks, private tokens never in shared/client files.

## Query Safety

- Parameterized queries only: never concatenate player, NUI, item-name, identifier, job-name or config-key input into SQL. Bind every value, validated and normalized first.
- Dynamic table/column names stay out of public input; if unavoidable, pick from a server-side allowlist and interpolate only the allowlisted constant, never raw input.
- Prefer `?`; named `@name`/`:name` (keyed table) still work and are on unless `mysql_connection_string` sets `namedPlaceholders=false`, but oxmysql deprecates them ([oxmysql placeholders](https://overextended.dev/docs/oxmysql/placeholders)).
- Backtick fixed table/column names that may collide with reserved words.
- Check affected rows for updates expected to mutate exactly one row.

### SQL Injection

A bound parameter is data, never SQL; a concatenated string lets one quote break out. ([oxmysql](https://overextended.dev/docs/oxmysql), [Secure your events](https://docs.fivem.net/docs/developers/server-security/))

```lua
-- BAD: item is spliced in; a value like  x'; DROP TABLE logs;--  runs arbitrary SQL
MySQL.query("INSERT INTO logs (item) VALUES ('" .. item .. "')")

-- GOOD: ? is bound by the engine, so item stays data
MySQL.insert.await("INSERT INTO logs (item) VALUES (?)", { item })
```

- Wrap multi-step valuable writes in one transaction, but `MySQL.transaction` rolls back only when a statement throws ([oxmysql transaction](https://overextended.dev/docs/oxmysql/Functions/transaction)). A conditional `UPDATE ... WHERE money >= ?` matching 0 rows is no error: the rest still commits and the call returns `true`. To let a conditional statement gate the grant, either:
  - run the debit alone with `MySQL.update.await`, grant only if it changed exactly 1 row, refund by compensating update if the grant fails (wrap the grant in `pcall`; `.await` raises on SQL error); or
  - use `MySQL.startTransaction` (oxmysql marks it experimental), where returning `false` rolls back:
    ```lua
    local committed = MySQL.startTransaction(function(query)
        local res = query('UPDATE characters SET money = money - ? WHERE owner = ? AND money >= ?', { cost, owner, cost })
        if not res or res.affectedRows ~= 1 then return false end
        query('INSERT INTO inventory (owner, item, count) VALUES (?, ?, ?) ON DUPLICATE KEY UPDATE count = count + ?', { owner, item, amount, amount })
    end)
    ```
- `skills/common/give-value-hardening.md` -> Give-Value Event Hardening (`PurchaseSql`) hardens the full handler around that debit (validation, throttle, in-flight lock).

## OxMySQL API Shape

- Narrowest function wins: `MySQL.scalar.await` (one column of one row), `MySQL.single.await` (one row), `MySQL.query.await` (many rows), `MySQL.insert.await` (insert ID), `MySQL.update.await` (affected rows), `MySQL.prepare.await` (repeated queries, multiple parameter sets).
- Prefer `.await` where it keeps server flow clearer, callback style where the project already uses it. No legacy aliases in new code unless maintaining a mysql-async compatibility layer.
- Handle `nil`/empty results and zero affected rows explicitly, and know how errors surface:
  - `MySQL.*.await` raises a Lua error on SQL failure (except `MySQL.transaction.await`, which returns `false`). `pcall` it wherever a lock, in-flight flag or dirty flag must be restored afterwards.
  - Callback queries never call back on error unless the manifest declares `mysql_option 'return_callback_errors'`, which makes it receive `(nil, err)` - except `MySQL.transaction`, whose callback always runs and gets `false` on an SQL error.

## Transactions And Atomic Writes

- Transaction for multi-query valuable state changes: transfers, purchases, crafting, inventories, ownership changes, claim rewards.
- `false` is a rejected mutation: apply no in-memory success state. `true` does not mean every conditional statement matched a row (see Query Safety).
- Prefer one conditional update over check-then-update when one row can enforce the rule. For money and inventory, never read a balance, yield, then write a new balance without a lock, transaction or conditional update.
- `INSERT ... ON DUPLICATE KEY UPDATE` plus a unique constraint only where this resource owns row creation: on a save path ODKU recreates rows deleted while the owner was online and can collide with other unique keys. Save existing rows with a plain `UPDATE` (see Performance).
- Never `REPLACE INTO` for normal upserts: it deletes and reinserts the row.
- Request IDs, claim IDs or in-flight markers when client retries could grant twice.

## Persistence Pattern

- Often-read player/resource state in RAM; dirty-track changed fields instead of writing every small mutation; debounce autosaves and spread them over time.
- Force-save dirty data on `playerDropped` and `onResourceStop`. Clear RAM caches, dirty flags, in-flight saves and retry state when the player/resource lifetime ends.
- Store only data this resource owns; do not mirror large framework state unless authoritative for it. Update specific columns/JSON fields instead of rewriting large blobs per change.
- `memory/common/cfx-patterns.md` -> Player Persistence Pattern is a concrete cache + dirty save shape; -> Save Sequence Guard Pattern covers overlapping saves of one row (retry, late autosave, second writer), -> Linked Trade Save Pattern value moving between two owners.

## Schema And Migrations

- Schema and migrations in a predictable server-side folder (`sql/`, `migrations/`), ordered, append-only, idempotent where possible.
- Add a resource schema version table when migrations apply automatically; never auto-run destructive migrations without an explicit operator action or backup path.
- Index identifiers, owner columns, foreign keys, lookup keys, high-frequency filters; searchable gameplay fields never only inside JSON blobs.
- Check `SHOW GRANTS` for the game user before releasing a migration: an `ALTER TABLE ... ADD COLUMN` that fails for lack of privilege leaves every join failing with `ERROR 1054` on the missing column. Gate joins on the column existing (an information_schema check), refuse with a "retry shortly" message, and log loudly (verified: live boot + offline harness).

## Performance

- Select only the columns needed; kill N+1 loops with `IN (...)`, joins, or one query per operation. Cache hot reference data in RAM when it is stable and has a cleanup/reload path.
- Never query in `Wait(0)` loops or on every client position/UI update; coalesce frequent state changes into one save.
- Slow-query/debug logging only while diagnosing, scoped to the resource. Startup slow queries matter less than gameplay stalls.
- Batch saves of existing rows with one multi-row `UPDATE t JOIN (SELECT ? AS pk, ? AS col UNION ALL SELECT ?, ?) v ON t.pk = v.pk SET t.col = v.col` per statement shape instead of N single-row updates in a transaction: 0.25-0.28 s -> 0.14-0.15 s per 10k rows and 499 fewer round-trips per batch (verified: MariaDB 12.3.3 benchmark).
  - Collapse duplicate keys to the newest row before building the statement; with a duplicate key in the derived table MariaDB picks the winning value non-deterministically.
  - Send variable row counts through the text protocol (`MySQL.update`), not `MySQL.prepare`: every batch size is another prepared statement and fills the per-connection cache up to `max_prepared_stmt_count` (16382).
  - Cap rows per statement in gameplay-time lanes (about 16): parameter binding runs on svMain, ~29 us per row at 2048 players.
- Do not build every player's save row in one frame: at 2048 players that was a 222 ms svMain frame; 150 players per frame with `Wait(0)` between chunks cut the worst frame to 69 ms (wall time 0.36 s -> 0.86 s). Prefer a time budget (~8 ms per frame) measured with `os.nanotime` over a fixed count (verified: 2048-player save waves).
- Calling oxmysql (or any JS resource) from Lua packs the arguments with msgpack on svMain before the query exists: ~31 ms of a ~45-50 ms save burst at 2048 players, of which 15.7 ms was packing 3.8 MB of rows inside the JS `msgpack.js`. Split large parameter arrays across frames; this cost never shows up as database time (verified: measured benchmark, 2048 players).
- Server `SetResourceKvp*`/`DeleteResourceKvp` fsync the WAL on every call (~0.6 ms each, so 500 writes in a loop stall the tick ~300 ms). For bulk writes use the `*NoSync` variants plus one `FlushResourceKvp()`; NoSync data survives `kill -9` but not power loss before that flush (verified: `ServerKVScriptFunctions.cpp`, FXServer 35945).

## Error Handling And Logging

- Log failures with resource name, query purpose, source/identifier when relevant, bounded error message - never payloads with secrets, tokens, webhooks, passwords, authorization headers or large JSON blobs.
- Retry transient save failures in a capped window, failure still visible.
- Failed persistence must be explicit - retry, mark dirty again, reject the action or roll back in-memory state - in a path that actually runs on error: a `pcall` around `.await`, or a callback with `mysql_option 'return_callback_errors'` declared (see OxMySQL API Shape above).
- A MariaDB outage is silent in resource logs: oxmysql queues the queries and runs them when the connection returns, so `.await` simply hangs, nothing errors and nothing rolls back. Bound long awaits with your own watchdog and confirm the outage in the oxmysql/MariaDB logs (verified: live connection-loss test).
- Never silently create missing critical rows in response to untrusted client input.

## Review Questions

- Player-controlled value reaching SQL unvalidated?
- Action needing a transaction, conditional update or in-flight marker?
- Query inside a loop, tick, callback spam or NUI spam path?
- Database dependency declared and loaded before this server file?
- Failed save keeping data dirty or otherwise recovering?
- Migrations safe to rerun against existing production data?
- Indexes on the columns used in frequent filters and joins?
