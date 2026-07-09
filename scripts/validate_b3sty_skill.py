#!/usr/bin/env python3
"""Validate b3sty-skill package wiring before publishing."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_PATHS = [
    "SKILL.md",
    "AGENTS.md",
    "README.md",
    "agents/openai.yaml",
    "skills/common/style.md",
    "skills/common/fxserver.md",
    "skills/common/native-rules.md",
    "skills/common/native-usage.md",
    "skills/common/resource-structure.md",
    "skills/common/security-performance.md",
    "skills/common/networking.md",
    "skills/common/nui.md",
    "skills/common/runtime.md",
    "skills/common/database.md",
    "skills/common/debugging.md",
    "skills/common/ox-lib.md",
    "skills/common/multi-resource.md",
    "skills/fivem/rules.md",
    "skills/redm/rules.md",
    "memory/common/README.md",
    "memory/common/native-bugs.md",
    "memory/common/common-errors.md",
    "memory/common/cfx-patterns.md",
    "memory/common/security-performance.md",
    "memory/fivem/README.md",
    "memory/fivem/native-bugs.md",
    "memory/redm/README.md",
    "memory/redm/native-bugs.md",
    "references/natives/fivem-gta5-natives.md",
    "references/natives/redm-rdr3-natives.md",
]


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_required_paths(failures: list[str]) -> None:
    for relative in REQUIRED_PATHS:
        if not (ROOT / relative).exists():
            fail(f"Missing required path: {relative}", failures)


def check_skill_frontmatter(skill_text: str, failures: list[str]) -> None:
    match = re.match(r"^---\n(?P<body>.*?)\n---\n", skill_text, re.DOTALL)
    if not match:
        fail("SKILL.md is missing YAML frontmatter", failures)
        return

    frontmatter = match.group("body")
    if "name: b3sty-skill" not in frontmatter:
        fail("SKILL.md frontmatter must include name: b3sty-skill", failures)
    if "description:" not in frontmatter:
        fail("SKILL.md frontmatter must include description", failures)
    if "RedM" not in frontmatter or "FiveM" not in frontmatter:
        fail("SKILL.md description should mention RedM and FiveM", failures)


def check_backticked_paths(markdown_path: Path, failures: list[str]) -> None:
    text = read_text(markdown_path)
    for value in re.findall(r"`([^`]+)`", text):
        normalized = value.replace("\\", "/")
        if not normalized.startswith(("skills/", "memory/", "references/", "agents/", "scripts/")):
            continue

        candidate = ROOT / normalized
        if not candidate.exists():
            relative = markdown_path.relative_to(ROOT).as_posix()
            fail(f"{relative} references missing path: {normalized}", failures)


SECTION_REF = re.compile(r"`((?:skills|memory|references)/[^`]+\.md)` -> ([^\n]+)")
_HEADING_CACHE: dict[Path, set[str]] = {}


def _headings(path: Path) -> set[str]:
    if path not in _HEADING_CACHE:
        _HEADING_CACHE[path] = {
            line.lstrip("#").strip()
            for line in read_text(path).splitlines()
            if line.startswith("#")
        }
    return _HEADING_CACHE[path]


def check_section_references(markdown_path: Path, failures: list[str]) -> None:
    """Validate `path.md` -> Section cross-references against real headings.

    Section names may be followed by prose ("... for the full rules") or list
    several sections; only the first section is validated, using the longest
    word-prefix that matches a heading in the target file.
    """
    text = read_text(markdown_path)
    for match in SECTION_REF.finditer(text):
        target = ROOT / match.group(1)
        if not target.exists():
            continue  # reported by check_backticked_paths

        headings = _headings(target)
        words = match.group(2).strip().split(" ")
        if not any(
            " ".join(words[:end]).rstrip(",.;:)") in headings
            for end in range(len(words), 0, -1)
        ):
            relative = markdown_path.relative_to(ROOT).as_posix()
            shown = " ".join(words[:8])
            fail(
                f"{relative} references missing section: {match.group(1)} -> {shown}",
                failures,
            )


def check_openai_yaml(failures: list[str]) -> None:
    text = read_text(ROOT / "agents/openai.yaml")
    if "display_name:" not in text:
        fail("agents/openai.yaml is missing interface.display_name", failures)
    if "short_description:" not in text:
        fail("agents/openai.yaml is missing interface.short_description", failures)
    if "$b3sty-skill" not in text:
        fail("agents/openai.yaml default_prompt must mention $b3sty-skill", failures)


def check_memory_readmes(failures: list[str]) -> None:
    for relative in ["memory/common/README.md", "memory/fivem/README.md", "memory/redm/README.md"]:
        text = read_text(ROOT / relative)
        if "Date:" not in text or "Game build:" not in text:
            fail(f"{relative} should include Date and Game build template fields", failures)


def check_reference_toc(failures: list[str]) -> None:
    for relative in ["skills/common/security-performance.md", "memory/common/cfx-patterns.md"]:
        text = read_text(ROOT / relative)
        if "## Contents" not in text:
            fail(f"{relative} is long and should include a Contents section", failures)


def main() -> int:
    failures: list[str] = []
    skill_text = read_text(ROOT / "SKILL.md")

    check_required_paths(failures)
    check_skill_frontmatter(skill_text, failures)
    check_openai_yaml(failures)
    check_memory_readmes(failures)
    check_reference_toc(failures)

    # Validate cross-links (backticked skill/memory/references paths) everywhere
    # rules live, not only the top-level entry points. Skip the large generated
    # native reference dumps; they are searched with rg, not cross-linked.
    generated_natives = {
        ROOT / "references" / "natives" / "fivem-gta5-natives.md",
        ROOT / "references" / "natives" / "redm-rdr3-natives.md",
    }
    cross_link_files = [ROOT / "SKILL.md", ROOT / "README.md", ROOT / "AGENTS.md"]
    cross_link_files += sorted((ROOT / "skills").rglob("*.md"))
    cross_link_files += sorted((ROOT / "memory").rglob("*.md"))
    cross_link_files += [
        path for path in (ROOT / "references").rglob("*.md") if path not in generated_natives
    ]
    for markdown_path in cross_link_files:
        check_backticked_paths(markdown_path, failures)
        check_section_references(markdown_path, failures)

    if failures:
        print("b3sty-skill validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("b3sty-skill validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
