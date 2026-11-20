<!-- docs-index begin -->
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
<!-- docs-index end -->
