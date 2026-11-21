"""Tests for 5.3 (#51), adapted from Zay Lin Myat's preserved PR #82.

Each rule in the table names the tests that prove it. These tests fail if a named test is renamed
or deleted, or if a required rule is missing from the table.
"""

import ast
import re

import pytest

from app.core.config import BASE_DIR

README = (BASE_DIR / "README.md").read_text(encoding="utf-8")

REQUIRED_RULES = [
    "A deactivated customer can't create or modify a cart",
    "At most one active cart per customer",
    "Cart items come from only one restaurant",
    "Unavailable, deactivated or nonexistent items can't be added",
    "Quantities are valid",
    "The backend calculates totals",
    "Checkout revalidates menu availability and prices",
    "Checkout requires a valid customer",
    "Orders are only created from a valid cart",
    "The cart is not cleared until the order is saved",
    "Relationships stay valid after restarts",
]


def rules_table() -> dict[str, str]:
    """Map each rule in the README's Business Rules table to its row."""
    section = README.split("## Business Rules", 1)[1].split("\n## ", 1)[0]
    rows = {}
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0] not in ("Rule", "---"):
            rows[cells[0]] = line
    return rows


def functions_in(file_name: str) -> set[str]:
    tree = ast.parse((BASE_DIR / file_name).read_text(encoding="utf-8"))
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


def test_every_required_rule_is_in_the_table():
    assert set(rules_table()) == set(REQUIRED_RULES)


@pytest.mark.parametrize("rule", REQUIRED_RULES)
def test_every_rule_names_existing_tests(rule):
    row = rules_table()[rule]
    references = re.findall(r"`(tests/[\w/]+\.py)::(\w+)`", row)

    assert references, f"No test named for: {rule}"
    for file_name, test_name in references:
        assert test_name in functions_in(file_name), f"{file_name}::{test_name} does not exist"
