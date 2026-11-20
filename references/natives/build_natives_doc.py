#!/usr/bin/env python3
"""Regenerate `fivem-gta5-natives.md` from a clone of citizenfx/natives.

The GTA V / FiveM native reference is a single-file build of the per-native
markdown in https://github.com/citizenfx/natives (namespace folders, one `.md`
per native). This script rebuilds that single file in the exact format the
reference uses, so a refresh picks up natives added upstream without hand edits.

Usage:
    git clone --depth 1 https://github.com/citizenfx/natives /path/to/natives
    python3 references/natives/build_natives_doc.py /path/to/natives \\
        -o references/natives/fivem-gta5-natives.md

Pass --selftest to run the parser/emit fixtures.

LICENSE NOTE: citizenfx/natives ships no LICENSE file (verified at build time
and recorded in references/natives/SOURCES.md). The redistribution terms of its
content are unconfirmed. This script only transforms content you cloned; whether
to publish the regenerated file in a public package is your call, and the repo's
own policy says not to publish it where upstream terms cannot be confirmed.

RDR3/RedM is NOT covered: `redm-rdr3-natives.md` is built from a different,
enriched source (see SOURCES.md), not from this repo.

Pure standard library.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

TITLE = "GTA V / FiveM Natives — Complete Reference"
HASH_RE = re.compile(r"0x[0-9A-Fa-f]+")
# Source param bullets use either `*` or `-` as the list marker.
PARAM_RE = re.compile(r"^[*-]\s+\*\*(?P<name>[^*]+)\*\*\s*:\s*(?P<desc>.*)$")
SIG_PARAMS_RE = re.compile(r"\((.*)\)", re.DOTALL)
# CFX prefixes a `cs_type(...)` codegen/marshalling hint onto the return type or
# a parameter (e.g. `cs_type(int) BOOL FOO()`, `cs_type(Any) Hash garageHash`).
# It is not part of the C type, so strip it before reading types or the name.
CS_TYPE_RE = re.compile(r"cs_type\([^)]*\)\s*")


def _clean_sig(signature: str) -> str:
    return CS_TYPE_RE.sub("", signature).strip()


def _text_has_body(buf, i) -> bool:
    """True if a heading at buf[i] is followed by real content before the next
    heading, so empty sections (e.g. an empty `## Return value`) are dropped."""
    j = i + 1
    while j < len(buf):
        if re.match(r"^#{1,6}\s+\S", buf[j]):
            break
        if buf[j].strip():
            return True
        j += 1
    return False


def read_blocks(lines, start):
    """Yield (kind, content_lines) for the body after the name heading.
    kind is 'fence:<lang>' for a code fence or 'text' for a run of plain lines."""
    i = start
    n = len(lines)
    while i < n:
        line = lines[i]
        fence = re.match(r"^```(\w*)\s*$", line)
        if fence:
            lang = fence.group(1)
            body = []
            i += 1
            while i < n and not re.match(r"^```\s*$", lines[i]):
                body.append(lines[i])
                i += 1
            i += 1  # closing fence
            yield (f"fence:{lang}", body)
        else:
            body = []
            while i < n and not re.match(r"^```(\w*)\s*$", lines[i]):
                body.append(lines[i])
                i += 1
            yield ("text", body)


def parse_signature_params(signature: str):
    """Return [(ctype, name)] from a C signature's parameter list."""
    signature = _clean_sig(signature)
    m = SIG_PARAMS_RE.search(signature)
    if not m:
        return []
    inner = m.group(1).strip()
    if not inner:
        return []
    pairs = []
    for raw in inner.split(","):
        part = raw.strip()
        if not part or part == "void":
            continue
        toks = part.split()
        if len(toks) >= 2:
            pairs.append((" ".join(toks[:-1]), toks[-1].lstrip("*")))
        else:
            pairs.append(("", toks[-1].lstrip("*")))
    return pairs


