"""Tests for the docs-index CLI (stdlib only). Run: uv run pytest plugins/docs-index/tests -q"""
import io
import json
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN / "scripts"))
import docs_index as di  # noqa: E402


def codes(problems):
    return sorted(p.code for p in problems)


def make_tree(root: Path) -> Path:
    """An initialized project with one research note that cites one source, all consistent."""
    di.init(root)
    docs = root / "docs"
    (docs / "research" / "note.md").write_text(
        "# Note\n\nA claim ([src-a](../BIBLIOGRAPHY.md" "#src-a)).\n")
    index = (docs / "INDEX.md").read_text().replace(
        "## Research\n",
        "## Research\n- **[A note](research/note.md)** — 2026-11-20\n  What the note found.\n"
        "  Sources: [src-a](BIBLIOGRAPHY.md" "#src-a)\n")
    (docs / "INDEX.md").write_text(index)
    bib = (docs / "BIBLIOGRAPHY.md").read_text().replace(
        di.BIB_END,
        '- <a id="src-a"></a>Doe, Jan. "A Source." *Example Site*, 2026, https://example.org/a. Accessed 20 Nov. 2026.\n'
        "  *Cited by:* [note](research/note.md)\n" + di.BIB_END)
    (docs / "BIBLIOGRAPHY.md").write_text(bib)
    return docs


# ---------------------------------------------------------------- init

def test_init_creates_the_tree(tmp_path):
    done = di.init(tmp_path)
    assert done == ["docs/research/", "docs/decisions/", "docs/guides/", "docs/reference/",
                    "docs/INDEX.md", "docs/BIBLIOGRAPHY.md"]
    for folder in ("research", "decisions", "guides", "reference"):
        assert (tmp_path / "docs" / folder / ".gitkeep").is_file()
    assert di.check(tmp_path) == []


def test_init_never_overwrites(tmp_path):
    di.init(tmp_path)
    (tmp_path / "docs" / "INDEX.md").write_text("mine\n")
    assert di.init(tmp_path) == []
    assert (tmp_path / "docs" / "INDEX.md").read_text() == "mine\n"


