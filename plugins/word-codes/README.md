# word-codes

Short adjective-animal codes that a person reads on one screen and types or compares on another: `dapper-newt`,
or two pairs `dapper-newt idle-pike`, optionally after a two-letter source-project prefix (`ea-dapper-newt`).

The skill holds the shared word lists (256 adjectives, 256 animals), the reference module `wordcode.py`
(`make`, `from_digest`, `normalize`, `valid`, `split`, `prefix_for`; standard library only), test vectors, an
example prefix registry and the rules for vendoring a pinned copy into a project. See
`skills/word-codes/SKILL.md`. Licensed MIT.

## Install
Install the plugin from the store as usual. The word lists and module work with no setup. To use your own
project prefixes, copy `skills/word-codes/prefixes.example.json` to `~/.config/word-codes/prefixes.json` and edit it.

## Permissions
| Permission | Why |
|---|---|
| Read | read the lists, the module and the rules |
| `Bash(python3 "${CLAUDE_PLUGIN_ROOT}/skills/word-codes/test_wordcode.py")` | run the reference checks |
| `Bash(cp ${CLAUDE_PLUGIN_ROOT}/skills/word-codes/* *)` | copy the module and lists out of the plugin into a project when vendoring |

No network, no hooks, no MCP servers.

## Configuration
The prefix registry (project name to two-letter prefix) is optional. `prefix_for` uses the first of these that
exists:
1. the file named by the `WORD_CODES_PREFIXES` environment variable;
2. `~/.config/word-codes/prefixes.json`;
3. the bundled `skills/word-codes/prefixes.example.json` (made-up example projects).

Loading is best effort: an unreadable or invalid registry is named on stderr and skipped, the next source is
used, and with none usable every project maps to `xx`. The codes themselves never depend on the registry.

Keep your own project names in the config file, never in the plugin. Projects vendor their own copy of the module
and lists and pin it with the SHA-256 values in the skill.

## Changes from the original
- The original shipped a `prefixes.json` listing the owner's own projects. That file is not part of the plugin; it
  is replaced by `prefixes.example.json` and the lookup order above.
- `wordcode.py` therefore changed (registry lookup), as did `test_wordcode.py` (example project names) and the
  SHA-256 table in `SKILL.md`: `wordcode.py` has a new pin and `prefixes.json` is replaced by `prefixes.example.json`. Projects that vendor a pinned copy keep their old pin until they choose to
  update; the word lists and `vectors.json` are byte-for-byte unchanged.

## Harnesses
Claude Code and Codex (the skill and the module only need Python 3.10 or later).

## Tests
`uv run pytest plugins/word-codes/tests -q` from the store repo runs the reference checks, the registry lookup
order and verifies the pinned SHA-256 table.
