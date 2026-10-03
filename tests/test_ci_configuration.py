"""`.gitlab-ci.yml` decides which pushes and merge requests are tested. Its workflow rule
order decides whether a pipeline runs at all, and an image referenced by tag can change
under a passing pipeline, so these tests pin the rules, the Python matrix, and image
digests, and name what breaks them."""

from __future__ import annotations

import copy
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CI_FILE = ROOT / ".gitlab-ci.yml"

ENTRY = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_.-]*):(?: (?P<value>.+))?")
PLAIN_SCALAR = re.compile(r"[^\s&*!|>'\"{}\[\],%@`#][^\t]*")
# Plain scalars YAML resolves to a boolean, null, or number, such as `true` or `3.10`.
TYPED_PLAIN_SCALAR = re.compile(
    r"(?i:true|false|yes|no|on|off|null|~)|[-+.0-9][-+.0-9_eE]*"
)
VARIABLE_REFERENCE = re.compile(r"\$(?:\{(\w+)\}|(\w+))")
PINNED_IMAGE = re.compile(r"[a-z0-9][a-z0-9._/:-]*@sha256:[0-9a-f]{64}")
PYTHON_IMAGE_TAG = re.compile(r"python:(\d+\.\d+)(?![0-9.])")

# Top-level keys that configure the pipeline rather than define a job.
GLOBAL_KEYWORDS = {
    "default",
    "include",
    "stages",
    "variables",
    "workflow",
    "spec",
}

WEB_RULE = {"if": '$CI_PIPELINE_SOURCE == "web"'}
CI_ENABLED_GATE = {"if": '$CI_ENABLED == "false"', "when": "never"}
# Order matters: GitLab applies the first matching rule.
WORKFLOW_RULES = (
    WEB_RULE,
    CI_ENABLED_GATE,
    {"if": '$CI_PIPELINE_SOURCE == "merge_request_event"'},
    {"if": "$CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS", "when": "never"},
    {"if": "$CI_COMMIT_BRANCH"},
)
SUPPORTED_PYTHONS = {"3.10", "3.14"}
SUITE_SCRIPT = [
    "python -m pip install --require-hashes -r requirements-test.txt",
    "python -m unittest discover -s tests -v",
]

# One significant source line: number, indentation, and text without the indentation.
Line = tuple[int, int, str]


def load_ci_configuration() -> dict[str, object]:
    """Parse the block-style YAML subset `.gitlab-ci.yml` is written in.

    Supports mappings, block sequences, plain scalars, and double-quoted scalars.
    Anything else, including anchors, flow collections, and multi-line strings, is
    rejected so that a construct this reader would misread fails instead of passing.
    """
    lines: list[Line] = []
    for number, raw in enumerate(CI_FILE.read_text(encoding="utf-8").splitlines(), start=1):
        text = raw.lstrip(" ")
        if not text or text.startswith("#"):
            continue
        if "\t" in raw:
            raise AssertionError(f".gitlab-ci.yml:{number}: tab character")
        lines.append((number, len(raw) - len(text), text))
    if not lines:
        raise AssertionError(".gitlab-ci.yml: empty file")
    document, index = _block(lines, 0, 0)
    if index != len(lines):
        raise AssertionError(f".gitlab-ci.yml:{lines[index][0]}: unexpected indentation")
    if not isinstance(document, dict):
        raise AssertionError(".gitlab-ci.yml: expected a top-level mapping")
    return document


def _block(lines: list[Line], index: int, indent: int) -> tuple[object, int]:
    if lines[index][2].startswith("- "):
        return _sequence(lines, index, indent)
    return _mapping(lines, index, indent)


def _sequence(lines: list[Line], index: int, indent: int) -> tuple[list[object], int]:
    items: list[object] = []
    while index < len(lines) and lines[index][1] == indent:
        if not lines[index][2].startswith("- "):
            break
        number, _, text = lines[index]
        item = text[2:].lstrip(" ")
        if ENTRY.fullmatch(item) or item.startswith("- "):
            # The item's first line opens a nested block at the item's content column.
            lines[index] = (number, indent + len(text) - len(item), item)
            value, index = _block(lines, index, lines[index][1])
        else:
            value, index = _scalar(item, number), index + 1
        items.append(value)
    return items, index


def _mapping(
    lines: list[Line], index: int, indent: int
) -> tuple[dict[str, object], int]:
    mapping: dict[str, object] = {}
    while index < len(lines) and lines[index][1] == indent:
        number, _, text = lines[index]
        match = ENTRY.fullmatch(text)
        if match is None:
            raise AssertionError(f".gitlab-ci.yml:{number}: unsupported syntax")
        key = match.group("key")
        if key in mapping:
            raise AssertionError(f".gitlab-ci.yml:{number}: duplicate key {key}")
        index += 1
        if match.group("value") is not None:
            mapping[key] = _scalar(match.group("value"), number)
        elif index < len(lines) and lines[index][1] > indent:
            mapping[key], index = _block(lines, index, lines[index][1])
        else:
            raise AssertionError(f".gitlab-ci.yml:{number}: {key} has no value")
    return mapping, index


def _scalar(text: str, number: int) -> str:
    if text.startswith('"'):
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            value = None
        if isinstance(value, str):
            return value
    elif TYPED_PLAIN_SCALAR.fullmatch(text):
        raise AssertionError(f".gitlab-ci.yml:{number}: quote {text} to keep it a string")
    elif PLAIN_SCALAR.fullmatch(text) and " #" not in text and ": " not in text:
        return text
    raise AssertionError(f".gitlab-ci.yml:{number}: unsupported scalar {text}")


