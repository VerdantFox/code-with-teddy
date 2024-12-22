"""test_blog_media: test the blog media endpoints."""

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from app.datastore import db_models
from app.services.media import media_handler
from scripts.start_local_postgres import DBBuilder
from tests import TEST_MEDIA_DATA_PATH, TestCase
from tests.conftest import delete_all_data


@pytest.fixture(autouse=True)
async def _clean_db_fixture_module(clean_db_module: None, anyio_backend: str) -> None:
    """Clean the database after the module."""


@pytest.fixture(name="clean_db_except_users_or_bps")
async def _clean_db_except_users_or_bps(
    db_session: AsyncSession, db_builder: DBBuilder
) -> AsyncGenerator[None, None]:
    """Delete all data from the database except users after the function."""
    yield
    await delete_all_data(db_session, db_builder, skip_tables={"users", "blog_posts"})


def test_upload_media_as_guest_fails(
    test_client: TestClient, basic_blog_post_module: db_models.BlogPost
):
    """Test that a guest cannot upload media."""
    bp = basic_blog_post_module
    response = test_client.post(f"/blog/{bp.id}/media", data={})
    assert response.status_code == status.HTTP_200_OK
    assert "Sign In</h1>" in response.text


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_upload_media_as_basic_user_fails(
    test_client: TestClient, basic_blog_post_module: db_models.BlogPost
):
    """Test that a basic user cannot upload media."""
    bp = basic_blog_post_module
    response = test_client.post(f"/blog/{bp.id}/media", data={})

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "403 Error" in response.text
    assert "You do not have permission to perform this action" in response.text


class MediaUploadTestCase(TestCase):
    """Test case for editing a blog post."""

    # RUF012: Mutable class strings should have typing.ClassVar
    # But these are from pydantic.BaseModel, so they are allowed to be mutable
    bp_id: int | str | None = None
    data: dict[str, str] = {}  # noqa: RUF012
    files: Any
    expected_status_code: int = status.HTTP_200_OK
    expected_strings: list[str] = []  # noqa: RUF012


# Good images
PNG_FILE = TEST_MEDIA_DATA_PATH / "test.png"
JPG_FILE = TEST_MEDIA_DATA_PATH / "test.jpg"
SVG_FILE = TEST_MEDIA_DATA_PATH / "test.svg"
WEBP_FILE = TEST_MEDIA_DATA_PATH / "test.webp"
GIF_FILE = TEST_MEDIA_DATA_PATH / "test.gif"

# Bad image
BMP_FILE = TEST_MEDIA_DATA_PATH / "test.bmp"

# Good videos
MP4_FILE = TEST_MEDIA_DATA_PATH / "test.mp4"
WEBM_FILE = TEST_MEDIA_DATA_PATH / "test.webm"


MEDIA_UPLOAD_TEST_CASES = [
    MediaUploadTestCase(
        id="png",
        data={"name": "PNG media"},
        files={"media": (PNG_FILE.name, PNG_FILE.read_bytes())},
        expected_strings=["PNG media"],
    ),
    MediaUploadTestCase(
        id="jpg",
        data={"name": "JPG media"},
        files={"media": (JPG_FILE.name, JPG_FILE.read_bytes())},
        expected_strings=["JPG media"],
    ),
    MediaUploadTestCase(
        id="svg",
        data={"name": "SVG media"},
        files={"media": (SVG_FILE.name, SVG_FILE.read_bytes())},
        expected_strings=["SVG media"],
    ),
    MediaUploadTestCase(
        id="webp",
        data={"name": "WEBP media"},
        files={"media": (WEBP_FILE.name, WEBP_FILE.read_bytes())},
        expected_strings=["WEBP media"],
    ),
    MediaUploadTestCase(
        id="gif",
        data={"name": "GIF media"},
        files={"media": (GIF_FILE.name, GIF_FILE.read_bytes())},
        expected_strings=["GIF media"],
    ),
    MediaUploadTestCase(
        id="mp4",
        data={"name": "MP4 media"},
        files={"media": (MP4_FILE.name, MP4_FILE.read_bytes())},
        expected_strings=["MP4 media"],
    ),
    MediaUploadTestCase(
        id="webm",
        data={"name": "WEBM media"},
        files={"media": (WEBM_FILE.name, WEBM_FILE.read_bytes())},
        expected_strings=["WEBM media"],
    ),
    MediaUploadTestCase(
        id="bad_image",
        data={"name": "BMP media"},
        files={"media": (BMP_FILE.name, BMP_FILE.read_bytes())},
        expected_strings=["BMP media"],
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    ),
    MediaUploadTestCase(
        id="no_name",
        data={},
        files={"media": (PNG_FILE.name, PNG_FILE.read_bytes())},
        expected_strings=["This field is required"],
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    ),
    MediaUploadTestCase(
        id="no_media",
        data={"name": "PNG media"},
        files={},
        expected_strings=["This field is required"],
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    ),
    MediaUploadTestCase(
        id="bp_not_found",
        bp_id=999,
        data={"name": "PNG media"},
        files={"media": (PNG_FILE.name, PNG_FILE.read_bytes())},
        expected_status_code=status.HTTP_404_NOT_FOUND,
        expected_strings=["Blog post not found"],
    ),
]


