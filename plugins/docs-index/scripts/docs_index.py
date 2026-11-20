#!/usr/bin/env python3
"""docs-index: set up and check a project's docs/ tree. Standard library only; reads and writes local files only.

  docs-index init  [--root DIR] [--claude-md] [--agents-md]
  docs-index check [--root DIR] [--json]
  docs-index check --hook      Claude Code Stop hook: reads the hook's JSON on stdin, never writes a file

The tree: docs/research, docs/decisions, docs/guides and docs/reference; docs/INDEX.md lists every document with a
one-line summary; docs/BIBLIOGRAPHY.md records every source once, in MLA format, with a citation key and
*Cited by:* links back to the documents that use it.

Exit status of check: 0 clean, 1 problems found, 2 the project has no docs/INDEX.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SECTIONS = (("research", "Research"), ("decisions", "Decisions"), ("guides", "Guides"), ("reference", "Reference"))
FOLDER_FOR_HEADING = {heading.lower(): folder for folder, heading in SECTIONS}
INDEX_START, INDEX_END = "<!-- INDEX:START -->", "<!-- INDEX:END -->"
BIB_START, BIB_END = "<!-- BIBLIOGRAPHY:START -->", "<!-- BIBLIOGRAPHY:END -->"
BLOCK_START, BLOCK_END = "<!-- docs-index begin -->", "<!-- docs-index end -->"
HOOK_MODES = ("off", "warn", "block")

ENTRY = re.compile(r"^- \*\*\[(?P<title>[^\]]+)\]\((?P<path>[^)\s]+)\)\*\*")
HEADING = re.compile(r"^## (?P<name>.+?)\s*$")
BIB_ID = re.compile(r'<a id="(?P<key>[A-Za-z0-9][A-Za-z0-9_-]*)"></a>')
BIB_LINK = re.compile(r"BIBLIOGRAPHY\.md#(?P<key>[A-Za-z0-9][A-Za-z0-9_-]*)")
MD_LINK = re.compile(r"\]\((?P<path>[^)\s#]+)(?:#[^)\s]*)?\)")
# Fenced code blocks and inline code: examples there are not citations.
CODE = re.compile(r"^(`{3,}|~{3,})[^\n]*\n.*?^\1[ \t]*$|`[^`\n]*`", re.M | re.S)

INDEX_TEMPLATE = f"""# Documentation index

Research, decisions, guides and reference notes for this project. Each entry links a document under docs/ and
gives a one-line summary; sources are in [BIBLIOGRAPHY.md](BIBLIOGRAPHY.md).

{INDEX_START}
## Research
## Decisions
## Guides
## Reference
{INDEX_END}
"""

BIB_TEMPLATE = f"""# Bibliography

Works cited in this project's documents, in MLA format. Each source appears once, starts with its citation key
as an anchor, and has a *Cited by:* line linking every document that uses it.

{BIB_START}
{BIB_END}
"""

CLAUDE_BLOCK = f"""{BLOCK_START}
## Project knowledge in docs/

This project files what it learns in four folders: `docs/research/`, `docs/decisions/`, `docs/guides/` and
`docs/reference/`. `docs/INDEX.md` is the table of contents, one entry and a one-line summary per document.
`docs/BIBLIOGRAPHY.md` lists each source a single time, in MLA style, under a key that links back to the documents
citing it. After research, or when a result is worth saving, suggest filing it with the docs-index skill.
Cite a source for every factual claim; mark anything uncited as unverified.
{BLOCK_END}
"""

AGENTS_BLOCK = f"""{BLOCK_START}
## Project knowledge in docs/

Notes this project keeps go in one of four folders: `docs/research/`, `docs/decisions/`, `docs/guides/` or
`docs/reference/`. Two files tie them together, and the `docs-index` command checks both.

When you save a document:
1. Put it in the folder that fits, then give it an entry in `docs/INDEX.md`, inside the INDEX marker comments and
   under that folder's heading. The entry is `- **[Title](<folder>/<file>.md)** — YYYY-MM-DD`, then a line
   indented by two spaces that sums the document up, then, only if it cites sources, an indented `Sources:` line
   with one `BIBLIOGRAPHY.md#<key>` link per source.
2. Give each source one MLA entry in `docs/BIBLIOGRAPHY.md`, inside the BIBLIOGRAPHY marker comments: a line that
   begins `- <a id="<key>"></a>`, and under it an indented `*Cited by:*` line linking every document that uses it.
