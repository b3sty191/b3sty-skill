#!/usr/bin/env python3
"""Generate a deterministic audit coverage ledger for a RedM/FiveM resource.

Scans a resource directory for every place untrusted input crosses into the
resource - net events, built-in client events, NUI callbacks, commands,
exports, framework/ox_lib callbacks, HTTP handlers, SQL calls, replicated
state-bag writes, and browser XSS sinks - and writes one ledger unit per
surface so an audit can tick every boundary off instead of eyeballing a grep.

The ledger is the coverage claim: a reviewer closes a unit only after reading
its handler. This is a lexical pre-pass, not a parser; it over-reports rather
than miss a boundary, and every unit carries file:line so a human confirms it.

Usage:
    python3 b3sty_audit_ledger.py <resource-dir> [-o ledger.json]
    python3 b3sty_audit_ledger.py --selftest

Pure standard library. Run with -I on untrusted trees.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

# Each rule: (surface, side, regex). `side` is where the handler runs, which
# decides how hostile the input is: a client can forge anything a server event
# or NUI callback receives. The regex captures the identifying name in group 1
# where there is one.
LUA_RULES = [
    ("net_event", "server", re.compile(r"""RegisterNetEvent\s*\(\s*["']([^"']+)["']""")),
    ("net_event", "server", re.compile(r"""RegisterServerEvent\s*\(\s*["']([^"']+)["']""")),
    ("nui_callback", "client", re.compile(r"""RegisterNUICallback\s*\(\s*["']([^"']+)["']""")),
    ("command", "server", re.compile(r"""RegisterCommand\s*\(\s*["']([^"']+)["']""")),
    ("callback", "server", re.compile(r"""lib\.callback\.register\s*\(\s*["']([^"']+)["']""")),
    ("callback", "server", re.compile(r"""(?:ESX\.RegisterServerCallback|QBCore\.Functions\.CreateCallback|RSGCore\.Functions\.CreateCallback|VORPcore\.addRpcCallback)\s*\(\s*["']([^"']+)["']""")),
    ("export", "either", re.compile(r"""exports\s*\(\s*["']([^"']+)["']""")),
    ("http_handler", "server", re.compile(r"""SetHttpHandler\s*\(""")),
    ("sql", "server", re.compile(r"""(?:MySQL\.\w+(?:\.await)?|exports\.oxmysql:\w+|exports\.ghmattimysql:\w+|exports\[['"]mysql-async['"]\])\s*\(""")),
    ("state_bag", "server", re.compile(r"""AddStateBagChangeHandler\s*\(\s*["']([^"']*)["']""")),
]

# Built-in events the client can fire at the server; validate like any
# :server: event. FiveM-only ones are tagged so a RedM review does not chase
# a surface that cannot exist.
BUILTIN_EVENTS = {
    "weaponDamageEvent": "both",
    "explosionEvent": "both",
    "startProjectileEvent": "both",
    "respawnPlayerPedEvent": "both",
    "giveWeaponEvent": "both",
    "removeWeaponEvent": "both",
    "clearPedTasksEvent": "both",
    "ptFxEvent": "fivem",
    "removeAllWeaponsEvent": "fivem",
    "fireEvent": "fivem",
}
BUILTIN_RE = re.compile(
    r"""AddEventHandler\s*\(\s*["'](""" + "|".join(map(re.escape, BUILTIN_EVENTS)) + r""")["']"""
)

# Browser XSS sinks in NUI frontend files: a player-controlled string reaching
# one of these runs as the victim and can drive every NUI callback.
WEB_RULES = [
    ("xss", "client", re.compile(r"""\.innerHTML\s*=""")),
    ("xss", "client", re.compile(r"""\.outerHTML\s*=""")),
    ("xss", "client", re.compile(r"""insertAdjacentHTML\s*\(""")),
    ("xss", "client", re.compile(r"""dangerouslySetInnerHTML""")),
    ("xss", "client", re.compile(r"""v-html""")),
    ("xss", "client", re.compile(r"""\{@html""")),
    ("xss", "client", re.compile(r"""document\.write\s*\(""")),
]

LUA_EXT = {".lua"}
WEB_EXT = {".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".html", ".htm"}
SKIP_DIRS = {".git", "node_modules", "dist", "build", ".yarn", "vendor", "stream"}
MAX_FILE_BYTES = 2_000_000


def iter_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts[:-1]):
            continue
        ext = path.suffix.lower()
        if ext in LUA_EXT or ext in WEB_EXT:
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield path, ext


def strip_comment(line: str, ext: str) -> str:
    """Drop the obvious single-line comment so a commented-out handler does
    not seed a unit. Block comments and strings are left alone on purpose -
    over-reporting is safer than dropping a live boundary."""
    marker = "--" if ext in LUA_EXT else "//"
    idx = line.find(marker)
    return line[:idx] if idx != -1 else line


def unit_id(surface: str, rel: str, name: str, line: int) -> str:
    digest = hashlib.sha1(f"{surface}\0{rel}\0{name}\0{line}".encode("utf-8")).hexdigest()
    return f"{surface}-{digest[:10]}"


def scan_text(text: str, rel: str, ext: str) -> list[dict]:
    units = []
    rules = LUA_RULES if ext in LUA_EXT else WEB_RULES
    include_builtin = ext in LUA_EXT
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = strip_comment(raw, ext)
        if not line.strip():
            continue
        for surface, side, pattern in rules:
            for match in pattern.finditer(line):
                name = match.group(1) if match.groups() else ""
                units.append({
                    "unit_id": unit_id(surface, rel, name, lineno),
                    "surface": surface,
                    "side": side,
                    "name": name,
                    "file": rel,
                    "line": lineno,
                    "snippet": raw.strip()[:200],
                    "status": "planned",
                })
        if include_builtin:
            for match in BUILTIN_RE.finditer(line):
                name = match.group(1)
                units.append({
                    "unit_id": unit_id("builtin_event", rel, name, lineno),
                    "surface": "builtin_event",
                    "side": BUILTIN_EVENTS[name],
                    "name": name,
                    "file": rel,
                    "line": lineno,
                    "snippet": raw.strip()[:200],
                    "status": "planned",
                })
    return units


def build_ledger(root: Path) -> list[dict]:
    units: list[dict] = []
    for path, ext in iter_files(root):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        units.extend(scan_text(text, rel, ext))
    units.sort(key=lambda u: (u["surface"], u["file"], u["line"], u["name"]))
    return units


SELFTEST_LUA = """
RegisterNetEvent("shop:server:buy", function(data) end)
AddEventHandler("explosionEvent", function(sender, ev) end)
RegisterNUICallback("buy", function(data, cb) end)   -- client boundary
-- RegisterNetEvent("dead:code") this is commented out
RegisterCommand("giveitem", function(src, args) end)
exports("GetBalance", function(src) end)
MySQL.update.await("UPDATE users SET money = ?", { 1 })
"""

SELFTEST_JS = """
document.getElementById("x").innerHTML = data.name;  // xss sink
const safe = foo.textContent;
"""


def selftest() -> int:
    lua = scan_text(SELFTEST_LUA, "core/server.lua", ".lua")
    got = sorted({u["surface"] for u in lua})
    want = {"net_event", "builtin_event", "nui_callback", "command", "export", "sql"}
    ok = True
    if got != sorted(want):
        print(f"selftest FAIL: lua surfaces {got} != {sorted(want)}")
        ok = False
    if any(u["name"] == "dead:code" for u in lua):
        print("selftest FAIL: commented-out handler was seeded")
        ok = False
    nui = [u for u in lua if u["surface"] == "nui_callback"]
    if not nui or nui[0]["side"] != "client":
        print("selftest FAIL: NUI callback side")
        ok = False
    web = scan_text(SELFTEST_JS, "html/app.js", ".js")
    if not any(u["surface"] == "xss" for u in web):
        print("selftest FAIL: xss sink not found")
        ok = False
    if len(web) != 1:
        print(f"selftest FAIL: expected 1 web unit, got {len(web)}")
        ok = False
    # Stable IDs: same input twice gives identical ledger.
    if json.dumps(scan_text(SELFTEST_LUA, "core/server.lua", ".lua")) != json.dumps(lua):
        print("selftest FAIL: ledger is not deterministic")
        ok = False
    print("b3sty audit ledger selftest passed." if ok else "b3sty audit ledger selftest FAILED.")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", nargs="?", help="resource directory to scan")
    parser.add_argument("-o", "--output", help="write ledger JSON here instead of stdout")
    parser.add_argument("--selftest", action="store_true", help="run built-in fixtures and exit")
    args = parser.parse_args()

    if args.selftest:
        return selftest()
    if not args.target:
        parser.error("target directory required (or --selftest)")

    root = Path(args.target)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    units = build_ledger(root)
    payload = json.dumps(units, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
        counts: dict[str, int] = {}
        for unit in units:
            counts[unit["surface"]] = counts.get(unit["surface"], 0) + 1
        summary = ", ".join(f"{k}:{v}" for k, v in sorted(counts.items())) or "none"
        print(f"{len(units)} units -> {args.output} ({summary})")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
