"""test_comment_non_mutating: Test non-mutating comment functionality."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.datastore import db_models
from tests import TestCase

PREVIEW = "&mdash;(preview)"


@pytest.fixture(autouse=True)
async def _clean_db_fixture(clean_db_module: None, anyio_backend: str) -> None:  # noqa: ARG001 (unused-arg)
    """Clean the database after the module completes."""


def test_get_comment(
    test_client: TestClient,
    advanced_blog_post_with_user_module: db_models.BlogPost,
):
    """Test that a user can view comments on a blog post."""
    comment = advanced_blog_post_with_user_module.comments[0]
    response = test_client.get(f"/blog/comment/{comment.id}")
    assert response.status_code == status.HTTP_200_OK
    assert comment.name
    assert comment.name in response.text
    assert comment.html_content in response.text


def test_get_comment_not_found(test_client: TestClient):
    """Test that a user receives a 404 error when a comment is not found."""
    response = test_client.get("/blog/comment/999999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "404 Error" in response.text
    assert "Blog post comment not found" in response.text


def test_get_comment_edit_as_guest_not_owned(
    test_client: TestClient, advanced_blog_post_with_user_module: db_models.BlogPost
):
    """Test that a guest cannot edit a comment that they do not own."""
    comment = advanced_blog_post_with_user_module.comments[0]
    response = test_client.get(f"/blog/comment/{comment.id}/edit")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "You can&#39;t edit this comment." in response.text


def test_get_comment_edit_as_user_owned(
    test_client: TestClient,
    logged_in_basic_user_module: db_models.User,
    advanced_blog_post_with_user_module: db_models.BlogPost,
):
    """Test that a user can edit a comment that they own."""
    comment = advanced_blog_post_with_user_module.comments[1]
    response = test_client.get(f"/blog/comment/{comment.id}/edit")
    assert response.status_code == status.HTTP_200_OK
    assert PREVIEW in response.text
    assert comment.html_content in response.text
    assert logged_in_basic_user_module.full_name in response.text


@pytest.mark.usefixtures("logged_in_basic_user_2_module")
def test_get_comment_edit_as_user_not_owned(
    test_client: TestClient,
    advanced_blog_post_with_user_module: db_models.BlogPost,
):
    """Test that a user can edit a comment that they own."""
    comment = advanced_blog_post_with_user_module.comments[1]
    response = test_client.get(f"/blog/comment/{comment.id}/edit")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "You can&#39;t edit this comment." in response.text


@pytest.mark.usefixtures("logged_in_admin_user_module")
def test_get_comment_edit_as_admin_not_owned(
    test_client: TestClient,
    advanced_blog_post_with_user_module: db_models.BlogPost,
):
    """Test that a user can edit a comment that they own.

    Comment editing other's posts is not allowed even for admins.
    """
    comment = advanced_blog_post_with_user_module.comments[1]
    response = test_client.get(f"/blog/comment/{comment.id}/edit")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "You can&#39;t edit this comment." in response.text


class GuestCommentPreviewTestCase(TestCase):
    """Test case for previewing a comment as a guest."""

    # RUF012: Mutable class strings should have typing.ClassVar
    # But these are from pydantic.BaseModel, so they are allowed to be mutable
    bp_id: int | str | None = None
    data: dict[str, str] = {}  # noqa: RUF012
    expected_status_code: int = status.HTTP_200_OK
    expected_strings: list[str] = []  # noqa: RUF012
    is_blank: bool = False


# Fields
CHECK_ME = "check_me"
NOT_ROBOT = "not_robot"
NAME = "name"
EMAIL = "email"
CONTENT = "content"

# Field values
PERRIN = "Perrin Aybara"
PERRIN_EMAIL = "perrin@email.com"
BASIC_CONTENT_MD = "some content"
BASIC_CONTENT_HTML = "<p>some content</p>"
BLANK = ""
TRUE = "true"

ADVANCED_CONTENT_MD = """\
# Header 1
## Header 2
### Header 3
#### Header 4
##### Header 5
###### Header 6

