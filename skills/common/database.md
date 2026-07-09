# Database Rules

Use this file when a RedM/FiveM resource reads or writes SQL, owns persisted player/resource state, changes schema, or depends on OxMySQL/mysql-async style APIs.

## Defaults

- Keep database access server-side only.
- Prefer `oxmysql` for new SQL work when the project accepts that dependency.
- Do not add a database dependency to a resource that can stay config-only or framework-state-only.
- Keep query code close to the feature unless the same query is reused enough to justify a small helper.
- Validate public event, callback, command, export, and NUI input before it reaches SQL.
- Run the game database as a dedicated user with grants limited to the game schema (no `SUPER`/`FILE`/`GRANT`, never root), reachable only from the server host or a private network. See `skills/common/security-performance.md` -> Server Hardening And Operations.
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
- Prefer `?` placeholders for ordinary OxMySQL queries. Named placeholders (`@name`) are supported too (require the resource's `namedPlaceholders` setting). ([oxmysql](https://overextended.dev/docs/oxmysql))
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
- Wrap multi-step valuable writes (debit + grant) in one `MySQL.transaction.await({ ... })` so they commit together or roll back together ([oxmysql transaction](https://overextended.dev/docs/oxmysql/Functions/transaction)). See `skills/common/security-performance.md` -> Database And Persistence and Give-Value Event Hardening for the race-safe pattern.

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
- Always handle `nil`, `false`, empty results, and zero affected rows explicitly.

## Transactions And Atomic Writes

- Use a transaction for multi-query valuable state changes such as transfers, purchases, crafting, inventories, ownership changes, and claim rewards.
- Treat a transaction result of `false` as a rejected mutation and do not apply in-memory success state.
- Prefer one conditional update over check-then-update when one row can enforce the rule.
- For money and inventory, avoid flows that read a balance, yield, and then write a new balance without locking, a transaction, or a conditional update.
- Use unique constraints plus `INSERT ... ON DUPLICATE KEY UPDATE` for upsert behavior.
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

## Schema And Migrations

- Put initial schema and migrations in a predictable server-side folder such as `sql/` or `migrations/`.
- Keep migration files ordered and append-only.
- Add a resource schema version table when the resource needs to apply migrations automatically.
- Do not auto-run destructive migrations without an explicit operator action or backup path.
- Write migrations to be idempotent when possible.
- Add indexes for identifiers, owner columns, foreign keys, lookup keys, and high-frequency filters.
- Avoid storing searchable gameplay fields only inside JSON blobs.

## Performance

- Select only the columns needed by the feature.
- Avoid N+1 query loops; batch with `IN (...)`, joins, or one query per resource operation.
- Cache hot reference data in RAM when it is stable and has a cleanup/reload path.
- Do not run database queries in `Wait(0)` loops or every client position/UI update.
- Coalesce frequent state changes into one save.
- Use slow-query/debug logging temporarily while diagnosing, then turn it off or scope it to the resource.
- Treat startup slow queries differently from gameplay slow queries; gameplay stalls matter more.

## Error Handling And Logging

- Log database failures with resource name, query purpose, source/identifier when relevant, and a bounded error message.
- Do not log full payloads containing secrets, tokens, webhooks, passwords, authorization headers, or large JSON blobs.
- Use retry windows for transient save failures, but cap retries and keep failure visible.
- Make failed persistence behavior explicit: retry, mark dirty again, reject the action, or roll back in-memory state.
- Do not silently create missing critical rows in response to untrusted client input.

## Review Questions

- Can any player-controlled value reach SQL without validation?
- Does this action need a transaction, conditional update, or in-flight marker?
- Is this query called in a loop, tick, callback spam path, or NUI spam path?
- Is the database dependency declared and loaded before this server file?
- Does a failed save keep data dirty or otherwise recover?
- Are migrations safe to rerun and safe for existing production data?
- Are indexes present for the columns used in frequent filters and joins?
