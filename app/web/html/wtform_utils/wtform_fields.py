"""wtforms_fixes: Updated WTForm fields to handle better input transformation."""

from typing import Any

from wtforms import BooleanField as WTFBoolField

from app.services.general import transforms


class BooleanField(WTFBoolField):
    """BooleanField with better input transformation."""

    def process_data(self, value: Any) -> None:
        """Process a value for this field."""
        self.data = transforms.to_bool(value)