## 123 Header starts with numbers

A paragraph.

- list item 1
- list item 2

1. numbered item 1
2. numbered item 2

**bold text**
*italic text*
***bold italic text***
`code`
~~strikethrough~~

[link](https://example.com)

![image](https://example.com/image.jpg)

```python
print("code block")
```

```html
<p>HTML in code block should look correct</p>
```

> blockquote

<script>HTML should get bleached</script>
"""
ADVANCED_CONTENT_HTML = """\
<h3>Header 1</h3>
<h4>Header 2</h4>
<h5>Header 3</h5>
<h6>Header 4</h6>
<h6>Header 5</h6>
<h6>Header 6</h6>
<h4>123 Header starts with numbers</h4>
<p>A paragraph.</p>
<ul>
<li>list item 1</li>
<li>list item 2</li>
</ul>
<ol>
<li>numbered item 1</li>
<li>numbered item 2</li>
</ol>
<p><strong>bold text</strong>
<em>italic text</em>
<strong><em>bold italic text</em></strong>
<code>code</code>
<del>strikethrough</del></p>
<p><a href="https://example.com" rel="noopener noreferrer" target="_blank">link</a></p>
<p class="text-center"><img alt="image" class="rounded-lg mx-auto" loading="lazy" src="https://example.com/image.jpg"></p>
<div class="highlight not-prose"><pre tabindex="0"><span></span><code><span class="nb">print</span><span class="p">(</span><span class="s2">"code block"</span><span class="p">)</span>
</code></pre></div>
<div class="highlight not-prose"><pre tabindex="0"><span></span><code><span class="p">&lt;</span><span class="nt">p</span><span class="p">&gt;</span>HTML in code block should look correct<span class="p">&lt;/</span><span class="nt">p</span><span class="p">&gt;</span>
</code></pre></div>
<blockquote>
<p>blockquote</p>
</blockquote>
<p>&lt;script&gt;HTML should get bleached&lt;/script&gt;</p>"""

NEFARIOUS_MD = """\
```html
<p>foo</p>
```

<script>foobar</script>

___CODEBLOCKfoo___


___BLOCKQUOTE___
"""
NEFARIOUS_HTML = """\
<div class="highlight not-prose"><pre tabindex="0"><span></span><code><span class="ni">&amp;lt;</span>p<span class="ni">&amp;gt;</span>foo<span class="ni">&amp;lt;</span>/p<span class="ni">&amp;gt;</span>
</code></pre></div>
<p>&lt;script&gt;foobar&lt;/script&gt;</p>
<p><strong><em>CODEBLOCKfoo</em></strong></p>
<p><strong><em>BLOCKQUOTE</em></strong></p>
"""


GUEST_COMMENT_PREVIEW_TEST_CASES = [
    GuestCommentPreviewTestCase(
        id="basic_with_email",
        data={
            CHECK_ME: BLANK,
            NOT_ROBOT: TRUE,
            NAME: PERRIN,
            EMAIL: PERRIN_EMAIL,
            CONTENT: BASIC_CONTENT_MD,
        },
        expected_strings=[PREVIEW, PERRIN, BASIC_CONTENT_HTML],
    ),
    GuestCommentPreviewTestCase(
        id="basic_with_bad_email",
        data={
            CHECK_ME: BLANK,
            NOT_ROBOT: TRUE,
            NAME: PERRIN,
            EMAIL: "not-an-email",  # Should succeed still
            CONTENT: BASIC_CONTENT_MD,
        },
        expected_strings=[PREVIEW, PERRIN, BASIC_CONTENT_HTML],
    ),
    GuestCommentPreviewTestCase(
        id="basic_no_email",
        data={
            CHECK_ME: BLANK,
            NOT_ROBOT: TRUE,
            NAME: PERRIN,
            EMAIL: BLANK,
            CONTENT: BASIC_CONTENT_MD,
        },
        expected_strings=[PREVIEW, PERRIN, BASIC_CONTENT_HTML],
    ),
    GuestCommentPreviewTestCase(
        id="fail_checks",  # This succeeds for the preview
        data={
            CHECK_ME: TRUE,
            NOT_ROBOT: BLANK,
            NAME: PERRIN,
            EMAIL: PERRIN_EMAIL,
            CONTENT: BASIC_CONTENT_MD,
        },
        expected_strings=[PREVIEW, PERRIN, BASIC_CONTENT_HTML],
    ),
    GuestCommentPreviewTestCase(
        id="no_name",
        data={
            CHECK_ME: BLANK,
            NOT_ROBOT: TRUE,
            NAME: BLANK,
            EMAIL: PERRIN_EMAIL,
            CONTENT: BASIC_CONTENT_MD,
        },
        expected_strings=[PREVIEW, BASIC_CONTENT_HTML],
    ),
    GuestCommentPreviewTestCase(
        id="no_content",
        data={
            CHECK_ME: BLANK,
            NOT_ROBOT: TRUE,
            NAME: PERRIN,
            EMAIL: PERRIN_EMAIL,
            CONTENT: BLANK,
        },
        is_blank=True,
    ),
    GuestCommentPreviewTestCase(
        id="advanced",
        data={
            CHECK_ME: BLANK,
            NOT_ROBOT: TRUE,
            NAME: PERRIN,
            EMAIL: PERRIN_EMAIL,
            CONTENT: ADVANCED_CONTENT_MD,
        },
        expected_strings=[PREVIEW, PERRIN, ADVANCED_CONTENT_HTML],
    ),
    GuestCommentPreviewTestCase(
        id="bad_bp_id",
        bp_id="foo",
        data={
            CHECK_ME: BLANK,
            NOT_ROBOT: TRUE,
            NAME: BLANK,
            EMAIL: PERRIN_EMAIL,
            CONTENT: BASIC_CONTENT_MD,
        },
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        expected_strings=["Something went wrong with the form submission."],
    ),
    GuestCommentPreviewTestCase(
        id="nefarious",
        data={
            CHECK_ME: BLANK,
            NOT_ROBOT: TRUE,
            NAME: PERRIN,
            EMAIL: PERRIN_EMAIL,
            CONTENT: NEFARIOUS_MD,
        },
        expected_strings=[PREVIEW, PERRIN, NEFARIOUS_HTML],
    ),
]


@GuestCommentPreviewTestCase.parametrize(GUEST_COMMENT_PREVIEW_TEST_CASES)
def test_comment_post_preview_as_guest(
    test_client: TestClient,
    advanced_blog_post_with_user_module: db_models.BlogPost,
    test_case: GuestCommentPreviewTestCase,
):
    """Test a comment post preview succeeding."""
    bp = advanced_blog_post_with_user_module
    bp_id = test_case.bp_id or bp.id

    response = test_client.post(f"/blog/{bp_id}/comment-preview", data=test_case.data)
    assert response.status_code == test_case.expected_status_code
    if test_case.is_blank:
        assert response.text == ""
        return
    for string in test_case.expected_strings:
        assert string in response.text


def test_comment_post_preview_as_logged_in_user(
    test_client: TestClient,
    logged_in_basic_user_module: db_models.User,
    advanced_blog_post_with_user_module: db_models.BlogPost,
):
    """Test a comment post preview succeeding."""
    bp = advanced_blog_post_with_user_module
    data = {
        CHECK_ME: BLANK,
        NOT_ROBOT: TRUE,
        NAME: logged_in_basic_user_module.full_name,
        EMAIL: logged_in_basic_user_module.email,
        CONTENT: BASIC_CONTENT_MD,
    }
    response = test_client.post(f"/blog/{bp.id}/comment-preview", data=data)
    assert response.status_code == status.HTTP_200_OK
    assert PREVIEW in response.text
    assert logged_in_basic_user_module.full_name in response.text
    assert BASIC_CONTENT_HTML in response.text
