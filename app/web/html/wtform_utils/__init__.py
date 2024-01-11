"""__init__: wtform_utils."""
from typing import Any, Self

from fastapi.datastructures import FormData
from werkzeug.datastructures import MultiDict
from wtforms import Form as WTForm


class Form(WTForm):
    """Form with better input transformation."""

    @classmethod
    def load(cls, data: dict[str, Any] | FormData) -> Self:
        """Load data into form."""
        return cls(formdata=MultiDict(dict(data)))