def describe(rule: object) -> str:
    if isinstance(rule, dict):
        return "`" + ", ".join(f"{key}: {value}" for key, value in rule.items()) + "`"
    return f"`{rule}`"


def workflow_rule_problems(rules: object) -> list[str]:
    """Name each rule that is missing, unexpected, or out of order."""
    if not isinstance(rules, list):
        return ["workflow:rules must be a list"]
    problems = [
        f"workflow rule {describe(rule)} is unexpected"
        for rule in rules
        if rule not in WORKFLOW_RULES
    ]
    positions = []
    for rule in WORKFLOW_RULES:
        if rule in rules:
            positions.append((rules.index(rule), rule))
        else:
            problems.append(f"workflow rule {describe(rule)} is missing")
    for (before, earlier), (after, later) in zip(positions, positions[1:]):
        if before > after:
            problems.append(
                f"workflow rule {describe(earlier)} must precede {describe(later)}"
            )
    return problems


def jobs(document: dict[str, object]) -> dict[str, dict[str, object]]:
    """Visible jobs; hidden `.name` keys are templates, not jobs."""
    found = {}
    for name, value in document.items():
        if name in GLOBAL_KEYWORDS or name.startswith("."):
            continue
        if not isinstance(value, dict):
            raise AssertionError(f"{name}: expected a job mapping")
        found[name] = value
    return found


def matrix_entries(job: dict[str, object]) -> list[object]:
    parallel = job.get("parallel")
    if not isinstance(parallel, dict):
        return []
    matrix = parallel.get("matrix")
    return matrix if isinstance(matrix, list) else []


def job_images(name: str, job: dict[str, object], default_image: object) -> list[str]:
    """Every image the job can run, expanding a `parallel:matrix` image variable."""
    image = job.get("image", default_image)
    if isinstance(image, dict):
        image = image.get("name")
    if not isinstance(image, str):
        raise AssertionError(f"{name}: no image; the runner default is not pinned")
    variable = VARIABLE_REFERENCE.fullmatch(image)
    if variable is None:
        return [image]
    variable_name = variable.group(1) or variable.group(2)
    images = []
    for entry in matrix_entries(job):
        value = entry.get(variable_name) if isinstance(entry, dict) else None
        images.extend(value if isinstance(value, list) else [value])
    if not images:
        raise AssertionError(f"{name}: image {image} is not set by parallel:matrix")
    return images


def image_problems(document: dict[str, object]) -> list[str]:
    default = document.get("default")
    default_image = default.get("image") if isinstance(default, dict) else None
    problems = []
    for name, job in jobs(document).items():
        for image in job_images(name, job, default_image):
            if not isinstance(image, str) or not PINNED_IMAGE.fullmatch(image):
                problems.append(f"{name}: image {image} is not pinned by manifest digest")
    return problems


class CIConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = load_ci_configuration()

    def workflow_rules(self) -> object:
        workflow = self.document.get("workflow")
        self.assertIsInstance(workflow, dict, "workflow must be a mapping")
        assert isinstance(workflow, dict)
        return workflow.get("rules")

    def test_workflow_rules_are_complete_and_ordered(self) -> None:
        self.assertEqual(workflow_rule_problems(self.workflow_rules()), [])

    def test_rule_check_names_a_web_rule_moved_after_the_gate(self) -> None:
        rules = copy.deepcopy(self.workflow_rules())
        assert isinstance(rules, list)
        rules.remove(WEB_RULE)
        rules.insert(rules.index(CI_ENABLED_GATE) + 1, WEB_RULE)

        self.assertEqual(
            workflow_rule_problems(rules),
            [
                f"workflow rule {describe(WEB_RULE)} must precede "
                f"{describe(CI_ENABLED_GATE)}"
            ],
        )

    def test_ci_enabled_is_declared_with_a_description(self) -> None:
        variables = self.document.get("variables")
        self.assertIsInstance(variables, dict, "variables must be a mapping")
        assert isinstance(variables, dict)
        declaration = variables.get("CI_ENABLED")

        self.assertIsInstance(declaration, dict, "CI_ENABLED needs a value and description")
        assert isinstance(declaration, dict)
        self.assertEqual(declaration.get("value"), "true")
        self.assertIn("false", str(declaration.get("description", "")))

    def test_suite_runs_on_each_supported_python(self) -> None:
        job = jobs(self.document).get("test")
        self.assertIsNotNone(job, "a test job is required")
        assert job is not None

        self.assertEqual(job.get("script", [])[-2:], SUITE_SCRIPT)
        images = job_images("test", job, None)
        versions = []
        for image in images:
            match = PYTHON_IMAGE_TAG.match(str(image))
            self.assertIsNotNone(match, f"test: image {image} is not a tagged python image")
            assert match is not None
            versions.append(match.group(1))
        self.assertEqual(sorted(versions), sorted(SUPPORTED_PYTHONS))

    def test_job_images_are_pinned_by_digest(self) -> None:
        self.assertEqual(image_problems(self.document), [])

    def test_image_check_names_a_job_using_a_tag_alone(self) -> None:
        document = copy.deepcopy(self.document)
        entry = matrix_entries(jobs(document)["test"])[-1]
        assert isinstance(entry, dict)
        entry["PYTHON_IMAGE"] = "python:3.14-slim"

        self.assertEqual(
            image_problems(document),
            ["test: image python:3.14-slim is not pinned by manifest digest"],
        )


if __name__ == "__main__":
    unittest.main()
