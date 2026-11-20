---
name: word-codes
description: Use when a project shows the owner a code to read on one screen and type or compare on another (run handles, approval match codes, pairing codes), or when vendoring, updating or checking the shared adjective-animal word lists. Covers the lists, the reference module wordcode.py (make, from_digest, normalize, valid), the rules, how many pairs to use, and how to vendor and pin a copy.
---

# Word codes

Short adjective-animal phrases the owner can read on a phone and type at a Mac: `dapper-newt`, or two pairs
`dapper-newt idle-pike`. Meant to be shared by every project that needs such codes, for example run handles or approval match codes.

## Contents
- `wordlists/adjectives.txt`, `wordlists/animals.txt`: 256 words each, sorted, one per line, ASCII.
- `wordcode.py`: the stdlib-only reference module.
  - `make(pairs=1, prefix=None)`: a random code from `secrets`.
  - `from_digest(hexdigest, pairs=2, prefix=None)`: deterministic. Byte 2i of the digest picks pair i's adjective and byte 2i+1 its
    animal, so two machines that hash the same thing show the same words.
  - `normalize(text)`: lowercase; spaces, underscores or hyphens between words become `adj-animal adj-animal`. Apply
    it to anything a person typed before comparing.
  - `valid(text, pairs=None, prefix=None)`: every pair is a listed adjective followed by a listed animal; a prefix,
    when present, is two letters (and the expected one when `prefix` is given).
  - `split(text)` gives `(prefix or None, pairs)`; `prefix_for(project)` reads the registry.
- `prefixes.example.json`: example prefix registry, the last fallback (lookup order below).
- `vectors.json`: test vectors (all-zero and all-f digests, a real SHA-256, normalize and valid cases).
- `test_wordcode.py`: checks the list rules and the vectors. Run it with
  `python3 "${CLAUDE_PLUGIN_ROOT}/skills/word-codes/test_wordcode.py"`.

## Rules the lists keep (the test enforces them)
- Words are 3 to 7 lowercase ASCII letters. There are no proper nouns or offensive words, and no word appears in
  both lists.
- No two words in a list share their first 4 letters, and no word is a prefix of another.
- No two words in a list are one letter apart (no bat/cat, no mole/vole), so one typo cannot land on another valid
  word.
- The adjective comes first, joined with a hyphen; pairs are separated by one space.
- Chosen the way military code names are (DoD NICKA; Churchill's 1943 rules): nothing gloomy, boastful, frivolous, crude or about
  bodies, and no word that reads like a verdict or an instruction on an approval screen (good, final, ready, safe,
  valid, honest, trusty and the like). Animals are real, specific animals (no dragon, no plain "fish").

## Source-project prefix
Every code starts with the two-letter prefix of the **project the request comes from**, for example
`ha-cute-narwhal` or `ha-cute-narwhal jaunty-pig`. Consumers that show codes are not the source apps; the prefix
names the application that asked.
- **The registry is a JSON file of the user's own projects.** `prefix_for(project)` uses the first of these that
  exists:
  1. the file named by the `WORD_CODES_PREFIXES` environment variable;
  2. `~/.config/word-codes/prefixes.json`;
  3. the bundled `prefixes.example.json` (made-up example projects; copy it to the path in 2 and edit it).
  Look a prefix up by project name and use `xx` when it is not listed.
- The file's shape: `projects` maps a project name to two lowercase letters, `xx` is reserved for an unknown
  project, and `aliases` maps other names a project goes by (its repo folder, a `project` field in another tool) to its
  registered name, so `prefix_for("example_app")` and `prefix_for("example-app")` both give `ea`. An alias must name
  a registered project and must not be one itself.
- The prefix carries no entropy and never counts toward the bits below. Every list word has 3 or more letters, so a
  leading two-letter word is always the prefix (`split`, `normalize` and `valid` rely on this).
- Prefixes are assigned explicitly, unique and never reissued. The word lists and the module stay shared: changes
  to them are agreed between the projects that use them.

## How many pairs
- One pair has 16 bits (65,536 codes). It is a **handle**: a way to find something, never a secret and never the
  security binding. Check it is unique among the live items it names, and accept the long id as well.
- Two pairs have 32 bits. Use them where a person **compares** two screens (a match code). The signature over the
  action is still the binding; the words only help the person see that the two screens agree.
- Never use a word code as a password, a token or the only check on an action.

## Vendoring
Copy `wordcode.py`, `prefixes.example.json` and the two lists into your project. Lists may sit next to the module or in `wordlists/`. Pin them
with these SHA-256 values in a test, so a changed copy fails loudly. Nothing may load from this folder at runtime.

| File | SHA-256 |
|---|---|
| `wordcode.py` | `28ff4aee0ab3970de756e1df9ad2f78ac77ba2d31d0b774a3c3ac4b37dbda248` |
| `prefixes.example.json` | `a6ef2cd87e807785a280b59e126b3edf3026647d01d547837b7b3e5210c91585` |
| `wordlists/adjectives.txt` | `e85fa386e28881eb1480600dbd7d5d5c0a2b806770266daded889f4ef9a3b4fe` |
| `wordlists/animals.txt` | `cbcf01f1d24c2fa6eec9f846ffd73f009d23b34318d9a4fc3df855ff8884c8c9` |
| `vectors.json` | `2e89770c5e265ca4031639686f87416d2da77f2d2febcee6ba1c85d38a5af5f8` |

Projects that vendor a pinned copy keep their old pin until they choose to update.

## Changing the lists
A change breaks every code derived with `from_digest` and every stored handle. Agree it with every project that vendors a copy,
rerun `test_wordcode.py`, regenerate `vectors.json`, update the SHA-256 table, and tell each project to
re-vendor.