3. Cite a source for every factual claim; mark anything uncited as unverified.
4. Finish with `docs-index check` and clear every problem it lists. Exit code 2 means docs/ is not set up yet:
   run `docs-index init`. If the command is not installed, run
   `uv tool install <path to the docs-index plugin folder>`.
{BLOCK_END}
"""


@dataclass(frozen=True)
class Problem:
    code: str
    path: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.code} {self.path}:{self.line} {self.message}"


# ---------------------------------------------------------------- init

def init(root: Path, claude_md: bool = False, agents_md: bool = False) -> list[str]:
    """Create whatever is missing of the docs/ tree; never overwrite. Returns the paths created or changed."""
    docs = root / "docs"
    done: list[str] = []
    for folder, _ in SECTIONS:
        d = docs / folder
        if not d.is_dir():
            d.mkdir(parents=True)
            (d / ".gitkeep").write_text("", encoding="utf-8")
            done.append(f"docs/{folder}/")
    for name, text in (("INDEX.md", INDEX_TEMPLATE), ("BIBLIOGRAPHY.md", BIB_TEMPLATE)):
        if not (docs / name).exists():
            (docs / name).write_text(text, encoding="utf-8")
            done.append(f"docs/{name}")
    for wanted, name, block in ((claude_md, "CLAUDE.md", CLAUDE_BLOCK), (agents_md, "AGENTS.md", AGENTS_BLOCK)):
        if wanted and _append_block(root / name, block):
            done.append(name)
    return done


def _append_block(path: Path, block: str) -> bool:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if BLOCK_START in text:
        return False
    sep = "" if not text or text.endswith("\n\n") else ("\n" if text.endswith("\n") else "\n\n")
    path.write_text(text + sep + block, encoding="utf-8")
    return True


# ---------------------------------------------------------------- check

def _between(lines: list[str], start: str, end: str) -> tuple[int, int] | None:
    """Indexes (first, last) of the lines strictly between the two markers, or None."""
    try:
        a = next(i for i, x in enumerate(lines) if x.strip() == start)
        b = next(i for i, x in enumerate(lines) if x.strip() == end and i > a)
    except StopIteration:
        return None
    return a + 1, b


def _doc_files(docs: Path) -> list[str]:
    out = []
    for folder, _ in SECTIONS:
        base = docs / folder
        if base.is_dir():
            out += sorted(p.relative_to(docs).as_posix() for p in base.rglob("*.md") if p.is_file())
    return out


def _check_index(docs: Path, problems: list[Problem]) -> dict[str, set[str]]:
    """Index problems; returns the citation keys each listed document's Sources line names."""
    lines = (docs / "INDEX.md").read_text(errors="replace").splitlines()
    span = _between(lines, INDEX_START, INDEX_END)
    if span is None:
        problems.append(Problem("IDX-MARKERS", "docs/INDEX.md", 1, f"no {INDEX_START} ... {INDEX_END} block"))
        return {}
    listed: dict[str, int] = {}
    sources: dict[str, set[str]] = {}
    folder = None
    current = None
    for i in range(*span):
        line, n = lines[i], i + 1
        h = HEADING.match(line)
        if h:
            folder, current = FOLDER_FOR_HEADING.get(h.group("name").lower()), None
            continue
        m = ENTRY.match(line)
        if m:
            path = m.group("path")
            current = path
            if path in listed:
                problems.append(Problem("IDX-DUP", "docs/INDEX.md", n, f"{path} is already listed on line {listed[path]}"))
            listed.setdefault(path, n)
            if not (docs / path).is_file():
                problems.append(Problem("IDX-LINK", "docs/INDEX.md", n, f"{path} does not exist"))
            if folder and path.split("/")[0] != folder:
                problems.append(Problem("IDX-SECTION", "docs/INDEX.md", n, f"{path} is not in docs/{folder}/"))
            nxt = lines[i + 1] if i + 1 < span[1] else ""
            if not nxt.startswith("  ") or not nxt.strip() or nxt.strip().startswith("Sources:"):
                problems.append(Problem("IDX-SUMMARY", "docs/INDEX.md", n, f"{path} has no one-line summary"))
            continue
        if current and line.startswith("  "):
            sources.setdefault(current, set()).update(k.group("key") for k in BIB_LINK.finditer(line))
    for rel in _doc_files(docs):
        if rel not in listed:
            problems.append(Problem("IDX-UNLISTED", f"docs/{rel}", 1, "not listed in docs/INDEX.md"))
    return sources