@pytest.mark.usefixtures("logged_in_admin_user_module", "clean_db_except_users_or_bps")
@MediaUploadTestCase.parametrize(MEDIA_UPLOAD_TEST_CASES)
def test_upload_media_as_admin_user(
    test_client: TestClient,
    basic_blog_post_module: db_models.BlogPost,
    test_case: MediaUploadTestCase,
    mocker: MockerFixture,
    tmp_path: Path,
):
    """Test that an admin user can upload media."""
    _mock_blog_upload_folder(tmp_path=tmp_path, mocker=mocker)

    bp = basic_blog_post_module
    bp_id = test_case.bp_id or bp.id
    response = test_client.post(f"/blog/{bp_id}/media", data=test_case.data, files=test_case.files)
    assert response.status_code == test_case.expected_status_code
    for string in test_case.expected_strings:
        assert string in response.text


def _mock_blog_upload_folder(tmp_path: Path, mocker: MockerFixture) -> Path:
    """Mock the blog upload folder."""
    tmp_blog_upload_folder_path = tmp_path / "static" / "media" / "blog"
    tmp_blog_upload_folder_path.mkdir(parents=True, exist_ok=True)
    mocker.patch.object(media_handler, "BLOG_UPLOAD_FOLDER", tmp_blog_upload_folder_path)
    return tmp_blog_upload_folder_path


def test_reorder_media_as_guest_fails(
    test_client: TestClient, basic_blog_post_module: db_models.BlogPost
):
    """Test that a guest cannot reorder media."""
    bp = basic_blog_post_module
    response = test_client.patch(f"/blog/{bp.id}/media/1", data={})
    assert response.status_code == status.HTTP_200_OK
    assert "Sign In</h1>" in response.text


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_reorder_media_as_basic_user_fails(
    test_client: TestClient, basic_blog_post_module: db_models.BlogPost
):
    """Test that a basic user cannot reorder media."""
    bp = basic_blog_post_module
    response = test_client.patch(f"/blog/{bp.id}/media/1", data={})

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "403 Error" in response.text
    assert "You do not have permission to perform this action" in response.text


MEDIA_1 = "Some media 1"
MEDIA_2 = "Some media 2"
MEDIA_3 = "Some media 3"


class MediaReorderTestCase(TestCase):
    """Test case for reordering media."""

    bp_id: int | str | None = None
    rel_media_id: int | None = None
    absolute_media_id: int | str | None = ""
    position: int | str = ""
    expected_status_code: int = status.HTTP_200_OK
    expected_strings: list[str] = []  # noqa: RUF012
    expected_order: list[str] = [MEDIA_3, MEDIA_1, MEDIA_2]  # noqa: RUF012


MEDIA_REORDER_TEST_CASES = [
    MediaReorderTestCase(
        id="0_to_1",
        rel_media_id=0,
        position=1,
        expected_order=[MEDIA_1, MEDIA_3, MEDIA_2],
    ),
    MediaReorderTestCase(
        id="1_to_1",
        rel_media_id=1,
        position=1,
        expected_order=[MEDIA_2, MEDIA_3, MEDIA_1],
    ),
    MediaReorderTestCase(
        id="2_to_1",
        rel_media_id=2,
        position=1,
        expected_order=[MEDIA_3, MEDIA_1, MEDIA_2],
    ),
    MediaReorderTestCase(
        id="2_to_blank",
        rel_media_id=2,
        position="",
        expected_order=[MEDIA_1, MEDIA_2, MEDIA_3],
    ),
    MediaReorderTestCase(
        id="1_to_-1",
        rel_media_id=1,
        position=-1,
        expected_order=[MEDIA_2, MEDIA_3, MEDIA_1],
    ),
    MediaReorderTestCase(
        id="bad_position",
        rel_media_id=1,
        position="foo",
        expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        expected_strings=["Invalid position"],
    ),
    MediaReorderTestCase(
        id="media_not_found",
        absolute_media_id=999,
        position=2,
        expected_status_code=status.HTTP_404_NOT_FOUND,
        expected_strings=["Blog post media not found"],
    ),
    MediaReorderTestCase(
        id="bp_not_found",
        bp_id=999,
        rel_media_id=1,
        position=2,
        expected_status_code=status.HTTP_404_NOT_FOUND,
        expected_strings=["Blog post not found"],
    ),
]


