"""`references/configuration.md` states the `.create-issue.toml` schema three ways: a TOML
schema block, a `## Keys` table, and worked examples. An agent enforces whichever it reads,
so these tests require all three to describe the same keys, types, and accepted values."""

from __future__ import annotations

import re
import unittest

from configuration_schema import (
    BACKTICKED,
    REFERENCE,
    TOML_BLOCK,
    TYPE_SHAPES,
    compatible,
    key_cells,
    leaf_values,
    section_of,
    tomllib,
    value_shape,
)


TABLE_HEADER = re.compile(r"^\[\[?([a-z_.]+)\]\]?\s*$")
ASSIGNMENT = re.compile(r"^([a-z_]+)\s*=")
ENUM_COMMENT = re.compile(r"#\s*([a-z-]+(?:\s*\|\s*[a-z-]+)+)\s*$")

# Keys whose accepted values form a closed set. Pinned so that a new enum key, or an
# enum comment reworded until it is no longer recognized, fails instead of escaping checks.
ENUM_KEYS = {
    "provider",
    "title.prefix",
    "labels.policy",
    "milestone.policy",
    "estimation.target",
}


def reference_section(heading: str) -> str:
    return section_of(REFERENCE.read_text(encoding="utf-8"), heading)


def schema_block() -> str:
    blocks = TOML_BLOCK.findall(reference_section("Schema"))
    if len(blocks) != 1:
        raise AssertionError("expected exactly one TOML block under '## Schema'")
    return blocks[0]


def leaf_shapes(document: dict[str, object]) -> dict[str, object]:
    """Map every leaf key path to its shape; arrays of tables use `name[]`."""
    return {path: value_shape(value) for path, value in leaf_values(document)}


def key_table() -> dict[str, dict[str, object]]:
    return {
        key: {
            "type": TYPE_SHAPES[type_name],
            "default": default,
            "accepted": BACKTICKED.findall(accepted),
        }
        for key, (type_name, default, accepted) in key_cells(
            REFERENCE.read_text(encoding="utf-8")
        ).items()
    }


def schema_enums() -> dict[str, set[str]]:
    """Enum comments `key = "x"  # a | b | c`, keyed by full dotted path."""
    enums: dict[str, set[str]] = {}
    table = ""
    for line in schema_block().splitlines():
        header = TABLE_HEADER.match(line.strip())
        if header:
            table = header.group(1) + "."
            continue
        assignment = ASSIGNMENT.match(line)
        comment = ENUM_COMMENT.search(line)
        if assignment and comment:
            values = {token.strip() for token in comment.group(1).split("|")}
            enums[f"{table}{assignment.group(1)}"] = values
    return enums


def lookup(document: dict[str, object], dotted: str) -> object:
    value: object = document
    for part in dotted.split("."):
        assert isinstance(value, dict)
        value = value[part]
    return value


class ConfigurationReferenceTests(unittest.TestCase):
    def test_schema_parses_and_pins_the_version(self) -> None:
        document = tomllib.loads(schema_block())
        self.assertEqual(document["version"], 1)

    def test_keys_table_documents_exactly_the_schema_keys(self) -> None:
        schema = set(leaf_shapes(tomllib.loads(schema_block())))
        table = set(key_table())
        self.assertEqual(sorted(schema - table), [], "schema keys missing from Keys table")
        self.assertEqual(sorted(table - schema), [], "Keys table rows absent from schema")

    def test_keys_table_types_match_schema_values(self) -> None:
        schema = leaf_shapes(tomllib.loads(schema_block()))
        for key, row in key_table().items():
            with self.subTest(key=key):
                self.assertTrue(compatible(schema[key], row["type"]), schema[key])

    def test_documented_defaults_have_the_declared_type(self) -> None:
        for key, row in key_table().items():
            default = row["default"]
            if default in {"required", "none"}:
                continue
            with self.subTest(key=key):
                literal = BACKTICKED.fullmatch(default)
                self.assertIsNotNone(literal, f"default must be one backticked literal: {default}")
                assert literal is not None
                value = tomllib.loads(f"v = {literal.group(1)}")["v"]
                self.assertTrue(compatible(value_shape(value), row["type"]))

    def test_every_enum_key_is_registered(self) -> None:
        self.assertEqual(set(schema_enums()), ENUM_KEYS)

    def test_enum_values_agree_between_schema_and_keys_table(self) -> None:
        table = key_table()
        for key, values in schema_enums().items():
            with self.subTest(key=key):
                self.assertEqual(set(table[key]["accepted"]), values)

    def test_enum_defaults_and_schema_values_are_accepted(self) -> None:
        document = tomllib.loads(schema_block())
        table = key_table()
        for key, values in schema_enums().items():
            with self.subTest(key=key):
                self.assertIn(lookup(document, key), values)
                default = tomllib.loads(f"v = {table[key]['default'].strip('`')}")["v"]
                self.assertIn(default, values)

    def test_examples_use_only_documented_keys_and_values(self) -> None:
        schema = leaf_shapes(tomllib.loads(schema_block()))
        enums = schema_enums()
        examples = TOML_BLOCK.findall(reference_section("Examples"))
        self.assertGreaterEqual(len(examples), 2)
        for index, block in enumerate(examples, start=1):
            with self.subTest(example=index):
                document = tomllib.loads(block)
                self.assertEqual(document.get("version"), 1)
                for key, shape in leaf_shapes(document).items():
                    self.assertIn(key, schema, f"undocumented key {key}")
                    self.assertTrue(compatible(shape, schema[key]), key)
                    if key in enums:
                        self.assertIn(lookup(document, key), enums[key])

    def test_category_examples_declare_categories(self) -> None:
        for block in TOML_BLOCK.findall(reference_section("Examples")):
            title = tomllib.loads(block).get("title", {})
            if title.get("prefix") == "category":
                self.assertTrue(title.get("categories"))

    def test_github_project_examples_are_complete(self) -> None:
        for block in TOML_BLOCK.findall(reference_section("Examples")):
            document = tomllib.loads(block)
            if document.get("estimation", {}).get("target") == "github-project":
                project = document.get("github_project", {})
                self.assertIn("owner", project)
                self.assertIn("number", project)


if __name__ == "__main__":
    unittest.main()
