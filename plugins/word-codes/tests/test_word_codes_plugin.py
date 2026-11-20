"""Tests for the word-codes plugin. Run: uv run pytest plugins/word-codes/tests -q"""
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILL = PLUGIN / "skills" / "word-codes"


def test_reference_checks_pass():
    r = subprocess.run([sys.executable, "-I", str(SKILL / "test_wordcode.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "word-codes: all checks pass" in r.stdout


def test_reference_checks_pass_with_a_user_registry(tmp_path):
    """The self-test must not depend on the live registry: a user's own prefixes.json leaves it green."""
    d = tmp_path / ".config" / "word-codes"
    d.mkdir(parents=True)
    (d / "prefixes.json").write_text(json.dumps({"projects": {"my-app": "ma"}, "aliases": {"my_app": "my-app"}}))
    env = {k: v for k, v in os.environ.items() if k != "WORD_CODES_PREFIXES"}
    env["HOME"] = str(tmp_path)
    r = subprocess.run([sys.executable, "-I", str(SKILL / "test_wordcode.py")], capture_output=True, text=True,
                       env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "word-codes: all checks pass" in r.stdout


def test_pinned_hashes_match_the_files():
    table = dict(re.findall(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|$", (SKILL / "SKILL.md").read_text(), re.M))
    assert set(table) == {"wordcode.py", "prefixes.example.json", "wordlists/adjectives.txt",
                          "wordlists/animals.txt", "vectors.json"}
    for rel, digest in table.items():
        assert hashlib.sha256((SKILL / rel).read_bytes()).hexdigest() == digest, rel


def test_manifest():
    m = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert (m["name"], m["author"]) == ("word-codes", {"name": "stegbk"})


def test_owner_registry_is_not_shipped():
    assert not (SKILL / "prefixes.json").exists()
    assert (SKILL / "prefixes.example.json").is_file()


def _load(monkeypatch, tmp_path, env=None, config=None):
    """Import a fresh wordcode with HOME in tmp_path; never touches the real ~/.config."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("WORD_CODES_PREFIXES", raising=False)
    if env is not None:
        monkeypatch.setenv("WORD_CODES_PREFIXES", str(env))
    if config is not None:
        d = tmp_path / ".config" / "word-codes"
        d.mkdir(parents=True)
        (d / "prefixes.json").write_text(json.dumps(config))
    spec = importlib.util.spec_from_file_location("wordcode_under_test", SKILL / "wordcode.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _reg(name, prefix):
    return {"projects": {name: prefix}}


def test_falls_back_to_the_bundled_example(monkeypatch, tmp_path):
    wc = _load(monkeypatch, tmp_path)
    assert wc.prefix_for("example-app") == "ea"
    assert wc.prefix_for("nothing-registered") == "xx"


def test_config_file_beats_the_example(monkeypatch, tmp_path):
    wc = _load(monkeypatch, tmp_path, config=_reg("my-app", "ma"))
    assert wc.prefix_for("my-app") == "ma"
    assert wc.prefix_for("example-app") == "xx"


def test_env_override_beats_the_config_file(monkeypatch, tmp_path):
    override = tmp_path / "other.json"
    override.write_text(json.dumps(_reg("env-app", "ev")))
    wc = _load(monkeypatch, tmp_path, env=override, config=_reg("my-app", "ma"))
    assert wc.prefix_for("env-app") == "ev"
    assert wc.prefix_for("my-app") == "xx"


def test_missing_env_file_falls_through(monkeypatch, tmp_path):
    wc = _load(monkeypatch, tmp_path, env=tmp_path / "absent.json", config=_reg("my-app", "ma"))
    assert wc.prefix_for("my-app") == "ma"


def _vectors_still_pass(wc):
    v = json.loads((SKILL / "vectors.json").read_text())
    for c in v["from_digest"]:
        assert wc.from_digest(c["digest"], c["pairs"], c.get("prefix")) == c["code"]
    for c in v["normalize"]:
        assert wc.normalize(c["in"]) == c["out"]
    for c in v["valid"]:
        assert wc.valid(c["code"], c.get("pairs"), c.get("prefix")) == c["valid"]
    for c in v["split"]:
        assert wc.split(c["in"]) == (c["prefix"], c["pairs"])
    assert wc.make(1) and wc.valid(wc.make(2), 2)


def test_malformed_json_falls_back(monkeypatch, tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    wc = _load(monkeypatch, tmp_path, env=bad)
    assert wc.prefix_for("example-app") == "ea"
    assert "bad.json" in capsys.readouterr().err
    _vectors_still_pass(wc)


def test_malformed_env_falls_to_config_file(monkeypatch, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("[")
    wc = _load(monkeypatch, tmp_path, env=bad, config=_reg("my-app", "ma"))
    assert wc.prefix_for("my-app") == "ma"


def test_unreadable_file_falls_back(monkeypatch, tmp_path, capsys):
    f = tmp_path / "locked.json"
    f.write_text(json.dumps(_reg("env-app", "ev")))
    f.chmod(0)
    try:
        wc = _load(monkeypatch, tmp_path, env=f)
        assert wc.prefix_for("example-app") == "ea"
        assert "locked.json" in capsys.readouterr().err
        _vectors_still_pass(wc)
    finally:
        f.chmod(0o600)


def test_invalid_prefixes_fall_back(monkeypatch, tmp_path, capsys):
    bad = tmp_path / "dup.json"
    bad.write_text(json.dumps({"projects": {"a": "aa", "b": "aa"}}))
    wc = _load(monkeypatch, tmp_path, env=bad)
    assert wc.prefix_for("example-app") == "ea"
    assert "dup.json" in capsys.readouterr().err
    _vectors_still_pass(wc)


def test_missing_home_falls_back(monkeypatch, tmp_path):
    def boom(cls=None):
        raise RuntimeError("no home")
    monkeypatch.setattr(Path, "home", classmethod(boom))
    monkeypatch.delenv("WORD_CODES_PREFIXES", raising=False)
    spec = importlib.util.spec_from_file_location("wordcode_nohome", SKILL / "wordcode.py")
    wc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wc)
    assert wc.prefix_for("example-app") == "ea"
    _vectors_still_pass(wc)


def test_unusable_example_gives_an_empty_registry(monkeypatch, tmp_path):
    root = tmp_path / "copy"
    shutil.copytree(SKILL, root)
    (root / "prefixes.example.json").write_text("nope")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("WORD_CODES_PREFIXES", raising=False)
    spec = importlib.util.spec_from_file_location("wordcode_empty", root / "wordcode.py")
    wc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wc)
    assert wc.prefix_for("example-app") == "xx"
    assert wc.PREFIXES == {}
    assert wc.make(1, "ab").startswith("ab-")
