"""test_blog_create: Test cases for creating blog posts."""

import re

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests.functional_tests import BASE_URL

ENDPOINT = "/blog/create"


@pytest.fixture(autouse=True)
async def _clean_db_fixture(clean_db_module: None, anyio_backend: str) -> None:  # noqa: ARG001 (unused-arg)
    """Clean the database after each test."""


# ---------------------------------- GET -------------------------------------
def test_get_create_blog_post_page_as_guest_redirects_to_sign_in(test_client: TestClient):
    """Test that a guest is redirected to the sign in page."""
    response = test_client.get(ENDPOINT, follow_redirects=False)
    assert response.status_code == status.HTTP_303_SEE_OTHER
    response = test_client.get(ENDPOINT)
    assert "Sign In</h1>" in response.text


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_get_create_blog_post_as_basic_user_fails(test_client: TestClient):
    """Test that a basic user cannot access the create blog post page."""
    response = test_client.get(ENDPOINT)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "403 Error" in response.text
    assert "You do not have permission to perform this action" in response.text


@pytest.mark.usefixtures("logged_in_admin_user_module")
def test_get_create_blog_post_as_admin_succeeds(test_client: TestClient):
    """Test that an admin user can access the create blog post page."""
    response = test_client.get(ENDPOINT)
    assert response.status_code == status.HTTP_200_OK
    assert "Create Blog Post" in response.text


# ---------------------------------- POST ------------------------------------
@pytest.mark.usefixtures("logged_in_admin_user_module", "clean_db_except_users")
def test_post_create_blog_post_succeeds(test_client: TestClient):
    """Test that an admin user can create a blog post."""
    title = "Test Title"
    description = "Test Description"
    content = "Test Content"
    tags = ["tag1", "tag2"]
    data = {
        "is_new": "true",
        "title": title,
        "tags": ", ".join(tags),
        "can_comment": "true",
        "is_published": "true",
        "description": description,
        "content": content,
    }
    response = test_client.post(ENDPOINT, data=data)
    assert response.status_code == status.HTTP_200_OK
    assert re.match(rf"{BASE_URL}/blog/\d+/edit", str(response.url))
    expected_strings = (
        title,
        description,
        content,
        *tags,
    )
    for string in expected_strings:
        assert string in response.text


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

