"""test_transforms: Unit tests for the transforms module in the services.general package."""

from typing import Any

import pytest

from app.services.general import transforms
from tests import TestCase


class ToBoolTestCase(TestCase):
    """Test case for the to_bool function."""

    value: Any
    expected_out: bool


TO_BOOL_TEST_CASES = [
    ToBoolTestCase(id="bool_true", value=True, expected_out=True),
    ToBoolTestCase(id="bool_false", value=False, expected_out=False),
    ToBoolTestCase(id="str_true", value="true", expected_out=True),
    ToBoolTestCase(id="str_false", value="false", expected_out=False),
    ToBoolTestCase(id="str_t", value="t", expected_out=True),
    ToBoolTestCase(id="str_f", value="f", expected_out=False),
    ToBoolTestCase(id="str_yes", value="yes", expected_out=True),
    ToBoolTestCase(id="str_no", value="no", expected_out=False),
    ToBoolTestCase(id="str_y", value="y", expected_out=True),
    ToBoolTestCase(id="str_n", value="n", expected_out=False),
    ToBoolTestCase(id="str_1", value="1", expected_out=True),
    ToBoolTestCase(id="str_0", value="0", expected_out=False),
    ToBoolTestCase(id="int_1", value=1, expected_out=True),
    ToBoolTestCase(id="int_0", value=0, expected_out=False),
    ToBoolTestCase(id="float_1", value=1.0, expected_out=False),
    ToBoolTestCase(id="float_0", value=0.0, expected_out=False),
    ToBoolTestCase(id="str_empty", value="", expected_out=False),
    ToBoolTestCase(id="str_space", value=" ", expected_out=False),
    ToBoolTestCase(id="str_none", value=None, expected_out=False),
    ToBoolTestCase(id="str_other", value="other", expected_out=False),
]


@ToBoolTestCase.parametrize(TO_BOOL_TEST_CASES)
def test_to_bool(test_case: ToBoolTestCase) -> None:
    """Test the to_bool function."""
    assert transforms.to_bool(test_case.value) == test_case.expected_out


# sourcery skip: simplify-generator
class ToListTestCase(TestCase):
    """Test case for the to_list function."""

    string: Any
    lowercase: bool = False
    expected_out: list[str] = []  # noqa: RUF012
    expect_error: bool = False


TO_LIST_TEST_CASES = [
    ToListTestCase(
        id="empty",
        string="",
        expected_out=[],
    ),
    ToListTestCase(
        id="list",
        string=["a", "b", "c"],
        expected_out=["a", "b", "c"],
    ),
    ToListTestCase(
        id="tuple",
        string=("a", "b", "c"),
        expected_out=["a", "b", "c"],
    ),
    ToListTestCase(
        id="set",
        string={"a", "b", "c"},
        expected_out=["a", "b", "c"],
    ),
    ToListTestCase(
        id="generator",
        string=(i for i in ["a", "b", "c"]),
        expected_out=["a", "b", "c"],
    ),
    ToListTestCase(
        id="str",
        string="A, B, C",
        expected_out=["A", "B", "C"],
    ),
    ToListTestCase(
        id="str_lower",
        string="A, B, C",
        lowercase=True,
        expected_out=["a", "b", "c"],
    ),
    ToListTestCase(
        id="str_quotes",
        string='"a", "b", "c"',
        expected_out=["a", "b", "c"],
    ),
    ToListTestCase(
        id="str_space_outer",
        string="\n  a  , b  , c  \n",
        expected_out=["a", "b", "c"],
    ),
    ToListTestCase(
        id="str_parentheses",
        string="(a, b, c)",
        expected_out=["a", "b", "c"],
    ),
    ToListTestCase(
        id="str_brackets",
        string="[a, b, c]",
        expected_out=["a", "b", "c"],
    ),
    ToListTestCase(
        id="str_empty",
        string="[]",
        expected_out=[],
    ),
    ToListTestCase(
        id="str_just_space",
        string="  ",
        expected_out=[],
    ),
    ToListTestCase(
        id="str_none",
        string=None,
        expected_out=[],
    ),
    ToListTestCase(
        id="str_other",
        string=1,
        expect_error=True,
    ),
]


@ToListTestCase.parametrize(TO_LIST_TEST_CASES)
def test_to_list(test_case: ToListTestCase) -> None:
    """Test the to_list function."""
    if test_case.expect_error:
        with pytest.raises(TypeError):
            transforms.to_list(test_case.string, lowercase=test_case.lowercase)
        return
    out = transforms.to_list(test_case.string, lowercase=test_case.lowercase)
    assert sorted(out) == sorted(test_case.expected_out)