def test_init_adds_each_block_once(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("# Project\n")
    assert di.init(tmp_path, claude_md=True, agents_md=True)[-2:] == ["CLAUDE.md", "AGENTS.md"]
    assert di.init(tmp_path, claude_md=True, agents_md=True) == []
    claude = (tmp_path / "CLAUDE.md").read_text()
    assert claude.startswith("# Project\n\n" + di.BLOCK_START) and claude.count(di.BLOCK_START) == 1
    assert (tmp_path / "AGENTS.md").read_text() == di.AGENTS_BLOCK


def test_agents_snippet_file_matches_the_cli():
    assert (PLUGIN / "AGENTS-snippet.md").read_text() == di.AGENTS_BLOCK


# ---------------------------------------------------------------- check

def test_consistent_tree_is_clean(tmp_path):
    make_tree(tmp_path)
    assert di.check(tmp_path) == []


def test_uninitialized_project(tmp_path, capsys):
    assert di.check(tmp_path) is None
    assert di.main(["check", "--root", str(tmp_path)]) == 2
    assert "docs-index init" in capsys.readouterr().out


def test_missing_markers(tmp_path):
    di.init(tmp_path)
    (tmp_path / "docs" / "INDEX.md").write_text("# Index\n")
    assert codes(di.check(tmp_path)) == ["IDX-MARKERS"]


def test_broken_link_and_unlisted_document(tmp_path):
    docs = make_tree(tmp_path)
    (docs / "research" / "note.md").rename(docs / "research" / "renamed.md")
    found = di.check(tmp_path)
    assert codes(found) == ["BIB-BACKLINK", "BIB-CITEDBY", "IDX-LINK", "IDX-UNLISTED"]
    assert [p.path for p in found if p.code == "IDX-UNLISTED"] == ["docs/research/renamed.md"]


def test_nested_documents_must_be_listed(tmp_path):
    docs = make_tree(tmp_path)
    (docs / "reference" / "datasheets").mkdir()
    (docs / "reference" / "datasheets" / "part.md").write_text("# Part\n")
    assert [(p.code, p.path) for p in di.check(tmp_path)] == [
        ("IDX-UNLISTED", "docs/reference/datasheets/part.md")]


def test_entry_without_summary(tmp_path):
    docs = make_tree(tmp_path)
    text = (docs / "INDEX.md").read_text().replace("  What the note found.\n", "")
    (docs / "INDEX.md").write_text(text)
    assert codes(di.check(tmp_path)) == ["IDX-SUMMARY"]


def test_entry_under_the_wrong_heading(tmp_path):
    docs = make_tree(tmp_path)
    text = (docs / "INDEX.md").read_text()
    entry = text[text.index("- **[A note]"):text.index("## Decisions")]
    text = text.replace(entry, "").replace("## Guides\n", "## Guides\n" + entry)
    (docs / "INDEX.md").write_text(text)
    found = di.check(tmp_path)
    assert codes(found) == ["IDX-SECTION"]
    assert "not in docs/guides/" in found[0].message


def test_duplicate_entry(tmp_path):
    docs = make_tree(tmp_path)
    entry = "- **[A note](research/note.md)** — 2026-11-20\n  Again.\n"
    text = (docs / "INDEX.md").read_text().replace("## Decisions\n", entry + "## Decisions\n")
    (docs / "INDEX.md").write_text(text)
    assert codes(di.check(tmp_path)) == ["IDX-DUP"]


def test_unknown_citation_key(tmp_path):
    docs = make_tree(tmp_path)
    (docs / "research" / "note.md").write_text("# Note\n\nSee [x](../BIBLIOGRAPHY.md" "#nope) and "
                                                "[a](../BIBLIOGRAPHY.md" "#src-a).\n")
    found = di.check(tmp_path)
    assert [(p.code, p.path) for p in found] == [("BIB-KEY", "docs/research/note.md")]
    assert "'nope'" in found[0].message


def test_citations_in_code_are_examples(tmp_path):
    docs = make_tree(tmp_path)
    (docs / "guides" / "how.md").write_text(
        "# How\n\nWrite `[k](../BIBLIOGRAPHY.md" "#inline-example)` like this:\n\n"
        "```markdown\n- [k](BIBLIOGRAPHY.md" "#fenced-example)\n```\n\n"
        "````markdown\n```\n[k](BIBLIOGRAPHY.md" "#nested-example)\n```\n````\n")
    text = (docs / "INDEX.md").read_text().replace(
        "## Guides\n", "## Guides\n- **[How](guides/how.md)** — 2026-11-20\n  How to cite.\n")
    (docs / "INDEX.md").write_text(text)
    assert di.check(tmp_path) == []


def test_missing_cited_by_line(tmp_path):
    docs = make_tree(tmp_path)
    text = (docs / "BIBLIOGRAPHY.md").read_text().replace("  *Cited by:* [note](research/note.md)\n", "")
    (docs / "BIBLIOGRAPHY.md").write_text(text)
    assert codes(di.check(tmp_path)) == ["BIB-BACKLINK", "BIB-CITEDBY"]


def test_cited_by_must_link_back_to_every_citing_document(tmp_path):
    docs = make_tree(tmp_path)
    (docs / "decisions" / "0001-x.md").write_text("# 0001\n\nPer [a](../BIBLIOGRAPHY.md" "#src-a).\n")
    text = (docs / "INDEX.md").read_text().replace(
        "## Decisions\n", "## Decisions\n- **[0001 — X](decisions/0001-x.md)** — 2026-11-20\n  Chose X.\n")
    (docs / "INDEX.md").write_text(text)
    found = di.check(tmp_path)
    assert codes(found) == ["BIB-BACKLINK"]
    assert "decisions/0001-x.md" in found[0].message


def test_duplicate_and_unanchored_bibliography_entries(tmp_path):
    docs = make_tree(tmp_path)
    text = (docs / "BIBLIOGRAPHY.md").read_text().replace(
        di.BIB_END,
        '- <a id="src-a"></a>Again.\n  *Cited by:* [note](research/note.md)\n- No anchor here.\n' + di.BIB_END)
    (docs / "BIBLIOGRAPHY.md").write_text(text)
    assert codes(di.check(tmp_path)) == ["BIB-DUP", "BIB-KEY"]


def test_check_cli_output_and_exit_codes(tmp_path, capsys):
    docs = make_tree(tmp_path)
    assert di.main(["check", "--root", str(tmp_path)]) == 0
    assert "consistent" in capsys.readouterr().out
    (docs / "guides" / "new.md").write_text("# New\n")
    assert di.main(["check", "--root", str(tmp_path), "--json"]) == 1
    assert json.loads(capsys.readouterr().out) == [
        {"code": "IDX-UNLISTED", "path": "docs/guides/new.md", "line": 1, "message": "not listed in docs/INDEX.md"}]


# ---------------------------------------------------------------- Stop hook

@pytest.fixture
def config(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    monkeypatch.setenv("DOCS_INDEX_CONFIG", str(path))
    return path


def _hook(project: Path, capsys, **extra) -> dict | None:
    payload = json.dumps({"cwd": str(project), "hook_event_name": "Stop", **extra})
    assert di.main(["check", "--hook"], stdin=io.StringIO(payload)) == 0
    out = capsys.readouterr().out.strip()
    return json.loads(out) if out else None


@pytest.mark.parametrize("text, mode", [("", "warn"), ("stop_hook: off\n", "off"), ("stop_hook: block # x\n", "block"),
                                        ("stop_hook: 'warn'\n", "warn"), ("stop_hook: loud\n", "warn")])
def test_hook_mode(config, text, mode):
    config.write_text(text)
    assert di.hook_mode() == mode


def test_hook_mode_without_a_config_file(config):
    assert di.hook_mode() == "warn"


def test_hook_is_silent_outside_an_initialized_project(tmp_path, config, capsys):
    assert _hook(tmp_path / "elsewhere", capsys) is None


def test_hook_is_silent_when_clean(tmp_path, config, capsys):
    make_tree(tmp_path / "p")
    assert _hook(tmp_path / "p" / "docs" / "research", capsys) is None


def test_hook_warns_by_default(tmp_path, config, capsys):
    docs = make_tree(tmp_path / "p")
    (docs / "guides" / "new.md").write_text("# New\n")
    out = _hook(tmp_path / "p", capsys)
    assert list(out) == ["systemMessage"] and "IDX-UNLISTED docs/guides/new.md" in out["systemMessage"]


def test_hook_blocks_once_when_configured(tmp_path, config, capsys):
    config.write_text("stop_hook: block\n")
    docs = make_tree(tmp_path / "p")
    (docs / "guides" / "new.md").write_text("# New\n")
    assert _hook(tmp_path / "p", capsys)["decision"] == "block"
    assert list(_hook(tmp_path / "p", capsys, stop_hook_active=True)) == ["systemMessage"]


def test_hook_off(tmp_path, config, capsys):
    config.write_text("stop_hook: off\n")
    docs = make_tree(tmp_path / "p")
    (docs / "guides" / "new.md").write_text("# New\n")
    assert _hook(tmp_path / "p", capsys) is None


def test_hook_survives_bad_input(tmp_path, config, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert di.main(["check", "--hook"], stdin=io.StringIO("not json")) == 0
    assert capsys.readouterr().out == ""


def test_hook_never_writes(tmp_path, config, capsys):
    docs = make_tree(tmp_path / "p")
    (docs / "guides" / "new.md").write_text("# New\n")
    before = {p: p.read_bytes() for p in (tmp_path / "p").rglob("*") if p.is_file()}
    _hook(tmp_path / "p", capsys)
    assert {p: p.read_bytes() for p in (tmp_path / "p").rglob("*") if p.is_file()} == before


# ---------------------------------------------------------------- plugin files

def test_stop_hook_runs_the_bundled_script():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text())
    [stop] = hooks["hooks"]["Stop"]
    [cmd] = stop["hooks"]
    assert cmd["type"] == "command"
    assert cmd["command"] == 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/docs_index.py" check --hook'


def test_manifests_agree():
    claude = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    codex = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text())
    assert claude["name"] == codex["name"] == "docs-index"
    assert claude["version"] == codex["version"]
    assert claude["author"] == {"name": "stegbk"}


# ---------------------------------------------------------------- hardening

def test_hook_fails_safe_on_os_error(tmp_path, config, capsys, monkeypatch):
    make_tree(tmp_path / "p")

    def boom(root):
        raise OSError("disk gone")

    monkeypatch.setattr(di, "check", boom)
    assert _hook(tmp_path / "p", capsys) is None


def test_cli_check_reports_os_error_without_traceback(tmp_path, capsys, monkeypatch):
    make_tree(tmp_path)

    def boom(root):
        raise OSError("disk gone")

    monkeypatch.setattr(di, "check", boom)
    assert di.main(["check", "--root", str(tmp_path)]) == 1
    assert capsys.readouterr().out.strip() == "error: disk gone"


def test_init_writes_utf8(tmp_path, monkeypatch):
    import locale
    monkeypatch.setattr(locale, "getpreferredencoding", lambda *a, **k: "ascii")
    di.init(tmp_path, claude_md=True, agents_md=True)
    assert "—" in (tmp_path / "AGENTS.md").read_bytes().decode("utf-8")


def test_agents_block_has_install_and_exit_code_notes():
    assert "uv tool install" in di.AGENTS_BLOCK
    assert "Exit code 2" in di.AGENTS_BLOCK and "docs-index init" in di.AGENTS_BLOCK


def test_codex_manifest_has_author_and_description():
    codex = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text())
    assert codex["author"] == {"name": "stegbk"} and codex["description"]