[internal link](#foo)

![image](https://example.com/image.jpg)

```python
print("code block")
```

> blockquote

<picture><img src="http://foo/mypic.png" alt="Pre commit logo" title="Pre commit logo" width="500" height="500"></picture>
picture caption

<div class="flex justify-center content-center"><video muted="" autoplay="" loop="" controls="" playsinline="" poster="http://foo/video-poster.svg" width="1854" height="1080"><source src="http://foo/vid.mp4" type="video/mp4">Your browser does not support the video tag.</video></div>

<video><source data-src="http://foo/vid.mp4" type="video/mp4"></video>
"""

ADVANCED_CONTENT_HTML = """\
<article id="blog-article"><h1 id="header-1" x-intersect="highlightTocElement('header-1')">Header 1</h1>
<h2 id="header-2" x-intersect="highlightTocElement('header-2')">Header 2</h2>
<h3 id="header-3" x-intersect="highlightTocElement('header-3')">Header 3</h3>
<h4 id="header-4" x-intersect="highlightTocElement('header-4')">Header 4</h4>
<h5 id="header-5" x-intersect="highlightTocElement('header-5')">Header 5</h5>
<h6 id="header-6" x-intersect="highlightTocElement('header-6')">Header 6</h6>
<h2 id="blog-123-header-starts-with-numbers" x-intersect="highlightTocElement('blog-123-header-starts-with-numbers')">123 Header starts with numbers</h2>
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
<p><a href="#foo">internal link</a></p>
<p class="text-center"><img alt="image" class="rounded-lg mx-auto" loading="lazy" src="https://example.com/image.jpg"/></p>
<div class="highlight not-prose"><pre tabindex="0"><span></span><code><span class="nb">print</span><span class="p">(</span><span class="s2">"code block"</span><span class="p">)</span>
</code></pre></div>
<blockquote>
<p>blockquote</p>
</blockquote>
<p class="text-center"><picture><img alt="Pre commit logo" class="rounded-lg mx-auto" height="500" loading="lazy" src="http://foo/mypic.png" title="Pre commit logo" width="500"/></picture>
picture caption</p>
<div class="flex justify-center content-center"><video autoplay="" class="lazy" controls="" height="1080" loop="" muted="" playsinline="" poster="http://foo/video-poster.svg" width="1854"><source data-src="http://foo/vid.mp4" type="video/mp4"/>Your browser does not support the video tag.</video></div>
<video class="lazy"><source data-src="http://foo/vid.mp4" type="video/mp4"/></video></article>"""

ADVANCED_CONTENT_TOC_NAV = """\
<nav class="not-prose" id="toc">
<ul class="flex flex-col gap-4"><li class="flex flex-col gap-4"><a @click="tocOpen = false; allowTocClose = false;" class="link px-2 py-1 rounded-lg" href="#">Title</a></li>
<li class="flex flex-col gap-4"><a @click="tocOpen = false; allowTocClose = false;" class="link px-2 py-1 rounded-lg" href="#header-1">Header 1</a><ul class="flex flex-col gap-4 ml-6">
<li class="flex flex-col gap-4"><a @click="tocOpen = false; allowTocClose = false;" class="link px-2 py-1 rounded-lg" href="#header-2">Header 2</a><ul class="flex flex-col gap-4 ml-6">
<li class="flex flex-col gap-4"><a @click="tocOpen = false; allowTocClose = false;" class="link px-2 py-1 rounded-lg" href="#header-3">Header 3</a></li>
</ul>
</li>
<li class="flex flex-col gap-4"><a @click="tocOpen = false; allowTocClose = false;" class="link px-2 py-1 rounded-lg" href="#blog-123-header-starts-with-numbers">123 Header starts with numbers</a></li>
</ul>
</li>
<li class="flex flex-col gap-4"><a @click="tocOpen = false; allowTocClose = false;" class="link px-2 py-1 rounded-lg" href="#about-the-author">About the author</a></li><li class="flex flex-col gap-4"><a @click="tocOpen = false; allowTocClose = false;" class="link px-2 py-1 rounded-lg" href="#comments">Comments</a></li></ul>
</nav>"""


@pytest.mark.usefixtures("logged_in_admin_user_module", "clean_db_except_users")
def test_post_create_blog_post_advanced_md_content_succeeds(test_client: TestClient):
    """Test that an admin user can create a blog post."""
    title = "Test Title"
    description = "Test Description"
    tags = ["tag1", "tag2"]
    data = {
        "is_new": "true",
        "title": title,
        "tags": ", ".join(tags),
        "can_comment": "true",
        "is_published": "true",
        "description": description,
        "content": ADVANCED_CONTENT_MD,
    }
    response = test_client.post(ENDPOINT, data=data)
    assert response.status_code == status.HTTP_200_OK
    assert re.match(rf"{BASE_URL}/blog/\d+/edit", str(response.url))

    expected_strings = (
        title,
        description,
        ADVANCED_CONTENT_HTML,
        ADVANCED_CONTENT_TOC_NAV,
        *tags,
    )
    for string in expected_strings:
        assert string in response.text


@pytest.mark.usefixtures("logged_in_admin_user_module", "clean_db_except_users")
def test_post_create_blog_post_with_form_errors_fails(test_client: TestClient):
    """Test that an admin user cannot create a blog post with form errors."""
    data = {
        "is_new": "true",
        "title": "",
        "can_comment": "true",
        "is_published": "true",
        "description": "",
        "content": "some content",
    }
    response = test_client.post(ENDPOINT, data=data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    expected_strings = (
        "Create New Blog Post",
        "Field must be at least 1 character long.",
        "some content",
    )
    for string in expected_strings:
        assert string in response.text


@pytest.mark.usefixtures("logged_in_admin_user_module", "clean_db_except_users")
def test_post_create_blog_post_with_duplicate_post_title_fails(test_client: TestClient):
    """Test that an admin user cannot create a blog post with a duplicate title."""
    title = "Test Title"
    description = "Test Description"
    content = "Test Content"
    data = {
        "is_new": "true",
        "title": title,
        "can_comment": "true",
        "is_published": "true",
        "description": description,
        "content": content,
    }
    response = test_client.post(ENDPOINT, data=data)
    assert response.status_code == status.HTTP_200_OK
    assert re.match(rf"{BASE_URL}/blog/\d+/edit", str(response.url))
    expected_strings: tuple[str, ...] = (
        title,
        description,
        content,
    )
    for string in expected_strings:
        assert string in response.text

    response = test_client.post(ENDPOINT, data=data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    expected_strings = (
        "Create New Blog Post",
        "Error saving blog post",
        title,
        description,
        content,
    )
    for string in expected_strings:
        assert string in response.text
