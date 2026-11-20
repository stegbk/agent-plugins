---
name: docs-index
description: Use when a project should keep research, a decision, a how-to guide or reference notes in its docs/ folder; when a document under docs/ is added, renamed or moved; when a source needs to be cited; when docs/ is being set up in a project; or when the docs-index check or its Stop hook reports a problem with docs/INDEX.md or docs/BIBLIOGRAPHY.md.
---

# docs-index

Each project keeps its written knowledge in four folders under `docs/`, plus two files that hold them together.

- `docs/research/`: what was found out, compared, measured or tested.
- `docs/decisions/`: one numbered file per decision (`NNNN-short-title.md`), with its context and consequences.
- `docs/guides/`: step-by-step instructions, setups, procedures and plans.
- `docs/reference/`: facts that change rarely, such as designs, specs and datasheet notes.
- `docs/INDEX.md`: the table of contents, one entry per document with a one-line summary.
- `docs/BIBLIOGRAPHY.md`: every source, listed once.

Cite a source for every factual claim; mark anything uncited as unverified.

## First use in a project
When there is no `docs/INDEX.md` yet, set the project up:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/docs_index.py" init --claude-md
```
This makes the four folders and the two files, and appends a short note about them to `CLAUDE.md`. Files that
already exist are left alone. If the project is also worked on with Codex, add `--agents-md` to put the same note
in `AGENTS.md`.

## Saving a document
1. Choose the folder from the list above. File names are lowercase words joined by hyphens; a new decision takes
   the next free number.
2. Write it. Where a statement rests on a source, link the source's key from the text:
   `[key](../BIBLIOGRAPHY.md#<key>)`.
3. List it in `docs/INDEX.md`. Entries go inside the `<!-- INDEX:START -->` / `<!-- INDEX:END -->` comments,
   under the heading that matches the folder, with the newest at the top:
   ```markdown
   - **[Title](research/file-name.md)** — 2026-11-20
     One line on what the document concludes or records, not only what it is about.
     Sources: [key-one](BIBLIOGRAPHY.md#<key-one>), [key-two](BIBLIOGRAPHY.md#<key-two>)
   ```
   A document with no sources has no `Sources:` line.
4. Record new sources in `docs/BIBLIOGRAPHY.md`, inside its marker comments, in key order and MLA style:
   ```markdown
   - <a id="key-one"></a>Author. "Title." *Site*, Publisher, date, URL. Accessed 20 Nov. 2026.
     *Cited by:* [file-name](research/file-name.md)
   ```
   A key is lowercase words joined by hyphens, for example `anthropic-cc-hooks`. When the source is already
   there, add the new document to its `*Cited by:*` line; never give a source a second entry.
5. Run the check, fix what it lists, and run it again until it is clean:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/docs_index.py" check
   ```

## Renaming or moving a document
After moving the file, point everything at the new path: its INDEX entry, each `*Cited by:*` line that names
it, and any links from other documents. Then run the check.

## Check codes
| Code | What it found |
|---|---|
| IDX-MARKERS, BIB-MARKERS, BIB-MISSING | `BIBLIOGRAPHY.md` or one of the marker pairs is absent |
| IDX-LINK | an INDEX entry points at a file that is not there |
| IDX-UNLISTED | a document in one of the four folders has no INDEX entry |
| IDX-SUMMARY | an INDEX entry lacks its one-line summary |
| IDX-SECTION | an INDEX entry is under a heading that does not match its folder |
| IDX-DUP, BIB-DUP | a document or a key is listed twice |
| BIB-KEY | a citation uses a key the bibliography does not have, or a bibliography entry has no anchor |
| BIB-CITEDBY | a bibliography entry has no `*Cited by:*` line, or that line points at a missing file |
| BIB-BACKLINK | a document cites a key whose `*Cited by:*` line does not point back to it |

## The Stop hook
In any project with a `docs/INDEX.md`, the plugin's Stop hook runs this check when a turn ends. It only reads
local files and never changes any. Out of the box it prints a warning. In `~/.config/docs-index/config.yaml`,
`stop_hook: block` has Claude fix the problems before it stops, and `stop_hook: off` disables the hook.
