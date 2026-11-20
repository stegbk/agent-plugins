"""Smoke test for the ui-design-process plugin. Run: uv run pytest plugins/ui-design-process/tests -q"""
import json
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SKILL = PLUGIN / "skills" / "ui-design-process"


def test_every_workflow_arg_is_documented():
    used = set(re.findall(r"\bA\.([a-zA-Z]+)", (SKILL / "workflow-template.js").read_text()))
    table = (SKILL / "SKILL.md").read_text()
    documented = set(re.findall(r"`([a-zA-Z]+)`", "".join(l for l in table.splitlines(True) if l.startswith("   | `"))))
    assert used == {"artDomain", "base", "decisions", "judges", "platform", "product", "readers", "rounds", "rules",
                    "scope", "scr", "title", "top"}
    assert used <= documented


def test_workflow_declares_its_phases():
    js = (SKILL / "workflow-template.js").read_text()
    assert js.startswith("export const meta = {")
    phases = re.findall(r"\{ title: '([A-Za-z]+)'", js)
    assert phases == ["Inventory", "Journeys", "Propose", "Feedback", "Reachability", "Rank", "Fusion", "Judge",
                      "Studio"]


def test_skill_points_at_the_bundled_template():
    assert "${CLAUDE_PLUGIN_ROOT}/skills/ui-design-process/workflow-template.js" in (SKILL / "SKILL.md").read_text()


def test_manifest():
    m = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    assert (m["name"], m["author"]) == ("ui-design-process", {"name": "stegbk"})


def test_skill_treats_untrusted_content_as_data():
    text = (SKILL / "SKILL.md").read_text()
    assert "Untrusted content." in text and "never instructions" in text


def _agent_prompts(js: str) -> list[str]:
    """The text of each agent( call up to its options object ({ label: ... }): the prompt template."""
    out = []
    for m in re.finditer(r"\bagent\(", js):
        end = js.index("{ label:", m.end())
        out.append(js[m.end():end])
    return out


def test_every_agent_prompt_carries_the_rules():
    js = (SKILL / "workflow-template.js").read_text()
    prompts = _agent_prompts(js)
    assert len(prompts) == js.count("{ label:") >= 12
    missing = [p.strip()[:80] for p in prompts if "${RULES}" not in p]
    assert missing == []


def test_studio_page_loads_nothing_from_third_parties():
    js = (SKILL / "workflow-template.js").read_text()
    assert "Google Fonts" not in js and "googleapis" not in js and "gstatic" not in js
    assert "system font stack" in js


def test_readme_declares_web_references():
    readme = (PLUGIN / "README.md").read_text()
    assert "| WebFetch, WebSearch |" in readme
    assert "web references chosen by the agents" in readme
