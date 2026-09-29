#!/usr/bin/env python3
"""Syntax-check every ```lua block in the skill docs with a Lua 5.4 compiler.

CfxLua extensions are rewritten to plain Lua 5.4 first (compound assignment,
backtick hashes), so the check proves the example parses, not that it runs.
Put `<!-- lua-check: skip -->` on the line before a fence to skip a block that
is intentionally partial.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC_GLOBS = ["SKILL.md", "skills/**/*.md", "memory/**/*.md", "commands/*.md"]
SKIP_MARKER = "<!-- lua-check: skip -->"
FENCE = re.compile(r"^(?P<indent>[ \t]*)```lua[ \t]*$")
COMPOUND = re.compile(
    r"^(?P<lhs>[ \t]*[A-Za-z_][\w.:\[\]\"']*)[ \t]*(?:\+|-|\*|/|<<|>>|&|\||\^)=(?!=)(?P<rhs>.*)$"
)
BACKTICK_HASH = re.compile(r"`[^`\n]*`")


def to_plain_lua(code: str) -> str:
    lines = []
    for line in code.splitlines():
        line = BACKTICK_HASH.sub("0", line)
        match = COMPOUND.match(line)
        if match:
            line = f"{match.group('lhs')} = ({match.group('rhs').strip()})"
        lines.append(line)
    return "\n".join(lines) + "\n"


def lua_blocks(path: Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        match = FENCE.match(lines[index])
        if not match:
            index += 1
            continue

        skip = index > 0 and lines[index - 1].strip() == SKIP_MARKER
        indent = len(match.group("indent"))
        start = index + 1
        body = []
        index += 1
        while index < len(lines) and lines[index].strip() != "```":
            body.append(lines[index][indent:] if lines[index][:indent].strip() == "" else lines[index])
            index += 1
        index += 1
        if not skip:
            yield start, "\n".join(body)


def find_compiler():
    for name in ("luac5.4", "luac"):
        binary = shutil.which(name)
        if binary:
            version = subprocess.run([binary, "-v"], capture_output=True, text=True)
            if "5.4" in (version.stdout + version.stderr):
                return lambda source: compile_with_luac(binary, source)
    try:
        from lupa import lua54  # type: ignore

        runtime = lua54.LuaRuntime()
        loader = runtime.eval("function(s) local f, err = load(s, '=example') return err end")
        return lambda source: loader(source)
    except ImportError:
        return None


def compile_with_luac(binary: str, source: str):
    with tempfile.NamedTemporaryFile("w", suffix=".lua", delete=False, encoding="utf-8") as handle:
        handle.write(source)
        name = handle.name
    try:
        result = subprocess.run([binary, "-p", name], capture_output=True, text=True)
        return (result.stderr or result.stdout).replace(name, "example").strip() or None
    finally:
        Path(name).unlink()


def main() -> int:
    compile_source = find_compiler()
    if compile_source is None:
        print("No Lua 5.4 compiler found: install lua5.4 (luac5.4) or `pip install lupa`.")
        return 2

    paths = sorted({path for pattern in DOC_GLOBS for path in ROOT.glob(pattern)})
    checked = 0
    failures = []
    for path in paths:
        for line, code in lua_blocks(path):
            checked += 1
            error = compile_source(to_plain_lua(code))
            if error:
                failures.append(f"{path.relative_to(ROOT).as_posix()}:{line}: {error}")

    if failures:
        print(f"Lua example check failed ({len(failures)} of {checked} blocks):")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"Lua example check passed ({checked} blocks).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
