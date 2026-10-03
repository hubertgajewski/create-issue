"""`scripts/normalize_reference.py` is the executable form of `references/reference-grammar.md`.
These tests run it as an agent does, through its command line, and check the JSON contract,
the exit status, and that a rejection never echoes the rejected text."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "create-issue" / "scripts" / "normalize_reference.py"
GITLAB_TARGET = ("--provider", "gitlab", "--host", "gitlab.com", "--project", "group/project")
GITHUB_TARGET = ("--provider", "github", "--host", "github.com", "--project", "owner/repo")


def run(*args: str) -> subprocess.CompletedProcess[str]:
    # -B keeps the package free of __pycache__, which the package tests would read as text.
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


class NormalizeReferenceTests(unittest.TestCase):
    def accept(self, *args: str) -> dict[str, object]:
        result = run(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout)

    def reject(self, *args: str, reason: str) -> str:
        result = run(*args)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.startswith("error: "), result.stderr)
        self.assertIn(reason, result.stderr)
        return result.stderr

    # AC1
    def test_project_url_normalizes(self) -> None:
        self.assertEqual(
            self.accept("project", "--ref", "https://gitlab.com/group/subgroup/project.git"),
            {
                "host": "gitlab.com",
                "issue": None,
                "project": "group/subgroup/project",
                "provider": "gitlab",
            },
        )

    def test_project_url_variants_normalize(self) -> None:
        cases = {
            "  https://GitHub.com/owner/repo/  ": ("github", "github.com", "owner/repo"),
            "HTTPS://gitlab.com/group/project?tab=readme#top": ("gitlab", "gitlab.com", "group/project"),
            "https://gitlab.example.com:443/group/project": ("gitlab", "gitlab.example.com", "group/project"),
            "https://gitlab.example.com:8443/group/project": ("gitlab", "gitlab.example.com:8443", "group/project"),
            "https://code.example.com/group/project": (None, "code.example.com", "group/project"),
        }
        for reference, (provider, host, project) in cases.items():
            with self.subTest(reference=reference):
                self.assertEqual(
                    self.accept("project", "--ref", reference),
                    {"host": host, "issue": None, "project": project, "provider": provider},
                )

    def test_project_path_has_no_host(self) -> None:
        self.assertEqual(
            self.accept("project", "--ref", "group/subgroup/project"),
            {"host": None, "issue": None, "project": "group/subgroup/project", "provider": None},
        )
        self.assertEqual(
            self.accept("project", "--ref", "owner/repo", "--provider", "github")["provider"],
            "github",
        )

    def test_explicit_provider_resolves_a_neutral_host(self) -> None:
        self.assertEqual(
            self.accept(
                "project", "--ref", "https://code.example.com/owner/repo", "--provider", "github"
            )["provider"],
            "github",
        )

    def test_malformed_projects_are_rejected(self) -> None:
        cases = {
            "project": "project path",
            "group//project": "project path",
            "group/../project": "project path",
            "group/-project": "project path",
            "group/pro ject": "printable ASCII",
            "group/projé": "printable ASCII",
            "group/project#4": "project path",
            "https://gitlab.com/group/pro%6aect": "percent-encoding",
            "https://gitlab.com/group/project/-/tree/main": "not a project URL",
            "https://gitlab.com/groups/group": "group-level",
            "https://gitlab.com/group": "project path",
            "https://gitlab.com/group/.git": "project path",
            "https://gitlab.com/": "project path",
            "https://github.com/owner/repo/pull/3": "exactly two",
            "ssh://gitlab.com/group/project": "HTTPS",
            "https://[::1]/group/project": "host",
            "https://gitlab.com:0/group/project": "port",
            "https://gitlab.com:65536/group/project": "port",
            "https://gitlab.github.example.com/group/project": "both",
        }
        for reference, reason in cases.items():
            with self.subTest(reference=reference):
                self.reject("project", "--ref", reference, reason=reason)

    def test_github_project_needs_exactly_two_components(self) -> None:
        self.reject(
            "project", "--ref", "group/subgroup/project", "--provider", "github", reason="exactly two"
        )

    def test_provider_contradicting_the_host_is_rejected(self) -> None:
        self.reject(
            "project", "--ref", "https://gitlab.com/group/project", "--provider", "github",
            reason="contradicts",
        )

    # AC2
    def test_issue_and_work_item_urls_normalize_as_parents(self) -> None:
        for reference in (
            "https://gitlab.com/group/project/-/issues/12",
            "https://gitlab.com/group/project/-/work_items/12",
            "https://gitlab.com/group/project/-/work_items/12/#note_1",
        ):
            with self.subTest(reference=reference):
                self.assertEqual(
                    self.accept("parent", "--ref", reference, *GITLAB_TARGET),
                    {"host": "gitlab.com", "issue": 12, "project": "group/project", "provider": "gitlab"},
                )

    def test_github_issue_url_normalizes_as_parent(self) -> None:
        self.assertEqual(
            self.accept("parent", "--ref", "https://github.com/other/repo/issues/7", *GITHUB_TARGET),
            {"host": "github.com", "issue": 7, "project": "other/repo", "provider": "github"},
        )

    def test_short_parent_references_resolve_against_the_target(self) -> None:
        cases = {
            "#12": "group/project",
            "12": "group/project",
            "other/sub/project#12": "other/sub/project",
        }
        for reference, project in cases.items():
            with self.subTest(reference=reference):
                self.assertEqual(
                    self.accept("parent", "--ref", reference, *GITLAB_TARGET),
                    {"host": "gitlab.com", "issue": 12, "project": project, "provider": "gitlab"},
                )

    def test_parent_host_comparison_is_normalized(self) -> None:
        result = self.accept(
            "parent", "--ref", "https://GitLab.example.com:443/group/project/-/issues/3",
            "--provider", "gitlab", "--host", "gitlab.example.com", "--project", "group/project",
        )
        self.assertEqual(result["host"], "gitlab.example.com")

    def test_malformed_issue_numbers_are_rejected(self) -> None:
        for reference in ("#0", "#012", "0", "#1" + "0" * 20, "#-1", "#", "group/project#"):
            with self.subTest(reference=reference):
                self.reject("parent", "--ref", reference, *GITLAB_TARGET, reason="error: ")

    # AC3
    def test_plain_http_is_rejected(self) -> None:
        for mode, target in (("project", ()), ("parent", GITLAB_TARGET)):
            with self.subTest(mode=mode):
                self.reject(
                    mode, "--ref", "http://gitlab.com/group/project/-/issues/12", *target,
                    reason="plain HTTP",
                )

    # AC4
    def test_user_information_is_rejected_without_being_echoed(self) -> None:
        secret = "glpat-SECRETVALUE123"
        for mode, target, reference in (
            ("project", (), f"https://deploy:{secret}@gitlab.com/group/project.git"),
            ("project", (), f"https://{secret}@gitlab.com/group/project"),
            ("parent", GITLAB_TARGET, f"https://deploy:{secret}@gitlab.com/group/project/-/issues/1"),
            ("project", (), f"http://deploy:{secret}@gitlab.com/group/project"),
        ):
            with self.subTest(mode=mode, reference=reference.replace(secret, "SECRET")):
                stderr = self.reject(mode, "--ref", reference, *target, reason="error: ")
                self.assertNotIn(secret, stderr)
                self.assertNotIn("deploy", stderr)

    def test_usage_errors_do_not_echo_arguments(self) -> None:
        secret = "glpat-SECRETVALUE123"
        result = run("project", "--ref", "group/project", f"https://u:{secret}@gitlab.com/x/y")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertNotIn(secret, result.stderr)

    # AC5
    def test_parent_on_another_host_is_rejected(self) -> None:
        for reference in (
            "https://gitlab.example.com/group/project/-/issues/12",
            "https://gitlab.com:8443/group/project/-/issues/12",
        ):
            with self.subTest(reference=reference):
                self.reject("parent", "--ref", reference, *GITLAB_TARGET, reason="another host")

    # AC6
    def test_non_issue_urls_are_not_parents(self) -> None:
        cases = {
            "https://gitlab.com/group/project/-/merge_requests/12": GITLAB_TARGET,
            "https://gitlab.com/group/project/-/blob/main/README.md": GITLAB_TARGET,
            "https://gitlab.com/group/project": GITLAB_TARGET,
            "https://gitlab.com/group/project/issues/12": GITLAB_TARGET,
            "https://gitlab.com/groups/group/-/work_items/12": GITLAB_TARGET,
            "https://github.com/owner/repo/pull/12": GITHUB_TARGET,
            "https://github.com/owner/repo/blob/main/README.md": GITHUB_TARGET,
            "https://github.com/owner/repo": GITHUB_TARGET,
            "https://github.com/owner/repo/-/issues/12": GITHUB_TARGET,
        }
        for reference, target in cases.items():
            with self.subTest(reference=reference):
                self.reject("parent", "--ref", reference, *target, reason="error: ")

    def test_parent_mode_requires_a_valid_frozen_target(self) -> None:
        self.reject("parent", "--ref", "#1", reason="error: ")
        self.reject(
            "parent", "--ref", "#1", "--provider", "github", "--host", "gitlab.com",
            "--project", "owner/repo", reason="contradicts",
        )
        self.reject(
            "parent", "--ref", "#1", "--provider", "github", "--host", "github.com",
            "--project", "group/sub/repo", reason="exactly two",
        )

    def test_oversized_reference_is_rejected(self) -> None:
        self.reject("project", "--ref", "group/" + "a" * 4096, reason="too long")


if __name__ == "__main__":
    unittest.main()
