"""custom_validators: Custom validators for WTForms."""
import re
from collections.abc import Callable
from typing import Any

from starlette.datastructures import UploadFile as StarletteUploadFile
from wtforms import (
    Form,
    FormField,
    ValidationError,
)


def is_allowed_extension(extensions: list[str], error_msg: str = "") -> Callable:
    """Check if the extension is allowed.

    Defaults to image extensions.
    """
    extensions_regex = re.compile(r"\.(" + "|".join(extensions) + ")$", re.IGNORECASE)

    def _is_allowed_extension(_form: Form, field: FormField) -> None:
        """Check if the file is of an allowed extension."""
        filename = (
            field.data.filename if isinstance(field.data, StarletteUploadFile) else field.data
        )
        if not filename:
            return
        if not extensions_regex.search(filename):
            msg = error_msg or f"Invalid file extension. Allowed: {', '.join(extensions)}."
            raise ValidationError(msg)

    return _is_allowed_extension


def is_value(value: Any, error_msg: str = "") -> Callable:
    """Check if the value is the given value."""

    def _is_value(_form: Form, field: FormField) -> None:
        """Check if the value is the given value."""
        if field.data != value:
            msg = error_msg or f"Invalid value. Must be {value}."
            raise ValidationError(msg)

    return _is_value
