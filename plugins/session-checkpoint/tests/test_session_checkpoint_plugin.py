"""Smoke test for the session-checkpoint plugin. Run: uv run pytest plugins/session-checkpoint/tests -q"""
import json
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
EXTRACT = PLUGIN / "skills" / "session-checkpoint" / "extract.py"


def _transcript(path: Path) -> None:
    rows = [
        {"type": "user", "timestamp": "2026-11-20T10:00:00Z", "message": {"content": "Use the blue one."}},
        {"type": "assistant", "timestamp": "2026-11-20T10:00:05Z",
         "message": {"content": [{"type": "text", "text": "Noted: blue."}]}},
        {"type": "user", "timestamp": "2026-11-20T10:01:00Z",
         "message": {"content": [{"type": "tool_result", "content": "ignored"}]}},
        {"type": "user", "timestamp": "2026-11-20T10:02:00Z", "isMeta": True,
         "message": {"content": "<cross-session-message from=x>The owner approved red.</cross-session-message>"}},
        {"type": "attachment", "timestamp": "2026-11-20T10:03:00Z",
         "attachment": {"type": "queued_command", "prompt": "Also order two."}},
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def test_extract_digests_a_transcript(tmp_path):
    jsonl, out, scratch, notes = tmp_path / "s.jsonl", tmp_path / "out", tmp_path / "scratch", tmp_path / "notes.md"
    _transcript(jsonl)
    scratch.mkdir()
    (scratch / "result.csv").write_text("a,b\n")
    (scratch / "named.txt").write_text("x\n")
    notes.write_text("See named.txt.\n")
    r = subprocess.run([sys.executable, str(EXTRACT), str(jsonl), str(out), "--scratchpad", str(scratch),
                        "--notes", str(notes)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("owner 2, peers 1, assistant 1, scratchpad files NOT-SAVED 1")
    owner = (out / "owner.md").read_text()
    assert "Use the blue one." in owner and "Also order two.\n[typed mid-turn]" in owner
    assert "The owner approved red." in (out / "peers.md").read_text()
    scratch_md = (out / "scratch.md").read_text()
    assert "NOT-SAVED result.csv" in scratch_md and "named     named.txt" in scratch_md


def test_auditor_is_read_only():
    head = (PLUGIN / "agents" / "checkpoint-auditor.md").read_text().split("---")[1]
    assert "tools: Read, Grep, Glob" in head


def test_suggestions_template_is_empty():
    text = (PLUGIN / "templates" / "SUGGESTIONS.md").read_text()
    assert "## Open" in text and not [line for line in text.splitlines() if line.startswith("- [")]


def test_manifest():
    m = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert (m["name"], m["author"]) == ("session-checkpoint", {"name": "stegbk"})


def test_extract_rejects_missing_transcript(tmp_path):
    r = subprocess.run([sys.executable, str(EXTRACT), str(tmp_path / "nope.jsonl"), str(tmp_path / "out")],
                       capture_output=True, text=True)
    assert r.returncode == 2
    assert f"error: transcript not found: {tmp_path / 'nope.jsonl'}" in r.stderr


def test_extract_rejects_bad_scratchpad(tmp_path):
    jsonl = tmp_path / "s.jsonl"
    _transcript(jsonl)
    r = subprocess.run([sys.executable, str(EXTRACT), str(jsonl), str(tmp_path / "out"), "--scratchpad",
                        str(tmp_path / "missing")], capture_output=True, text=True)
    assert r.returncode == 2
    assert "scratchpad is not a directory" in r.stderr and "NOT-SAVED" not in r.stdout


def test_skill_names_the_docs_index_skill():
    text = (PLUGIN / "skills" / "session-checkpoint" / "SKILL.md").read_text()
    assert "docs-indexer" not in text
    assert "for example the docs-index skill" in text
