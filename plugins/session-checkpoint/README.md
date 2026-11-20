# session-checkpoint

Answers "can we restart?" honestly. Before a session is restarted, cleared or handed over, the skill proves that
everything the owner said and everything the session produced lives in files the next session reads:
1. `extract.py` digests the session transcript into owner messages, peer messages, assistant replies and a list
   of scratchpad files (it never prints message bodies);
2. the read-only `checkpoint-auditor` agent (Read, Grep and Glob only) compares the digests with the note files
   and reports what is missing, stale, contradictory or wrongly attributed;
3. the working session spot-checks the report, fixes the notes, and re-runs the extract until nothing that
   matters is left unsaved.

Installed from the store, the agent is `session-checkpoint:checkpoint-auditor`.

## Permissions
| Permission | Why |
|---|---|
| Read, Grep, Glob | read the digests and the note files |
| `Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/session-checkpoint/extract.py *)` | digest the transcript |
| Agent | dispatch the read-only auditor |
| Write, Edit | fix the note files and append to the suggestions log |
| `Bash(git add *)`, `Bash(git commit *)` | commit the fixes, only when the owner allows it |

It reads the session transcript (`$CLAUDE_CONFIG_DIR/projects/…`), which can hold content the session fetched
from the web, so the store records an injection review for each version. No network, no hooks, no MCP servers.

## Configuration
None. The suggestions log, where each run records flaws for the owner to review, lives at
`$CLAUDE_CONFIG_DIR/session-checkpoint/SUGGESTIONS.md`; the skill creates it from `templates/SUGGESTIONS.md` the
first time.

## Changes from the original
`extract.py` exits 2 with an error on stderr when the transcript file is missing or `--scratchpad` is not a
directory, instead of crashing or reporting "NOT-SAVED 0".

## Harnesses
Claude Code only (it reads Claude Code transcripts and dispatches a sub-agent).

## Tests
`uv run pytest plugins/session-checkpoint/tests -q` from the store repo runs `extract.py` on a small synthetic
transcript.
