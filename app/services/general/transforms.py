"""transforms: functions for transforming data from one type to another."""

from collections.abc import Generator
from typing import Annotated, Any

from pydantic import BeforeValidator, ValidationInfo


def to_bool(value: Any) -> bool:
    # sourcery skip: assign-if-exp, reintroduce-else
    """Convert a value to a boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.casefold() in ("true", "t", "yes", "y", "1")
    if isinstance(value, int):
        return value == 1
    return False


def too_bool_validator(v: Any, _: ValidationInfo) -> bool:
    """Cooerce any value to a bool."""
    return to_bool(v)


CoercedBool = Annotated[bool, BeforeValidator(too_bool_validator)]


def to_list(string: Any, *, lowercase: bool = False) -> list[str]:
    """Convert a list-like string to a list.

    Also, convert iterables to lists.
    Lowercase list items.
    """
    if not string:
        return []
    if isinstance(string, list | tuple | set | Generator):
        return list(string)
    string_list = string.strip(" []()").split(",")
    if lowercase:
        return [item.strip().strip("\"'").casefold() for item in string_list]
    return [item.strip().strip("\"'") for item in string_list]


def to_list_validator(v: Any, _: ValidationInfo) -> list[str]:
    """Coerce an iterable or a list-like str into a list."""
    return to_list(v, lowercase=True)


CoercedList = Annotated[list[str], BeforeValidator(to_list_validator)]