def parse_native(path: Path, namespace: str):
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    # The first `## ` line is the native-name heading. It is sometimes empty
    # (the name then lives only in the C signature), so capture it even when
    # blank and resolve the real name from the signature below.
    heading = None
    name_idx = None
    for idx, line in enumerate(lines):
        m = re.match(r"^##\s*(.*?)\s*$", line)
        if m:
            heading = m.group(1).strip()
            name_idx = idx
            break
    if name_idx is None:
        return None

    blocks = list(read_blocks(lines, name_idx + 1))

    # First code fence holds `// 0x... [0x...]` then the signature.
    hashes, signature = [], None
    first_fence_consumed = False
    rendered = []
    for kind, body in blocks:
        if kind.startswith("fence:") and not first_fence_consumed:
            first_fence_consumed = True
            sig_lines = []
            for b in body:
                s = b.strip()
                if s.startswith("//"):
                    found = HASH_RE.findall(s)
                    if found:
                        hashes = found
                        continue
                sig_lines.append(b)
            signature = " ".join(l.strip() for l in sig_lines if l.strip())
            rendered.append(("signature", signature))
        elif kind.startswith("fence:"):
            rendered.append(("fence", (kind.split(":", 1)[1], body)))
        else:
            rendered.append(("text", body))

    # Return type and function name come from the signature once the
    # `cs_type(...)` marshalling hints are stripped: `<rettype...> NAME(params)`.
    rettype, funcname = "void", ""
    if signature:
        before = _clean_sig(signature).split("(", 1)[0].strip()
        toks = before.split()
        if len(toks) >= 2:
            rettype = " ".join(toks[:-1])
            funcname = toks[-1].lstrip("*")
        elif len(toks) == 1:
            funcname = toks[-1].lstrip("*")

    # Resolve the native name: the heading when present, else the signature's
    # function name (files with an empty heading carry the name only there).
    name = heading or funcname
    if not name:
        return None

    return {
        "name": name,
        "namespace": namespace,
        "hashes": hashes,
        "signature": signature or f"void {name}();",
        "rettype": rettype,
        "rendered": rendered,
        "signature_params": parse_signature_params(signature or ""),
    }


def emit_native(nat) -> list[str]:
    out = [f"### `{nat['name']}`", ""]
    hash_bits = [f"`{h}`" for h in nat["hashes"]] or ["`?`"]
    out.append(" · ".join(hash_bits) + f" · returns `{nat['rettype']}`")
    out.append("")
    out.append("```c")
    out.append(nat["signature"])
    out.append("```")
    out.append("")

    type_by_name = {name: ctype for ctype, name in nat["signature_params"]}

    for kind, payload in nat["rendered"]:
        if kind == "signature":
            continue
        if kind == "fence":
            lang, body = payload
            out.append(f"```{lang}")
            out.extend(body)
            out.append("```")
            out.append("")
        else:  # text
            buf = payload
            idx = 0
            while idx < len(buf):
                line = buf[idx]
                heading = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
                param = PARAM_RE.match(line)
                if heading:
                    # Drop headings with no body (e.g. an empty `## Return value`).
                    if _text_has_body(buf, idx):
                        out.append(f"**{heading.group(1).strip()}:**")
                        out.append("")
                elif param:
                    pname = param.group("name").strip()
                    ctype = type_by_name.get(pname, "")
                    label = f"{ctype} {pname}".strip()
                    desc = param.group("desc").strip()
                    out.append(f"- `{label}` — {desc}" if desc else f"- `{label}`")
                elif line.strip() == "":
                    if out and out[-1] != "":
                        out.append("")
                else:
                    out.append(line)
                idx += 1
            if out and out[-1] != "":
                out.append("")

    out.append("---")
    out.append("")
    return out


def build(root: Path) -> str:
    namespaces = sorted(
        d for d in root.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )
    sections = {}
    for ns_dir in namespaces:
        ns = ns_dir.name
        natives = []
        for md in sorted(ns_dir.glob("*.md")):
            nat = parse_native(md, ns)
            if nat:
                natives.append(nat)
        natives.sort(key=lambda x: x["name"])
        if natives:
            sections[ns] = natives

    total = sum(len(v) for v in sections.values())
    ns_count = len(sections)

    lines = [
        f"# {TITLE}",
        "",
        f"All **{total} natives** across **{ns_count} namespaces**, with per-native "
        "documentation (signature, parameters, return value, examples) taken verbatim "
        "from the source repo.",
        "",
        "Single-file build of `https://github.com/citizenfx/natives` (branch `main`, "
        "GTA V/FiveM). Original per-native markdown at `https://docs.fivem.net/natives/`. "
        "Do not edit by hand — regenerate from the repo.",
        "",
        "## Contents",
        "",
    ]
    for ns in sections:
        anchor = ns.lower()
        lines.append(f"- [{ns}](#{anchor}) ({len(sections[ns])})")
    lines.append("")

    for ns, natives in sections.items():
        lines.append(f'<a id="{ns.lower()}"></a>')
        lines.append(f"## {ns}")
        lines.append("")
        lines.append(f"{len(natives)} natives. [↑ Contents](#contents)")
        lines.append("")
        for nat in natives:
            lines.extend(emit_native(nat))

    return "\n".join(lines).rstrip() + "\n"


