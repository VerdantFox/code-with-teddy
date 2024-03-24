"""model_fixtures: fixtures for loading db_models for tests."""


import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.datastore import db_models
from app.services.blog import blog_handler
from tests.data import models as test_models

pytestmark = pytest.mark.anyio


# ------------------------ Users ------------------------
@pytest.fixture(name="basic_user")
async def add_basic_user(db_session: AsyncSession) -> db_models.User:
    """Return a basic user added to the database, function scoped."""
    user = test_models.basic_user()
    await add_user(db_session, user)
    return user


@pytest.fixture(name="basic_user_2")
async def add_basic_user_2(db_session: AsyncSession) -> db_models.User:
    """Return a basic user added to the database, function scoped."""
    user = test_models.basic_user(
        username="test_user_2", email="test2@email.com", full_name="Test User 2"
    )
    await add_user(db_session, user)
    return user


@pytest.fixture(name="basic_user_module", scope="module")
async def add_basic_user_module(db_session_module: AsyncSession) -> db_models.User:
    """Return a basic user added to the database, module scoped."""
    user = test_models.basic_user()
    await add_user(db_session_module, user)
    return user


@pytest.fixture(name="basic_user_2_module", scope="module")
async def add_basic_user_2_module(db_session_module: AsyncSession) -> db_models.User:
    """Return a basic user added to the database, module scoped."""
    user = test_models.basic_user(
        username="test_user_2", email="test2@email.com", full_name="Test User 2"
    )
    await add_user(db_session_module, user)
    return user


@pytest.fixture(name="admin_user")
async def add_admin_user(db_session: AsyncSession) -> db_models.User:
    """Return an admin user added to the database, function scoped."""
    user = test_models.admin_user()
    await add_user(db_session, user)
    return user


@pytest.fixture(name="admin_user_module", scope="module")
async def add_admin_user_module(db_session_module: AsyncSession) -> db_models.User:
    """Return an admin user added to the database, module scoped."""
    user = test_models.admin_user()
    await add_user(db_session_module, user)
    return user


async def add_user(db_session: AsyncSession, user: db_models.User) -> db_models.User:
    """Add a user to the database."""
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ------------------------ Blog Posts -------------------
@pytest.fixture(name="basic_blog_post")
async def add_basic_blog_post(db_session: AsyncSession) -> db_models.BlogPost:
    """Return a basic blog post added to the database."""
    blog_post_input: blog_handler.SaveBlogInput = test_models.basic_blog_post()
    response = await blog_handler.save_blog_post(db=db_session, data=blog_post_input)
    assert response.blog_post
    return response.blog_post


@pytest.fixture(name="basic_blog_post_module", scope="module")
async def add_basic_blog_post_module(db_session_module: AsyncSession) -> db_models.BlogPost:
    """Return a basic blog post added to the database."""
    blog_post_input: blog_handler.SaveBlogInput = test_models.basic_blog_post(
        title="Module Blog Post"
    )
    response = await blog_handler.save_blog_post(db=db_session_module, data=blog_post_input)
    assert response.blog_post
    return response.blog_post


@pytest.fixture(name="unpublished_blog_post")
async def add_unpublished_blog_post(db_session: AsyncSession) -> db_models.BlogPost:
    """Return an unpublished blog post added to the database."""
    bp_input = test_models.basic_blog_post(is_published=False, title="Unpublished Blog Post")
    response = await blog_handler.save_blog_post(db=db_session, data=bp_input)
    assert response.blog_post
    return response.blog_post


@pytest.fixture(scope="module", name="unpublished_blog_post_module")
async def add_unpublished_blog_post_module(db_session_module: AsyncSession) -> db_models.BlogPost:
    """Return an unpublished blog post added to the database."""
    bp_input = test_models.basic_blog_post(is_published=False, title="Unpublished Blog Post")
    response = await blog_handler.save_blog_post(db=db_session_module, data=bp_input)
    assert response.blog_post
    return response.blog_post


@pytest.fixture(name="blog_post_cannot_comment")
async def add_blog_post_cannot_comment(db_session: AsyncSession) -> db_models.BlogPost:
    """Return a blog post that cannot be commented on, added to the database."""
    bp_input = test_models.basic_blog_post(can_comment=False, title="Cannot Comment Blog Post")
    response = await blog_handler.save_blog_post(db=db_session, data=bp_input)
    assert response.blog_post
    return response.blog_post


