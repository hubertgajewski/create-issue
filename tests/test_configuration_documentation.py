"""The user guide and the normative reference must describe the same `.create-issue.toml`.

`skills/create-issue/references/configuration.md` owns the schema an agent enforces;
`docs/configuration.md` restates every key for the person writing the file. A key added,
removed, retyped, or given a different default or accepted values in one document alone is
drift, and these tests fail with a message naming the key.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "skills" / "create-issue" / "references" / "configuration.md"
GUIDE = ROOT / "docs" / "configuration.md"

HEADING = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)
TOML_BLOCK = re.compile(r"^```toml\n(.*?)^```\s*$", re.DOTALL | re.MULTILINE)
# The first four cells of a key row. The reference has a fifth, Meaning, which the guide
# replaces with prose, so it is not compared.
KEY_ROW = re.compile(r"^\| `([^`]+)` \| ([^|]+?) \| ([^|]+?) \| ([^|]+?) \|", re.MULTILINE)
ENUM_CELL = re.compile(r"`[^`]+`(?:, `[^`]+`)+")
BACKTICKED = re.compile(r"`([^`]+)`")
FIELDS = ("type", "default", "accepted values")
TYPE_SHAPES = {
    "integer": "integer",
    "string": "string",
    "string array": ("array", "string"),
    "integer array": ("array", "integer"),
}


def section_of(text: str, heading: str) -> str:
    """The text under `## <heading>`, up to the next level-2 heading."""
    matches = [m for m in HEADING.finditer(text) if m.group(1) == heading]
    if not matches:
        raise AssertionError(f"no '## {heading}' section")
    start = matches[0].end()
    following = HEADING.search(text, start)
    return text[start:following.start() if following else len(text)]


def key_rows(text: str) -> dict[str, tuple[str, ...]]:
    """Map each key in the `## Keys` section to its type, default, and accepted values."""
    rows: dict[str, tuple[str, ...]] = {}
    for key, *cells in KEY_ROW.findall(section_of(text, "Keys")):
        if key in rows:
            raise AssertionError(f"{key}: documented in more than one row")
        rows[key] = tuple(" ".join(cell.split()) for cell in cells)
    return rows


def drift(reference: dict[str, tuple[str, ...]], guide: dict[str, tuple[str, ...]]) -> list[str]:
    messages = [
        f"{key}: in the reference but missing from the guide"
        for key in sorted(reference.keys() - guide.keys())
    ]
    messages += [
        f"{key}: in the guide but absent from the reference"
        for key in sorted(guide.keys() - reference.keys())
    ]
    for key in sorted(reference.keys() & guide.keys()):
        for field, expected, actual in zip(FIELDS, reference[key], guide[key]):
            if expected != actual:
                messages.append(
                    f"{key}: {field} is {actual!r} in the guide but {expected!r} in the reference"
                )
    return messages


def drift_between(reference_text: str, guide_text: str) -> list[str]:
    return drift(key_rows(reference_text), key_rows(guide_text))


def value_shape(value: object) -> object:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        shapes = {value_shape(item) for item in value}
        if len(shapes) > 1:
            raise AssertionError(f"mixed array: {value!r}")
        return ("array", shapes.pop() if shapes else "empty")
    raise AssertionError(f"unsupported TOML value: {value!r}")


def leaf_values(document: dict[str, object]) -> list[tuple[str, object]]:
    """Every leaf key path with its value; arrays of tables use `name[]`."""
    leaves: list[tuple[str, object]] = []

    def visit(table: dict[str, object], prefix: str) -> None:
        for key, value in table.items():
            path = f"{prefix}{key}"
            if isinstance(value, dict):
                visit(value, f"{path}.")
            elif isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
                for entry in value:
                    visit(entry, f"{path}[].")
            else:
                leaves.append((path, value))

    visit(document, "")
    return leaves


class ConfigurationDocumentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.reference_text = REFERENCE.read_text(encoding="utf-8")
        self.guide_text = GUIDE.read_text(encoding="utf-8")
        self.reference = key_rows(self.reference_text)

    def assert_no_drift(self, messages: list[str]) -> None:
        if messages:
            self.fail(
                "docs/configuration.md and references/configuration.md disagree:\n"
                + "\n".join(messages)
            )

    def test_reference_keys_table_is_read(self) -> None:
        self.assertIn("version", self.reference)
        self.assertIn("milestone.rules[].when", self.reference)
        self.assertGreater(len(self.reference), 20)

    def test_guide_documents_every_key_as_the_reference_does(self) -> None:
        self.assert_no_drift(drift_between(self.reference_text, self.guide_text))

    def test_guide_examples_use_only_reference_keys_and_types(self) -> None:
        blocks = TOML_BLOCK.findall(self.guide_text)
        self.assertGreater(len(blocks), 2)
        for index, block in enumerate(blocks, start=1):
            for key, value in leaf_values(tomllib.loads(block)):
                with self.subTest(block=index, key=key):
                    self.assertIn(key, self.reference, f"{key}: not a reference key")
                    declared = TYPE_SHAPES[self.reference[key][0]]
                    shape = value_shape(value)
                    self.assertTrue(
                        shape == declared
                        or (isinstance(declared, tuple) and shape == ("array", "empty")),
                        f"{key}: {shape} is not the declared {self.reference[key][0]}",
                    )

    def test_full_example_sets_every_key_to_an_accepted_value(self) -> None:
        blocks = TOML_BLOCK.findall(section_of(self.guide_text, "Full example"))
        self.assertEqual(len(blocks), 1, "expected one TOML block under '## Full example'")
        document = tomllib.loads(blocks[0])
        leaves = leaf_values(document)
        self.assertEqual(document.get("version"), 1)
        missing = sorted(self.reference.keys() - {key for key, _ in leaves})
        self.assertEqual(missing, [], "keys missing from the full example")
        for key, value in leaves:
            accepted = self.reference[key][2]
            if ENUM_CELL.fullmatch(accepted):
                with self.subTest(key=key):
                    self.assertIn(value, BACKTICKED.findall(accepted), key)


class DriftDetectionTests(unittest.TestCase):
    """Each kind of drift AC4 names must fail, and the message must name the key.

    The guide here is rebuilt from the reference's own rows rather than read from
    `docs/configuration.md`, so real drift is reported once, by the test above, instead of
    also breaking every fixture edit below.
    """

    def setUp(self) -> None:
        self.reference_text = REFERENCE.read_text(encoding="utf-8")
        rows = "".join(
            f"| `{key}` | {' | '.join(cells)} |\n"
            for key, cells in key_rows(self.reference_text).items()
        )
        self.guide_text = f"# Configuration\n\n## Keys\n\n{rows}"

    def test_the_rebuilt_guide_has_no_drift(self) -> None:
        self.assertEqual(drift_between(self.reference_text, self.guide_text), [])

    def edited(self, text: str, old: str, new: str) -> str:
        self.assertEqual(text.count(old), 1, f"fixture text not found exactly once: {old!r}")
        return text.replace(old, new)

    def assert_drift_names(self, key: str, reference_text: str, guide_text: str) -> None:
        messages = drift_between(reference_text, guide_text)
        self.assertTrue(messages, f"drift in {key} went undetected")
        self.assertTrue(all(m.startswith(f"{key}: ") for m in messages), messages)

    def test_a_key_removed_from_the_guide_is_named(self) -> None:
        row = "| `labels.policy` | string | `\"existing-only\"` | `existing-only`, `propose-new`, `none` |\n"
        guide = self.edited(self.guide_text, row, "")
        self.assert_drift_names("labels.policy", self.reference_text, guide)

    def test_a_key_the_reference_lacks_is_named(self) -> None:
        row = "| `labels.epic` | string array | `[]` | label names |\n"
        guide = self.edited(
            self.guide_text, row, row + "| `labels.chore` | string array | `[]` | label names |\n"
        )
        self.assert_drift_names("labels.chore", self.reference_text, guide)

    def test_a_default_changed_in_the_guide_is_named(self) -> None:
        guide = self.edited(
            self.guide_text,
            "| `title.max_length` | integer | `72` |",
            "| `title.max_length` | integer | `80` |",
        )
        self.assert_drift_names("title.max_length", self.reference_text, guide)

    def test_an_accepted_value_changed_in_the_reference_is_named(self) -> None:
        reference = self.edited(
            self.reference_text,
            "| `provider` | string | `\"auto\"` | `auto`, `github`, `gitlab` |",
            "| `provider` | string | `\"auto\"` | `auto`, `github`, `gitlab`, `gitea` |",
        )
        self.assert_drift_names("provider", reference, self.guide_text)

    def test_a_type_changed_in_the_guide_is_named(self) -> None:
        guide = self.edited(
            self.guide_text,
            "| `estimation.warn_at` | integer |",
            "| `estimation.warn_at` | string |",
        )
        self.assert_drift_names("estimation.warn_at", self.reference_text, guide)


if __name__ == "__main__":
    unittest.main()
