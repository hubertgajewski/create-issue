"""Parsing shared by the tests that read `.create-issue.toml` documentation.

`test_configuration.py` checks the reference against itself and
`test_configuration_documentation.py` checks the user guide against the reference, so both
must read sections, key rows, and TOML values the same way.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "skills" / "create-issue" / "references" / "configuration.md"

HEADING = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)
TOML_BLOCK = re.compile(r"^```toml\n(.*?)^```\s*$", re.DOTALL | re.MULTILINE)
# The first four cells of a key row: key, type, default, and accepted values.
KEY_ROW = re.compile(r"^\| `([^`]+)` \| ([^|]+?) \| ([^|]+?) \| ([^|]+?) \|", re.MULTILINE)
BACKTICKED = re.compile(r"`([^`]+)`")
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


def key_cells(text: str) -> dict[str, tuple[str, ...]]:
    """Map each key in the `## Keys` section to its type, default, and accepted values."""
    rows: dict[str, tuple[str, ...]] = {}
    for key, *cells in KEY_ROW.findall(section_of(text, "Keys")):
        if key in rows:
            raise AssertionError(f"{key}: documented in more than one row")
        rows[key] = tuple(" ".join(cell.split()) for cell in cells)
    return rows


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


def compatible(actual: object, declared: object) -> bool:
    """An empty array matches any declared array type."""
    return actual == declared or (
        isinstance(declared, tuple) and actual == ("array", "empty")
    )


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
