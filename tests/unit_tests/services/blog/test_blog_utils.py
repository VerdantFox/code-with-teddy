"""tst_blog_utils: unit tests for blog_utils service."""

import pytest

from app.services.blog import blog_utils
from tests import TEST_EXAMPLE_BLOGS_PATH, TestCase

PYTEST_TIPS_BP_PATH = TEST_EXAMPLE_BLOGS_PATH / "pytest_tips_and_tricks.md"
PYTEST_TIPS_BP_MD = PYTEST_TIPS_BP_PATH.read_text()


class TestGetSlug(TestCase):
    """Test case for the get_slug function."""

    title: str
    expected_out: str


GET_SLUG_TEST_CASES = [
    TestGetSlug(id="no_special_chars", title="test title", expected_out="test-title"),
    TestGetSlug(id="lowercase", title="Test Title", expected_out="test-title"),
    TestGetSlug(
        id="multiple_spaces", title="This    is   a Test Title", expected_out="this-is-a-test-title"
    ),
    TestGetSlug(
        id="special_chars", title="test!@#$%^&*()+=`~<>/:;., title", expected_out="test-title"
    ),
    TestGetSlug(id="empty", title="", expected_out=""),
    TestGetSlug(id="space", title=" ", expected_out=""),
    TestGetSlug(id="other", title="other", expected_out="other"),
]


@TestGetSlug.parametrize(GET_SLUG_TEST_CASES)
def test_get_slug(test_case: TestGetSlug) -> None:
    """Test get_slug function."""
    assert blog_utils.get_slug(test_case.title) == test_case.expected_out


class TestCalcReadMins(TestCase):
    """Test case for the calc_read_mins function."""

    content: str
    image_count: int
    expected_out: int


CALC_READ_MINS_TEST_CASES = [
    TestCalcReadMins(
        id="no_images",
        content="This is a test article.",
        image_count=0,
        expected_out=1,
    ),
    TestCalcReadMins(
        id="longer_post_with_images",
        content=PYTEST_TIPS_BP_MD,
        image_count=4,
        expected_out=34,
    ),
]


@TestCalcReadMins.parametrize(CALC_READ_MINS_TEST_CASES)
def test_calc_read_mins(test_case: TestCalcReadMins) -> None:
    """Test calc_read_mins function."""
    assert (
        blog_utils.calc_read_mins(test_case.content, test_case.image_count)
        == test_case.expected_out
    )


EXAMPLE_MD = """\
# This is an h1 header

### This is an h3 header

This is a paragraph with a [link](https://example.com).

![This is an image](https://example.com/image.jpg).

<picture>
  <source media="(min-width: 650px)" srcset="img_pink_flowers.jpg">
  <source media="(min-width: 465px)" srcset="img_white_flower.jpg">
  <img src="img_orange_flowers.jpg" alt="Flowers" style="width:auto;">
</picture>

This is a paragraph with a class{: .class } here.

This is a paragraph with a random "#" here.
"""
EXPECTED_MD = (
    "This is an h1 header. This is an h3 header."
    " This is a paragraph with a link. This is an image."
    " This is a paragraph with a class here."
    ' This is a paragraph with a random "#" here.'
)


def test_strip_markdown() -> None:
    """Test strip_markdown function."""
    assert blog_utils.strip_markdown(EXAMPLE_MD) == EXPECTED_MD


EXPECTED_INTRODUCTION = """\
<picture><img alt="Pytest logo" class="rounded-lg" loading="lazy" src="http://localhost:8000/static/media/local/blog/pytest-logo.png" title="Pytest logo" width="600" height="278"></picture>

Are you a python developer looking to improve your testing abilities with
pytest? Me too! So I've put together a list of 9 tips and tricks I've
found most useful in getting my tests looking sharp. Here are the features
we're going to be covering today:

1. Useful command-line arguments
2. `skip` and `xfail`
3. Mocking with `monkeypatch`
4. `tmp_path` and `importlib`
5. `fixture`s and the `conftest.py` file
6. Testing python exceptions
7. Checking stdout and log messages
8. Parameterizing tests
9. Using pytest-cov

All of the code discussed in this article can be found in the following
[GitHub repository](https://github.com/VerdantFox/pytest_examples){: target="_blank", rel="noopener noreferrer" }
I created. To run the code, you'll need `pytest` and `pytest-cov`, which you
can install with `pip install pytest` and `pip install pytest-cov`.
I recommend doing so in a virtual environment.
"""


def test_get_bp_introduction() -> None:
    """Test get_bp_introduction function."""
    assert blog_utils.get_bp_introduction(PYTEST_TIPS_BP_MD) == EXPECTED_INTRODUCTION


def test_get_bp_introduction_empty() -> None:
    """Test get_bp_introduction function with empty content."""
    with pytest.raises(ValueError, match="No introduction found in the blog post content."):
        blog_utils.get_bp_introduction("")


def test_get_bp_tags() -> None:
    """Test get_bp_tags function."""
    assert blog_utils.get_bp_tags(PYTEST_TIPS_BP_MD) == ["testing", "pytest", "python"]


def test_get_bp_tags_empty() -> None:
    """Test get_bp_tags function with empty content."""
    with pytest.raises(ValueError, match="No tags found in the blog post content."):
        blog_utils.get_bp_tags("")


def test_get_bp_thumbnail() -> None:
    """Test get_bp_thumbnail function."""
    thumbnail = blog_utils.get_bp_thumbnail(PYTEST_TIPS_BP_MD)
    assert thumbnail == "http://localhost:8000/static/media/local/blog/pytest-logo.png"


def test_get_bp_thumbnail_empty() -> None:
    """Test get_bp_thumbnail function with empty content."""
    assert blog_utils.get_bp_thumbnail("") is None


def test_get_bp_title() -> None:
    """Test get_bp_title function."""
    title = blog_utils.get_bp_title(PYTEST_TIPS_BP_MD)
    assert title == "9 pytest tips and tricks to take your tests to the next level"


def test_get_bp_title_empty() -> None:
    """Test get_bp_title function with empty content."""
    with pytest.raises(ValueError, match="No title found in the blog post content."):
        blog_utils.get_bp_title("")


def test_get_bp_content() -> None:
    """Test get_bp_content function."""
    content = blog_utils.get_bp_content(PYTEST_TIPS_BP_MD)
    assert "## Conclusions" in content


def test_get_bp_content_empty() -> None:
    """Test get_bp_content function with empty content."""
    with pytest.raises(ValueError, match="No content found in the blog post content."):
        blog_utils.get_bp_content("")