SELFTEST_FILE = """---
ns: ENTITY
---
## GET_ENTITY_HEALTH

```c
// 0xEEF059FAD016D209 0x8E3222B7
int GET_ENTITY_HEALTH(Entity entity);
```

## Parameters
* **entity**: The entity to check

## Return value
The health as an integer.
"""

# Exercises: a `cs_type(...)` return prefix (real return is BOOL, not cs_type),
# a `cs_type(...)` param prefix (type is Hash), a dash-bulleted param with no
# description, and an empty `## Return value` that must be dropped.
SELFTEST_FILE_CS = """---
ns: TEST
aliases: ["0x1234ABCD"]
---
## DO_THING

```c
// 0x1234ABCD 0xDEADBEEF
cs_type(int) BOOL DO_THING(cs_type(Any) Hash item, int count);
```

## Parameters
- **item**:
- **count**: how many

## Return value
"""


def selftest() -> int:
    ok = True
    with tempfile.TemporaryDirectory() as d:
        ns = Path(d) / "ENTITY"
        ns.mkdir()
        (ns / "GetEntityHealth.md").write_text(SELFTEST_FILE, encoding="utf-8")
        ns2 = Path(d) / "TEST"
        ns2.mkdir()
        (ns2 / "DoThing.md").write_text(SELFTEST_FILE_CS, encoding="utf-8")

        nat = parse_native(ns / "GetEntityHealth.md", "ENTITY")
        if nat["name"] != "GET_ENTITY_HEALTH":
            ok = False; print("selftest FAIL: name")
        if nat["hashes"] != ["0xEEF059FAD016D209", "0x8E3222B7"]:
            ok = False; print("selftest FAIL: hashes", nat["hashes"])
        if nat["rettype"] != "int":
            ok = False; print("selftest FAIL: rettype", nat["rettype"])

        cs = parse_native(ns2 / "DoThing.md", "TEST")
        if cs["name"] != "DO_THING":
            ok = False; print("selftest FAIL: cs name", cs["name"])
        if cs["rettype"] != "BOOL":
            ok = False; print("selftest FAIL: cs_type return not stripped:", cs["rettype"])
        if ("Hash", "item") not in cs["signature_params"]:
            ok = False; print("selftest FAIL: cs_type param not stripped:", cs["signature_params"])

        doc = build(Path(d))
        for needle in ["### `GET_ENTITY_HEALTH`",
                       "`0xEEF059FAD016D209` · `0x8E3222B7` · returns `int`",
                       "- `Entity entity` — The entity to check",
                       "**Return value:**",
                       '<a id="entity"></a>',
                       "### `DO_THING`",
                       "· returns `BOOL`",
                       "- `Hash item`",          # empty desc -> no trailing dash
                       "- `int count` — how many",
                       "All **2 natives** across **2 namespaces**"]:
            if needle not in doc:
                ok = False; print(f"selftest FAIL: missing {needle!r}")
        if "- `Hash item` —" in doc:
            ok = False; print("selftest FAIL: empty param desc emitted a trailing dash")
        # Exactly one Return value section: GET_ENTITY_HEALTH's; DO_THING's empty one dropped.
        if doc.count("**Return value:**") != 1:
            ok = False; print("selftest FAIL: empty Return value section not dropped:",
                              doc.count("**Return value:**"))
    print("native doc builder selftest passed." if ok else "native doc builder selftest FAILED.")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", nargs="?", help="path to a citizenfx/natives clone")
    parser.add_argument("-o", "--output", help="write here instead of stdout")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return selftest()
    if not args.source:
        parser.error("source directory required (or --selftest)")

    root = Path(args.source)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    doc = build(root)
    if args.output:
        Path(args.output).write_text(doc, encoding="utf-8")
        print(f"wrote {args.output} ({doc.count(chr(10))} lines, "
              f"{doc.count(chr(10).join([chr(10),'### ']).strip()) if False else doc.count('### ')} natives)")
    else:
        sys.stdout.write(doc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