@pytest.mark.usefixtures("logged_in_admin_user_module", "clean_db_except_users")
@MediaReorderTestCase.parametrize(MEDIA_REORDER_TEST_CASES)
def test_reorder_media_as_admin_user(
    test_client: TestClient,
    blog_post_with_media: db_models.BlogPost,
    test_case: MediaReorderTestCase,
):
    """Test that an admin user can reorder media."""
    bp = blog_post_with_media
    bp_id = test_case.bp_id or bp.id
    if test_case.rel_media_id is not None:
        sorted_media = sorted(bp.media, key=lambda m: m.id)
        media_id: Any = sorted_media[test_case.rel_media_id].id
    else:
        media_id = test_case.absolute_media_id
    response = test_client.patch(
        f"/blog/{bp_id}/media/{media_id}", data={"position": str(test_case.position)}
    )
    assert response.status_code == test_case.expected_status_code
    for string in test_case.expected_strings:
        assert string in response.text
    if response.status_code == status.HTTP_200_OK:
        order = find_order(response.text)
        assert order == test_case.expected_order


def find_order(html: str):
    """Find the order of the 3 media strings."""
    positions = [
        (html.find(MEDIA_1), MEDIA_1),
        (html.find(MEDIA_2), MEDIA_2),
        (html.find(MEDIA_3), MEDIA_3),
    ]
    positions.sort()
    return [string for _, string in positions]


def test_delete_media_as_guest_fails(
    test_client: TestClient, basic_blog_post_module: db_models.BlogPost
):
    """Test that a guest cannot delete media."""
    bp = basic_blog_post_module
    response = test_client.delete(f"/blog/{bp.id}/media/1")
    assert response.status_code == status.HTTP_200_OK
    assert "Sign In</h1>" in response.text


@pytest.mark.usefixtures("logged_in_basic_user_module")
def test_delete_media_as_basic_user_fails(
    test_client: TestClient, basic_blog_post_module: db_models.BlogPost
):
    """Test that a basic user cannot delete media."""
    bp = basic_blog_post_module
    response = test_client.delete(f"/blog/{bp.id}/media/1")

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "403 Error" in response.text
    assert "You do not have permission to perform this action" in response.text


class MediaDeleteTestCase(TestCase):
    """Test case for deleting media."""

    bp_id: int | str | None = None
    rel_media_id: int | None = None
    absolute_media_id: int | str | None = ""
    expected_status_code: int = status.HTTP_200_OK
    expected_strings: list[str] = []  # noqa: RUF012
    expected_missing_strings: list[str] = []  # noqa: RUF012


MEDIA_DELETE_TEST_CASES = [
    MediaDeleteTestCase(
        id="media_1",
        rel_media_id=0,
        expected_strings=["Some media 2", "Some media 3"],
        expected_missing_strings=["Some media 1"],
    ),
    MediaDeleteTestCase(
        id="media_not_found",
        absolute_media_id=999,
        expected_status_code=status.HTTP_404_NOT_FOUND,
        expected_strings=["Blog post media not found"],
    ),
    MediaDeleteTestCase(
        id="bp_not_found",
        bp_id=999,
        rel_media_id=1,
        expected_status_code=status.HTTP_404_NOT_FOUND,
        expected_strings=["Blog post not found"],
    ),
]


@pytest.mark.usefixtures("logged_in_admin_user_module", "clean_db_except_users")
@MediaDeleteTestCase.parametrize(MEDIA_DELETE_TEST_CASES)
def test_delete_media_as_admin_user(
    test_client: TestClient,
    blog_post_with_media: db_models.BlogPost,
    test_case: MediaDeleteTestCase,
):
    """Test that an admin user can delete media."""
    bp = blog_post_with_media
    bp_id = test_case.bp_id or bp.id
    if test_case.rel_media_id is not None:
        sorted_media = sorted(bp.media, key=lambda m: m.id)
        media_id: Any = sorted_media[test_case.rel_media_id].id
    else:
        media_id = test_case.absolute_media_id
    response = test_client.delete(f"/blog/{bp_id}/media/{media_id}")
    assert response.status_code == test_case.expected_status_code
    for string in test_case.expected_strings:
        assert string in response.text
    for string in test_case.expected_missing_strings:
        assert string not in response.text
