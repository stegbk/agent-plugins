"""Run: python3 -I test_wordcode.py (stdlib only). Checks the lists' rules and the vectors in vectors.json."""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wordcode as wc  # noqa: E402


def one_apart(a: str, b: str) -> bool:
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    s, longer = (a, b) if len(a) < len(b) else (b, a)
    return any(longer[:i] + longer[i + 1:] == s for i in range(len(longer)))


def main() -> int:
    fails = []
    for name, words in (("adjectives", wc.ADJECTIVES), ("animals", wc.ANIMALS)):
        if list(words) != sorted(words):
            fails.append(f"{name}: not sorted")
        for w in words:
            if not re.fullmatch(r"[a-z]{3,7}", w):
                fails.append(f"{name}: {w!r} is not 3-7 lowercase letters")
        for i, a in enumerate(words):
            for b in words[i + 1:]:
                if a[:4] == b[:4] or b.startswith(a):
                    fails.append(f"{name}: {a} and {b} share a prefix")
                if one_apart(a, b):
                    fails.append(f"{name}: {a} and {b} are one letter apart")
    if set(wc.ADJECTIVES) & set(wc.ANIMALS):
        fails.append(f"both lists hold {sorted(set(wc.ADJECTIVES) & set(wc.ANIMALS))}")

    vectors = json.loads((HERE / "vectors.json").read_text())
    for v in vectors["from_digest"]:
        got = wc.from_digest(v["digest"], v["pairs"], v.get("prefix"))
        if got != v["code"]:
            fails.append(f"from_digest({v['digest'][:12]}…, {v['pairs']}) = {got!r}, want {v['code']!r}")
    for v in vectors["normalize"]:
        if wc.normalize(v["in"]) != v["out"]:
            fails.append(f"normalize({v['in']!r}) = {wc.normalize(v['in'])!r}, want {v['out']!r}")
    for v in vectors["valid"]:
        if wc.valid(v["code"], v.get("pairs"), v.get("prefix")) != v["valid"]:
            fails.append(f"valid({v['code']!r}, {v.get('pairs')}, {v.get('prefix')}) should be {v['valid']}")
    for v in vectors["split"]:
        if wc.split(v["in"]) != (v["prefix"], v["pairs"]):
            fails.append(f"split({v['in']!r}) = {wc.split(v['in'])!r}")
    for v in vectors["prefix_for"]:
        if wc.prefix_for(v["project"]) != v["prefix"]:
            fails.append(f"prefix_for({v['project']!r}) = {wc.prefix_for(v['project'])!r}")
    for project, p in wc.PREFIXES.items():
        if wc.prefix_for(project) != p or p == wc.UNKNOWN:
            fails.append(f"registry: {project} -> {p}")
    for _ in range(50):
        c = wc.make(2, "ha")
        if not wc.valid(c, 2, "ha") or wc.normalize(c) != c:
            fails.append(f"make(2, 'ha') gave {c!r}")
    for _ in range(200):
        for n in (1, 2):
            c = wc.make(n)
            if not wc.valid(c, n) or wc.normalize(c) != c:
                fails.append(f"make({n}) gave {c!r}")
    for bad in ("", "zz", "0", "00"):
        try:
            wc.from_digest(bad, 1)
            fails.append(f"from_digest({bad!r}) did not refuse")
        except ValueError:
            pass

    # aliases (2026-11-20): other names a project goes by resolve to the registered prefix. Checked against the
    # bundled example registry, parsed directly, so a user's own registry cannot make the self-test fail.
    example = next(p for p in (HERE / "wordlists" / "prefixes.example.json", HERE / "prefixes.example.json")
                   if p.is_file())
    bundled = wc._parse_prefixes(example)
    for name, want in (("example-app", "ea"), ("example_app", "ea"), ("example_service_api", "es"),
                       ("example-tools", "et"), ("never-registered", "xx")):
        if bundled.get(name, wc.UNKNOWN) != want:
            fails.append(f"example registry: {name!r} is {bundled.get(name, wc.UNKNOWN)!r}, want {want!r}")
    if len(set(bundled.values())) < 4:
        fails.append("expected 4 distinct prefixes in the example registry")

    print("\n".join(fails) if fails else "word-codes: all checks pass")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
