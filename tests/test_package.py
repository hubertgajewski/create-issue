from __future__ import annotations

import json
import re
import stat
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "create-issue"
FRONTMATTER = re.compile(
    r"\A---\nname: (?P<name>[a-z0-9-]+)\n"
    r"description: (?P<description>[^\n]+)\n---\n"
)
YAML_FIELD = re.compile(
    r'^  (?P<key>[a-z][a-z0-9_]*): (?P<value>"(?:[^"\\]|\\.)*")$'
)
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FENCE = re.compile(r"^ {0,3}```.*?^ {0,3}```", re.DOTALL | re.MULTILINE)
# GitHub Projects (v2) node IDs for projects, fields, and single-select fields.
PROJECT_NODE_ID = re.compile(r"\bPVT(?:F|SSF)?_[A-Za-z0-9_-]{6,}")
FORGE_PROJECT_URL = re.compile(r"https://(?:github|gitlab)\.com/[A-Za-z0-9_.-]+/")


def interface_metadata(path: Path) -> dict[str, str]:
    """Parse the JSON-quoted YAML subset used by the OpenAI metadata file."""
    relative = path.relative_to(ROOT).as_posix()
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "interface:":
        raise AssertionError(f"{relative}: expected an interface mapping")

    metadata: dict[str, str] = {}
    for line_number, line in enumerate(lines[1:], start=2):
        match = YAML_FIELD.fullmatch(line)
        if match is None:
            raise AssertionError(f"{relative}:{line_number}: malformed interface field")
        key = match.group("key")
        if key in metadata:
            raise AssertionError(f"{relative}:{line_number}: duplicate field {key}")
        value = json.loads(match.group("value"))
        if not isinstance(value, str) or not value:
            raise AssertionError(f"{relative}:{line_number}: expected a nonempty string")
        metadata[key] = value
    return metadata


def markdown_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.md")
        if ".git" not in path.relative_to(ROOT).parts
    )


def relative_links(path: Path) -> list[str]:
    """Relative link targets outside fenced code, without their fragments."""
    text = FENCE.sub("", path.read_text(encoding="utf-8"))
    targets = []
    for target in MARKDOWN_LINK.findall(text):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            continue
        targets.append(target.split("#", 1)[0])
    return targets


class PackageTests(unittest.TestCase):
    def test_required_package_files_exist(self) -> None:
        for relative in (
            "SKILL.md",
            "agents/openai.yaml",
            "references/configuration.md",
            "references/forges.md",
            "references/templates/story.md",
            "references/templates/bug.md",
            "references/templates/task.md",
            "references/templates/epic.md",
        ):
            with self.subTest(relative=relative):
                path = SKILL / relative
                try:
                    mode = path.lstat().st_mode
                except FileNotFoundError:
                    self.fail(f"{relative}: missing required package file")
                self.assertTrue(
                    stat.S_ISREG(mode),
                    f"{relative}: required package path must be a regular file",
                )

    def test_skill_has_valid_frontmatter(self) -> None:
        match = FRONTMATTER.match((SKILL / "SKILL.md").read_text(encoding="utf-8"))

        self.assertIsNotNone(match, "SKILL.md: malformed frontmatter")
        assert match is not None
        self.assertEqual(match.group("name"), "create-issue")
        description = match.group("description")
        self.assertLessEqual(len(description), 1024, "description exceeds 1024 characters")
        self.assertIn("Use when", description, "description must say when to use the skill")
        self.assertIn(
            "Do not use to fix or implement an issue",
            description,
            "description must exclude fixing issues",
        )

    def test_openai_metadata_is_valid(self) -> None:
        metadata = interface_metadata(SKILL / "agents" / "openai.yaml")

        self.assertEqual(
            set(metadata), {"display_name", "short_description", "default_prompt"}
        )
        self.assertEqual(metadata["display_name"], "Create Issue")
        self.assertIn("$create-issue", metadata["default_prompt"])

    def test_agent_instructions_live_in_agents_md_only(self) -> None:
        self.assertTrue((ROOT / "AGENTS.md").is_file(), "AGENTS.md is required")
        for name in ("CLAUDE.md", ".claude/CLAUDE.md"):
            with self.subTest(name=name):
                self.assertFalse(
                    (ROOT / name).exists(),
                    f"{name} must not exist; Claude Code reads AGENTS.md directly",
                )

    def test_relative_markdown_links_resolve(self) -> None:
        for path in markdown_files():
            for target in relative_links(path):
                if not target:
                    continue
                with self.subTest(path=path.relative_to(ROOT).as_posix(), target=target):
                    self.assertTrue(
                        (path.parent / target).exists(),
                        f"{path.relative_to(ROOT)} links to missing {target}",
                    )

    def test_package_links_stay_inside_the_package(self) -> None:
        package = SKILL.resolve()
        for path in sorted(SKILL.rglob("*.md")):
            for target in relative_links(path):
                with self.subTest(path=path.relative_to(ROOT).as_posix(), target=target):
                    resolved = (path.parent / target).resolve()
                    self.assertTrue(
                        resolved.is_relative_to(package),
                        f"{path.relative_to(ROOT)} links outside the package: {target}",
                    )

    def test_package_contains_no_project_specific_identifiers(self) -> None:
        for path in sorted(p for p in SKILL.rglob("*") if p.is_file()):
            text = path.read_text(encoding="utf-8")
            relative = path.relative_to(ROOT).as_posix()
            with self.subTest(path=relative):
                self.assertIsNone(
                    PROJECT_NODE_ID.search(text),
                    f"{relative}: contains a GitHub project node ID",
                )
                self.assertIsNone(
                    FORGE_PROJECT_URL.search(text),
                    f"{relative}: contains a URL to a specific forge project",
                )


if __name__ == "__main__":
    unittest.main()