def _check_bibliography(docs: Path, citing: dict[str, set[str]], problems: list[Problem]) -> None:
    bib = docs / "BIBLIOGRAPHY.md"
    if not bib.is_file():
        problems.append(Problem("BIB-MISSING", "docs/BIBLIOGRAPHY.md", 1, "no docs/BIBLIOGRAPHY.md"))
        return
    lines = bib.read_text(errors="replace").splitlines()
    span = _between(lines, BIB_START, BIB_END)
    if span is None:
        problems.append(Problem("BIB-MARKERS", "docs/BIBLIOGRAPHY.md", 1, f"no {BIB_START} ... {BIB_END} block"))
        return
    entries: dict[str, tuple[int, list[str] | None]] = {}
    key = None
    for i in range(*span):
        line, n = lines[i], i + 1
        if line.startswith("- "):
            m = BIB_ID.search(line)
            key = m.group("key") if m else None
            if key is None:
                problems.append(Problem("BIB-KEY", "docs/BIBLIOGRAPHY.md", n, "entry has no <a id=\"key\"></a> anchor"))
            elif key in entries:
                problems.append(Problem("BIB-DUP", "docs/BIBLIOGRAPHY.md", n, f"key {key!r} is already used"))
                key = None
            else:
                entries[key] = (n, None)
        elif key and "*Cited by:*" in line:
            n0, _ = entries[key]
            paths = [m.group("path") for m in MD_LINK.finditer(line)]
            entries[key] = (n0, paths)
            for p in paths:
                if not (docs / p).is_file():
                    problems.append(Problem("BIB-CITEDBY", "docs/BIBLIOGRAPHY.md", n, f"{key}: {p} does not exist"))
    for k, (n, paths) in entries.items():
        if paths is None:
            problems.append(Problem("BIB-CITEDBY", "docs/BIBLIOGRAPHY.md", n, f"{k}: no *Cited by:* line"))
    for k, docs_citing in sorted(citing.items()):
        if k not in entries:
            for doc in sorted(docs_citing):
                problems.append(Problem("BIB-KEY", f"docs/{doc}", 1, f"cites {k!r}, which is not in BIBLIOGRAPHY.md"))
            continue
        cited_by = set(entries[k][1] or [])
        for doc in sorted(docs_citing - cited_by):
            problems.append(Problem("BIB-BACKLINK", "docs/BIBLIOGRAPHY.md", entries[k][0],
                                    f"{k}: *Cited by:* does not link {doc}"))


def check(root: Path) -> list[Problem] | None:
    """Every problem in root's docs/ tree, or None when docs/INDEX.md does not exist."""
    docs = root / "docs"
    if not (docs / "INDEX.md").is_file():
        return None
    problems: list[Problem] = []
    citing: dict[str, set[str]] = {}
    for doc, keys in _check_index(docs, problems).items():
        for k in keys:
            citing.setdefault(k, set()).add(doc)
    for rel in _doc_files(docs):
        text = CODE.sub("", (docs / rel).read_text(errors="replace"))
        for m in BIB_LINK.finditer(text):
            citing.setdefault(m.group("key"), set()).add(rel)
    _check_bibliography(docs, citing, problems)
    return problems


# ---------------------------------------------------------------- Stop hook

def config_path() -> Path:
    env = os.environ.get("DOCS_INDEX_CONFIG")
    return Path(env).expanduser() if env else Path.home() / ".config" / "docs-index" / "config.yaml"


def hook_mode(path: Path | None = None) -> str:
    """The stop_hook value from the config file (off, warn or block); warn when unset or unreadable."""
    try:
        text = (path or config_path()).read_text()
    except OSError:
        return "warn"
    for line in text.splitlines():
        m = re.match(r"^\s*stop_hook\s*:\s*['\"]?(\w+)['\"]?\s*(?:#.*)?$", line)
        if m and m.group(1) in HOOK_MODES:
            return m.group(1)
    return "warn"


def _project_root(start: Path) -> Path | None:
    for d in (start, *start.parents):
        if (d / "docs" / "INDEX.md").is_file():
            return d
    return None


def run_hook(stdin) -> int:
    try:
        data = json.loads(stdin.read() or "{}")
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    mode = hook_mode()
    root = _project_root(Path(data.get("cwd") or os.getcwd()).resolve())
    if mode == "off" or root is None:
        return 0
    try:
        problems = check(root) or []
    except OSError:
        return 0
    if not problems:
        return 0
    shown = "; ".join(str(p) for p in problems[:5]) + (" ..." if len(problems) > 5 else "")
    text = f"docs-index: {len(problems)} problem(s) in docs/: {shown}. Run docs-index check and fix them."
    if mode == "block" and not data.get("stop_hook_active"):
        print(json.dumps({"decision": "block", "reason": text}))
    else:
        print(json.dumps({"systemMessage": text}))
    return 0


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None, stdin=None) -> int:
    ap = argparse.ArgumentParser(prog="docs-index", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init", help="create the docs/ tree, INDEX.md and BIBLIOGRAPHY.md (never overwrites)")
    p.add_argument("--root", default=".")
    p.add_argument("--claude-md", action="store_true", help="add the docs-index block to CLAUDE.md")
    p.add_argument("--agents-md", action="store_true", help="add the docs-index block to AGENTS.md (Codex)")
    p = sub.add_parser("check", help="report index and bibliography problems")
    p.add_argument("--root", default=".")
    p.add_argument("--json", action="store_true")
    p.add_argument("--hook", action="store_true", help="run as the Claude Code Stop hook")
    a = ap.parse_args(argv)
    if a.cmd == "init":
        done = init(Path(a.root), a.claude_md, a.agents_md)
        print("\n".join(f"created {x}" for x in done) if done else "nothing to do: docs/ is already set up")
        return 0
    if a.hook:
        return run_hook(stdin or sys.stdin)
    try:
        problems = check(Path(a.root))
    except OSError as e:
        print(f"error: {e}")
        return 1
    if problems is None:
        print("docs-index: no docs/INDEX.md here; run: docs-index init")
        return 2
    if a.json:
        print(json.dumps([asdict(p) for p in problems], indent=2))
    elif problems:
        print("\n".join(str(p) for p in problems))
    else:
        print("docs-index: docs/ is consistent")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
