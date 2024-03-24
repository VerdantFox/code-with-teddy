from collections.abc import Sequence

import pytest
from pydantic import BaseModel


class TestCase(BaseModel, arbitrary_types_allowed=True):
    """TestCase baseclass for parametrized tests."""

    id: str
    marks: Sequence[pytest.MarkDecorator] = ()

    @staticmethod
    def parametrize(
        test_cases: Sequence["TestCase"], *, arg_name: str = "test_case"
    ) -> pytest.MarkDecorator:
        """Parametrize the test cases."""
        return pytest.mark.parametrize(
            arg_name, [pytest.param(case, id=case.id, marks=case.marks) for case in test_cases]
        )
