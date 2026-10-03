from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATION_BLOCK = re.compile(
    r"^## Validation\n\n```bash\n(?P<commands>.*?)^```$", re.DOTALL | re.MULTILINE
)
OWNERSHIP_ROW = re.compile(r"^\| `(?P<path>[^`]+)` \|", re.MULTILINE)


def section(text: str, heading: str) -> str:
    """Return the body of a level-2 section, up to the next level-2 heading."""
    match = re.search(
        rf"^## {re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)",
        text,
        re.DOTALL | re.MULTILINE,
    )
    if match is None:
        raise AssertionError(f"missing section: ## {heading}")
    return match.group("body")


def validation_commands(name: str) -> str:
    match = VALIDATION_BLOCK.search((ROOT / name).read_text(encoding="utf-8"))
    if match is None:
        raise AssertionError(f"{name}: missing bash block under ## Validation")
    return match.group("commands")


def ownership_paths() -> list[str]:
    text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    return OWNERSHIP_ROW.findall(section(text, "Documentation ownership"))


def tracked_root_markdown() -> list[str]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--", ":(glob)*.md"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise unittest.SkipTest(f"tracked files unavailable: {error}") from error
    return sorted(name for name in result.stdout.decode().split("\0") if name)


class RepositoryDocsTests(unittest.TestCase):
    def test_contributing_validation_matches_agents_md(self) -> None:
        self.assertEqual(
            validation_commands("CONTRIBUTING.md"),
            validation_commands("AGENTS.md"),
            "CONTRIBUTING.md and AGENTS.md must give identical validation commands",
        )

    def test_ownership_table_paths_exist(self) -> None:
        paths = ownership_paths()
        self.assertTrue(paths, "CONTRIBUTING.md: empty documentation ownership table")
        for path in paths:
            with self.subTest(path=path):
                target = ROOT / path
                exists = target.is_dir() if path.endswith("/") else target.is_file()
                self.assertTrue(exists, f"ownership table names missing {path}")

    def test_ownership_table_covers_owned_documents(self) -> None:
        paths = set(ownership_paths())
        required = [
            *tracked_root_markdown(),
            "skills/create-issue/SKILL.md",
            "skills/create-issue/references/",
        ]
        for path in required:
            with self.subTest(path=path):
                self.assertIn(path, paths, f"ownership table has no row for {path}")


if __name__ == "__main__":
    unittest.main()
