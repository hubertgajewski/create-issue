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
# The package's own project. Only package metadata may name it, and it is the only absolute
# link target the package's Markdown may use.
PROJECT_URL = re.compile(
    r"https://gitlab\.com/hubertgajewski-ai/create-issue(?![A-Za-z0-9_.-])"
)
PROJECT_URL_FILES = {"README.md", "CHANGELOG.md", ".claude-plugin/plugin.json"}
AUTOLINK = re.compile(r"<([a-z][a-z0-9+.-]*:[^>\s]*)>")
SEMVER = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
CHANGELOG_HEADING = re.compile(
    rf"^## (?P<version>{SEMVER}) - (?:[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}|Unreleased)$"
)
MANIFEST_KEYS = {
    "name",
    "displayName",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
}
TABLE_ROW = re.compile(r"^\| (?P<cells>.*) \|$")


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


def claude_manifest(path: Path) -> dict[str, object]:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        keys = [key for key, _ in pairs]
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        if duplicates:
            raise AssertionError(f"plugin.json: duplicate keys {duplicates}")
        return dict(pairs)

    manifest = json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates
    )
    if not isinstance(manifest, dict):
        raise AssertionError("plugin.json: expected a JSON object")
    return manifest


def changelog_latest_version(text: str) -> str:
    """The version of the first section; every level-2 heading must be a version."""
    versions = []
    for line in text.splitlines():
        if line.startswith("## "):
            match = CHANGELOG_HEADING.fullmatch(line)
            if match is None:
                raise AssertionError(f"CHANGELOG.md: malformed version heading {line!r}")
            versions.append(match.group("version"))
    if not versions:
        raise AssertionError("CHANGELOG.md: no version heading")
    return versions[0]


def check_versions_match(changelog: str, manifest_version: object) -> None:
    latest = changelog_latest_version(changelog)
    if latest != manifest_version:
        raise AssertionError(
            f"CHANGELOG.md latest version {latest} differs from "
            f".claude-plugin/plugin.json version {manifest_version}"
        )


def check_license_matches(root: bytes, packaged: bytes) -> None:
    if packaged != root:
        raise AssertionError("skills/create-issue/LICENSE differs from the root LICENSE")


def invocation_table(path: Path, heading: str) -> dict[str, str]:
    """Map each client in the table under a level-2 heading to its invocation cell."""
    text = path.read_text(encoding="utf-8")
    match = re.search(
        rf"^## {re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)",
        text,
        re.DOTALL | re.MULTILINE,
    )
    if match is None:
        raise AssertionError(f"{path.relative_to(ROOT)}: missing section ## {heading}")
    rows = [
        row.group("cells").split(" | ")
        for row in map(TABLE_ROW.fullmatch, match.group("body").splitlines())
        if row is not None
    ]
    if len(rows) < 3 or rows[0][0] != "Client" or rows[0][-1] != "Invocation":
        raise AssertionError(f"{path.relative_to(ROOT)}: missing client invocation table")
    return {cells[0]: cells[-1] for cells in rows[2:]}


def markdown_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.md")
        if ".git" not in path.relative_to(ROOT).parts
    )


def absolute_links(path: Path) -> list[str]:
    """Absolute link and autolink targets outside fenced code."""
    text = FENCE.sub("", path.read_text(encoding="utf-8"))
    targets = MARKDOWN_LINK.findall(text) + AUTOLINK.findall(text)
    return [target for target in targets if re.match(r"^[a-z][a-z0-9+.-]*:", target)]


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
            "references/reference-grammar.md",
            "references/templates/story.md",
            "references/templates/bug.md",
            "references/templates/task.md",
            "references/templates/epic.md",
            "scripts/normalize_reference.py",
            "README.md",
            "CHANGELOG.md",
            "LICENSE",
            ".claude-plugin/plugin.json",
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

    def test_claude_manifest_is_valid(self) -> None:
        manifest = claude_manifest(SKILL / ".claude-plugin" / "plugin.json")
        frontmatter = FRONTMATTER.match((SKILL / "SKILL.md").read_text(encoding="utf-8"))
        assert frontmatter is not None
        openai = interface_metadata(SKILL / "agents" / "openai.yaml")

        self.assertEqual(set(manifest), MANIFEST_KEYS)
        self.assertEqual(manifest["name"], frontmatter.group("name"))
        self.assertEqual(manifest["displayName"], openai["display_name"])
        self.assertIsInstance(manifest["version"], str)
        self.assertRegex(manifest["version"], rf"\A{SEMVER}\Z")
        self.assertIsInstance(manifest["description"], str)
        self.assertTrue(manifest["description"])
        self.assertIsInstance(manifest["author"], dict)
        self.assertEqual(set(manifest["author"]), {"name"})
        self.assertIsInstance(manifest["author"]["name"], str)
        self.assertTrue(manifest["author"]["name"])
        for key in ("homepage", "repository"):
            with self.subTest(key=key):
                self.assertIsInstance(manifest[key], str)
                self.assertIsNotNone(PROJECT_URL.fullmatch(manifest[key]))
        self.assertEqual(manifest["license"], "MIT")
        self.assertTrue(
            (SKILL / "LICENSE").read_text(encoding="utf-8").startswith("MIT License\n"),
            "manifest license must name the packaged LICENSE",
        )

    def test_changelog_latest_version_matches_manifest(self) -> None:
        manifest = claude_manifest(SKILL / ".claude-plugin" / "plugin.json")
        check_versions_match(
            (SKILL / "CHANGELOG.md").read_text(encoding="utf-8"), manifest["version"]
        )

    def test_version_mismatch_names_both_versions(self) -> None:
        changelog = "# Changelog\n\n## 1.1.0 - Unreleased\n\n## 1.0.0 - 2026-01-02\n"

        with self.assertRaisesRegex(AssertionError, r"1\.1\.0 .* 1\.0\.0"):
            check_versions_match(changelog, "1.0.0")
        check_versions_match(changelog, "1.1.0")
        with self.assertRaisesRegex(AssertionError, "malformed version heading"):
            changelog_latest_version("## 1.1.0\n\n## 1.0.0 - 2026-01-02\n")

    def test_packaged_license_matches_root(self) -> None:
        check_license_matches(
            (ROOT / "LICENSE").read_bytes(), (SKILL / "LICENSE").read_bytes()
        )

    def test_license_divergence_fails(self) -> None:
        root = (ROOT / "LICENSE").read_bytes()
        for index in (0, len(root) // 2, len(root) - 1):
            with self.subTest(index=index):
                diverged = bytearray(root)
                diverged[index] ^= 0x01
                with self.assertRaises(AssertionError):
                    check_license_matches(root, bytes(diverged))
        with self.assertRaises(AssertionError):
            check_license_matches(root, root + b"\n")

    def test_package_readme_gives_every_documented_invocation(self) -> None:
        self.assertEqual(
            invocation_table(SKILL / "README.md", "Invocation"),
            invocation_table(ROOT / "docs" / "installation.md", "Client directories"),
            "skills/create-issue/README.md must give the invocation of every client "
            "in docs/installation.md",
        )

    def test_package_absolute_links_point_at_the_project(self) -> None:
        for path in sorted(SKILL.rglob("*.md")):
            for target in absolute_links(path):
                with self.subTest(path=path.relative_to(ROOT).as_posix(), target=target):
                    self.assertIsNotNone(
                        PROJECT_URL.match(target),
                        f"{path.relative_to(ROOT)}: absolute link outside the project: "
                        f"{target}",
                    )

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
            if path.relative_to(SKILL).as_posix() in PROJECT_URL_FILES:
                text = PROJECT_URL.sub("", text)
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
