# docs-index

Keeps a project's `docs/` folder in order: research, decisions, guides and reference notes, an `INDEX.md` that
lists each document with a one-line summary, and a `BIBLIOGRAPHY.md` that records every source once in MLA format,
with a citation key and *Cited by:* links back to the documents that use it.

It has three parts:
- the **docs-index skill**, which tells the agent how to file a document, write the entries and cite sources;
- the **`docs-index` CLI** (`scripts/docs_index.py`, Python standard library only) with `init` and `check`;
- an optional **Stop hook** (Claude Code only) that runs `check` at the end of each turn.

## Use
- Claude Code: ask to save research or a decision, or run the skill. In a new project the skill runs
  `docs-index init` first.
- Codex: install the CLI once with `uv tool install <path to this plugin folder>`, run `docs-index init --agents-md`
  in the project, and Codex follows the block it adds to `AGENTS.md`. `AGENTS-snippet.md` is the same block.
- Anyone: `docs-index check` exits 0 when `docs/` is consistent, 1 with a list of problems, 2 when the project has
  no `docs/INDEX.md`. `--json` gives machine-readable output.

## Permissions
| Permission | Why |
|---|---|
| Read, Glob | read the project's `docs/` tree |
| Write, Edit | write documents, `docs/INDEX.md`, `docs/BIBLIOGRAPHY.md`, and the `CLAUDE.md`/`AGENTS.md` block |
| `Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/docs_index.py" *)` | run `init` and `check` |
| Stop hook | runs `check --hook`: reads local files under the project's `docs/` and the config file; no network, never writes |

No network access, no MCP servers, no other commands.

## Configuration
Optional. Copy `config.example.yaml` to `~/.config/docs-index/config.yaml` (or set `DOCS_INDEX_CONFIG` to another
path). The only setting is `stop_hook`: `warn` (the default, also used when there is no file), `block` or `off`.
Nothing personal is stored by the plugin; each project's documents stay in that project.

## Harnesses
- Claude Code: skill, CLI and Stop hook.
- Codex: the AGENTS.md block and the CLI; there is no Stop hook.

## Tests
`uv run pytest plugins/docs-index/tests -q` from the store repo.
