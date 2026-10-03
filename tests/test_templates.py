"""Each built-in template states its structure twice: a `## Sections` table an agent reads
for guidance and a `## Body` skeleton it copies. These tests pin both to the agreed issue
structure so the two cannot drift apart, or away from it, unnoticed."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "create-issue"
TEMPLATES = SKILL / "references" / "templates"

# (section, required) in body order.
EXPECTED = {
    "story": [
        ("Summary", True),
        ("User Story", True),
        ("Context", True),
        ("Scope", True),
        ("Acceptance Criteria", True),
        ("Technical Notes", False),
        ("Dependencies", False),
        ("Definition of Done", True),
    ],
    "bug": [
        ("Summary", True),
        ("Environment", True),
        ("Steps to Reproduce", True),
        ("Expected Result", True),
        ("Actual Result", True),
        ("Frequency", True),
        ("Impact", True),
        ("Detection", True),
        ("Suspected Cause", False),
        ("Acceptance Criteria", True),
        ("Definition of Done", True),
    ],
    "task": [
        ("Summary", True),
        ("Motivation", True),
        ("Scope", True),
        ("Acceptance Criteria", True),
        ("Definition of Done", True),
    ],
    "epic": [
        ("Outcome", True),
        ("Success Criteria", True),
        ("Scope", True),
        ("Child Issues", True),
        ("Risks and Dependencies", True),
    ],
}
GIVEN_WHEN_THEN = {"story", "bug"}

HEADING = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)
TABLE_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*(yes|no)\s*\|", re.MULTILINE)
MARKDOWN_BLOCK = re.compile(r"^```markdown\n(.*?)^```\s*$", re.DOTALL | re.MULTILINE)
AC_HEADING = re.compile(r"^### AC(\d+): \S", re.MULTILINE)


FENCE = re.compile(r"^```.*?^```\s*$", re.DOTALL | re.MULTILINE)


def section_of(path: Path, heading: str) -> str:
    """Text under a document `## <heading>`, ignoring headings inside fenced code.

    The skeleton block is itself made of `##` headings, so fences are blanked to equal-length
    filler before searching and the section is then sliced from the original text.
    """
    text = path.read_text(encoding="utf-8")
    masked = FENCE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
    matches = [m for m in HEADING.finditer(masked) if m.group(1) == heading]
    if not matches:
        raise AssertionError(f"{path.name} has no '## {heading}' section")
    start = matches[0].end()
    following = HEADING.search(masked, start)
    return text[start:following.start() if following else len(text)]


def table_sections(path: Path) -> list[tuple[str, bool]]:
    return [
        (name, flag == "yes")
        for name, flag in TABLE_ROW.findall(section_of(path, "Sections"))
    ]


def skeleton(path: Path) -> str:
    blocks = MARKDOWN_BLOCK.findall(section_of(path, "Body"))
    if len(blocks) != 1:
        raise AssertionError(f"{path.name}: expected one markdown block under '## Body'")
    return blocks[0]


def skeleton_section(body: str, heading: str) -> str:
    matches = [m for m in HEADING.finditer(body) if m.group(1) == heading]
    if not matches:
        raise AssertionError(f"skeleton has no '## {heading}'")
    start = matches[0].end()
    following = HEADING.search(body, start)
    return body[start:following.start() if following else len(body)]


class TemplateTests(unittest.TestCase):
    def test_exactly_the_expected_templates_exist(self) -> None:
        self.assertEqual({p.stem for p in TEMPLATES.glob("*.md")}, set(EXPECTED))

    def test_skill_links_every_template(self) -> None:
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        for name in EXPECTED:
            with self.subTest(template=name):
                self.assertIn(f"(references/templates/{name}.md)", text)

    def test_every_template_states_a_title_rule(self) -> None:
        for name in EXPECTED:
            with self.subTest(template=name):
                self.assertTrue(section_of(TEMPLATES / f"{name}.md", "Title").strip())

    def test_section_table_matches_the_agreed_structure(self) -> None:
        for name, expected in EXPECTED.items():
            with self.subTest(template=name):
                self.assertEqual(table_sections(TEMPLATES / f"{name}.md"), expected)

    def test_skeleton_headings_match_the_section_table(self) -> None:
        for name, expected in EXPECTED.items():
            with self.subTest(template=name):
                headings = HEADING.findall(skeleton(TEMPLATES / f"{name}.md"))
                self.assertEqual(headings, [section for section, _ in expected])

    def test_acceptance_criteria_are_numbered_from_one(self) -> None:
        for name, expected in EXPECTED.items():
            if "Acceptance Criteria" not in dict(expected):
                continue
            with self.subTest(template=name):
                criteria = skeleton_section(
                    skeleton(TEMPLATES / f"{name}.md"), "Acceptance Criteria"
                )
                numbers = [int(n) for n in AC_HEADING.findall(criteria)]
                self.assertTrue(numbers, "no AC headings")
                self.assertEqual(numbers, list(range(1, len(numbers) + 1)))

    def test_stories_and_bugs_use_given_when_then_with_two_scenarios(self) -> None:
        for name in GIVEN_WHEN_THEN:
            with self.subTest(template=name):
                criteria = skeleton_section(
                    skeleton(TEMPLATES / f"{name}.md"), "Acceptance Criteria"
                )
                scenarios = AC_HEADING.split(criteria)[2::2]
                self.assertGreaterEqual(len(scenarios), 2, "need a failure or edge case")
                for scenario in scenarios:
                    for keyword in ("Given", "When", "Then"):
                        self.assertIn(f"- **{keyword}**", scenario)

    def test_definition_of_done_is_a_task_list(self) -> None:
        for name, expected in EXPECTED.items():
            if "Definition of Done" not in dict(expected):
                continue
            with self.subTest(template=name):
                done = skeleton_section(
                    skeleton(TEMPLATES / f"{name}.md"), "Definition of Done"
                )
                self.assertRegex(done, r"(?m)^- \[ \] \S")

    def test_epic_lists_at_least_two_children(self) -> None:
        children = skeleton_section(skeleton(TEMPLATES / "epic.md"), "Child Issues")
        self.assertGreaterEqual(len(re.findall(r"(?m)^- \[ \] \S", children)), 2)

    def test_no_skeleton_line_could_trigger_a_gitlab_quick_action(self) -> None:
        for name in EXPECTED:
            with self.subTest(template=name):
                for line in skeleton(TEMPLATES / f"{name}.md").splitlines():
                    self.assertFalse(line.startswith("/"), line)


if __name__ == "__main__":
    unittest.main()
