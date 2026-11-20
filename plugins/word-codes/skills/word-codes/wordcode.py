"""Word codes: short adjective-animal phrases people can read on a phone and type at a Mac.

Reference implementation for the word-codes skill (stdlib only). Projects vendor this file, the two word lists and
prefixes.example.json, and pin them with the SHA-256 values in SKILL.md; nothing loads from the skill folder at runtime.

A pair is "<adjective>-<animal>" (16 bits: 256 x 256). A code of N pairs joins them with a single space. A code may
start with the source project's two-letter prefix and a hyphen ("ha-nifty-dolphin scary-otter"); the prefix names
where the request comes from and carries no entropy.
- make(pairs, prefix=None)              random code from `secrets`
- from_digest(hex, pairs, prefix=None)  deterministic: byte 2i picks pair i's adjective, byte 2i+1 its animal
- prefix_for(project)                   the registered prefix, or "xx" for a project not in the registry
                                        (registry: $WORD_CODES_PREFIXES, else ~/.config/word-codes/prefixes.json,
                                        else the bundled prefixes.example.json; first one that exists)
- split(text)                           (prefix or None, the word pairs)
- normalize(text)                       lowercase; spaces, underscores or hyphens between words become canonical
- valid(text, pairs=None, prefix=None)  pairs of a listed adjective then a listed animal; a prefix, when present,
                                        is two letters and (when given) the expected one
"""

from __future__ import annotations

import json
import os
import re
import secrets
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
UNKNOWN = "xx"
_PREFIX_RE = re.compile(r"[a-z]{2}")


def _find(name: str) -> Path:
    for base in (_HERE / "wordlists", _HERE):
        if (base / name).is_file():
            return base / name
    raise FileNotFoundError(f"{name} not found next to wordcode.py or in wordlists/")


def _load(name: str) -> tuple[str, ...]:
    words = tuple(w.strip() for w in _find(name).read_text(encoding="ascii").splitlines() if w.strip())
    if len(words) != 256 or len(set(words)) != 256:
        raise ValueError(f"{name}: expected 256 distinct words, found {len(words)}")
    return words


def _candidates() -> list[Path]:
    """Registry sources in lookup order: $WORD_CODES_PREFIXES, ~/.config/word-codes/prefixes.json, the example."""
    out: list[Path] = []
    env = os.environ.get("WORD_CODES_PREFIXES")
    if env:
        out.append(Path(env).expanduser())
    try:
        out.append(Path.home() / ".config" / "word-codes" / "prefixes.json")
    except (RuntimeError, OSError, KeyError):
        pass  # no home directory: skip the user config
    out.append(_HERE / "wordlists" / "prefixes.example.json")
    out.append(_HERE / "prefixes.example.json")
    return out


def _parse_prefixes(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    projects = data.get("projects", {})
    seen = {UNKNOWN}
    for project, p in projects.items():
        if not isinstance(p, str) or not _PREFIX_RE.fullmatch(p) or p in seen:
            raise ValueError(f"{project!r} has an invalid or repeated prefix {p!r}")
        seen.add(p)
    out = dict(projects)
    # aliases: other names the same project goes by (a repo folder, a field in another tool) -> its registered name
    for alias, project in data.get("aliases", {}).items():
        if project not in projects or alias in projects:
            raise ValueError(f"alias {alias!r} must name a registered project and not be one itself")
        out[alias] = projects[project]
    return out


def _load_prefixes() -> dict[str, str]:
    """Best effort: the first usable source wins; a bad one is named on stderr and skipped; none gives {}."""
    for path in _candidates():
        try:
            if not path.is_file():
                continue
            return _parse_prefixes(path)
        except (OSError, ValueError, AttributeError, TypeError) as e:  # JSONDecodeError is a ValueError
            print(f"word-codes: ignoring prefix registry {path}: {e}", file=sys.stderr)
    return {}


ADJECTIVES = _load("adjectives.txt")
ANIMALS = _load("animals.txt")
PREFIXES = _load_prefixes()
_ADJ, _ANI = set(ADJECTIVES), set(ANIMALS)
BITS_PER_PAIR = 16


def _check_pairs(pairs: int) -> None:
    if isinstance(pairs, bool) or not isinstance(pairs, int) or not 1 <= pairs <= 8:
        raise ValueError("pairs must be a whole number from 1 to 8")


def _with_prefix(code: str, prefix: str | None) -> str:
    if prefix is None:
        return code
    if not isinstance(prefix, str) or not _PREFIX_RE.fullmatch(prefix):
        raise ValueError("prefix must be two lowercase letters")
    return f"{prefix}-{code}"


def prefix_for(project: str) -> str:
    return PREFIXES.get(project, UNKNOWN)


def make(pairs: int = 1, prefix: str | None = None) -> str:
    _check_pairs(pairs)
    code = " ".join(f"{secrets.choice(ADJECTIVES)}-{secrets.choice(ANIMALS)}" for _ in range(pairs))
    return _with_prefix(code, prefix)


def from_digest(hexdigest: str, pairs: int = 2, prefix: str | None = None) -> str:
    _check_pairs(pairs)
    if not isinstance(hexdigest, str) or not re.fullmatch(r"[0-9a-fA-F]+", hexdigest) or len(hexdigest) % 2:
        raise ValueError("hexdigest must be an even-length hex string")
    data = bytes.fromhex(hexdigest)
    if len(data) < 2 * pairs:
        raise ValueError(f"{pairs} pairs need at least {2 * pairs} bytes of digest")
    code = " ".join(f"{ADJECTIVES[data[2 * i]]}-{ANIMALS[data[2 * i + 1]]}" for i in range(pairs))
    return _with_prefix(code, prefix)


def _words(text: str) -> list[str]:
    return [w for w in re.split(r"[\s_\-]+", text.strip().lower()) if w]


def split(text: str) -> tuple[str | None, str]:
    """The prefix (a leading two-letter word; every list word has 3 or more letters) and the canonical pairs."""
    words = _words(text)
    prefix = words.pop(0) if words and _PREFIX_RE.fullmatch(words[0]) else None
    if len(words) % 2:
        return prefix, " ".join(words)  # not a whole number of pairs: valid() refuses it
    return prefix, " ".join(f"{words[i]}-{words[i + 1]}" for i in range(0, len(words), 2))


def normalize(text: str) -> str:
    prefix, pairs = split(text)
    return _with_prefix(pairs, prefix) if pairs or prefix is None else prefix


def valid(text: str, pairs: int | None = None, prefix: str | None = None) -> bool:
    if not isinstance(text, str) or not text:
        return False
    head, sep, rest = text.partition("-")
    has_prefix = bool(sep) and _PREFIX_RE.fullmatch(head) is not None
    if prefix is not None and (not has_prefix or head != prefix):
        return False
    body = rest if has_prefix else text
    parts = body.split(" ")
    if pairs is not None and len(parts) != pairs:
        return False
    for part in parts:
        adj, sep, ani = part.partition("-")
        if not sep or adj not in _ADJ or ani not in _ANI:
            return False
    return True
