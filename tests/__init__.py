from collections.abc import Sequence
from pathlib import Path

import pytest
from pydantic import BaseModel

TEST_ROOT_PATH = Path(__file__).parent
TEST_DATA_PATH = TEST_ROOT_PATH / "data"
TEST_MEDIA_DATA_PATH = TEST_DATA_PATH / "media"
TEST_EXAMPLE_BLOGS_PATH = TEST_DATA_PATH / "example_blog_posts"


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