@pytest.fixture(name="blog_post_cannot_comment_module", scope="module")
async def add_blog_post_cannot_comment_module(
    db_session_module: AsyncSession,
) -> db_models.BlogPost:
    """Return a blog post that cannot be commented on, added to the database."""
    bp_input = test_models.basic_blog_post(can_comment=False, title="Cannot Comment Blog Post")
    response = await blog_handler.save_blog_post(db=db_session_module, data=bp_input)
    assert response.blog_post
    return response.blog_post


@pytest.fixture(name="advanced_blog_post")
async def add_advanced_blog_post(db_session: AsyncSession) -> db_models.BlogPost:
    """Return an advanced blog post added to the database."""
    return await save_advanced_blog_post(db_session)


@pytest.fixture(name="advanced_blog_post_with_user")
async def add_advanced_blog_post_with_user(
    db_session: AsyncSession, basic_user: db_models.User
) -> db_models.BlogPost:
    """Return an advanced blog post added to the database."""
    return await save_advanced_blog_post(db_session, user=basic_user)


@pytest.fixture(name="advanced_blog_post_module", scope="module")
async def add_advanced_blog_post_module(db_session_module: AsyncSession) -> db_models.BlogPost:
    """Return an advanced blog post added to the database."""
    return await save_advanced_blog_post(db_session_module)


@pytest.fixture(name="advanced_blog_post_with_user_module", scope="module")
async def add_advanced_blog_post_with_user_module(
    db_session_module: AsyncSession, basic_user_module: db_models.User
) -> db_models.BlogPost:
    """Return an advanced blog post added to the database."""
    return await save_advanced_blog_post(db_session_module, user=basic_user_module)


async def save_advanced_blog_post(
    db_session: AsyncSession, user: db_models.User | None = None
) -> db_models.BlogPost:
    """Save an advanced blog post to the database."""
    bp_input = test_models.advanced_blog_post()
    bp_response = await blog_handler.save_blog_post(db=db_session, data=bp_input)
    bp = bp_response.blog_post
    assert bp
    await blog_handler.commit_media_to_db(
        db=db_session,
        blog_post=bp,
        name="Some media",
        locations_str="some_location.png",
        media_type="image/png",
    )
    comment_input1 = blog_handler.SaveCommentInput(
        bp_id=bp.id,
        guest_id="guest_id_1",
        name="Guest 1",
        email="guest1@email.com",
        content="Some comment",
    )
    comment_response1 = await blog_handler.save_new_comment(db=db_session, data=comment_input1)
    assert comment_response1.comment
    old_slug = db_models.OldBlogPostSlug(slug="old-slug-1", blog_post_id=bp.id)
    db_session.add(old_slug)
    await db_session.commit()

    if user:
        comment_input2 = blog_handler.SaveCommentInput(
            bp_id=bp.id,
            user_id=user.id,
            content="# Some comment from user",
        )
        comment_response2 = await blog_handler.save_new_comment(db=db_session, data=comment_input2)
        assert comment_response2.comment

    await db_session.refresh(bp, attribute_names=["comments", "old_slugs"])
    return bp


@pytest.fixture(name="several_blog_posts")
async def add_several_blog_posts(db_session: AsyncSession) -> list[db_models.BlogPost]:
    """Return several blog posts added to the database, function scoped."""
    return await _add_several_blog_posts(db_session)


@pytest.fixture(name="several_blog_posts_module", scope="module")
async def add_several_blog_posts_module(
    db_session_module: AsyncSession,
) -> list[db_models.BlogPost]:
    """Return several blog posts added to the database, module scoped."""
    return await _add_several_blog_posts(db_session_module)


async def _add_several_blog_posts(db_session: AsyncSession) -> list[db_models.BlogPost]:
    """Return several blog posts added to the database."""
    blog_post_inputs = [
        test_models.basic_blog_post(
            title=f"basic_{i}",
            tags=[f"foo_{i+j}" for j in range(3)],
            content=f"test blog post {i}. " * i,
            likes=i,
            views=i * 10,
        )
        for i in range(1, 5)
    ]
    blog_post_inputs[1].is_published = False
    blog_posts = []
    for bp_input in blog_post_inputs:
        response = await blog_handler.save_blog_post(db=db_session, data=bp_input)
        assert response.blog_post
        blog_posts.append(response.blog_post)
    return blog_posts