# ---------------------------------------------------------------- block wording (decision 0001, clean-room)

def test_block_markers_are_begin_and_end():
    assert (di.BLOCK_START, di.BLOCK_END) == ("<!-- docs-index begin -->", "<!-- docs-index end -->")
    for block in (di.CLAUDE_BLOCK, di.AGENTS_BLOCK):
        assert block.startswith(di.BLOCK_START + "\n") and block.endswith(di.BLOCK_END + "\n")
        assert ":START" not in block and ":END" not in block


def test_init_detects_a_block_already_present_with_the_new_markers(tmp_path):
    existing = "# Project\n\n<!-- docs-index begin -->\nmy own edited wording\n<!-- docs-index end -->\n"
    (tmp_path / "CLAUDE.md").write_text(existing)
    (tmp_path / "AGENTS.md").write_text(existing)
    assert "CLAUDE.md" not in di.init(tmp_path, claude_md=True, agents_md=True)
    assert (tmp_path / "CLAUDE.md").read_text() == existing
    assert (tmp_path / "AGENTS.md").read_text() == existing


def test_blocks_ask_for_citations_and_unverified_marking():
    rule = "Cite a source for every factual claim; mark anything uncited as unverified."
    skill = (PLUGIN / "skills" / "docs-index" / "SKILL.md").read_text()
    for text in (di.CLAUDE_BLOCK, di.AGENTS_BLOCK, skill):
        assert rule in text
        assert "cannot attribute" not in text and "can't attribute" not in text


def test_skill_description_wording():
    skill = (PLUGIN / "skills" / "docs-index" / "SKILL.md").read_text()
    description = skill.split("description:", 1)[1].split("\n", 1)[0].lower()
    assert "untraceable" not in description and "stale links" not in description
    assert "missing entries" not in description
