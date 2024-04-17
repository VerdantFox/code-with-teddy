"""sitemap: Sitemap route for the web application."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from starlette.datastructures import URL

from app.datastore import db_models
from app.datastore.database import DBSession
from app.services.blog import blog_handler

# ----------- Routers -----------
router = APIRouter(tags=["sitemap"])


@router.get("/sitemap.xml", response_model=None)
async def sitemap(request: Request, db: DBSession) -> HTMLResponse:
    """Return the sitemap page."""
    return HTMLResponse(
        content=await create_sitemap_xml(request=request, db=db), media_type="application/xml"
    )


async def create_sitemap_xml(*, request: Request, db: DBSession) -> str:
    """Return the sitemap.xml file."""
    opener = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    )
    closer = "\n</urlset>"
    return f"{opener}\n{await create_sitemap_urls(request=request, db=db)}{closer}"


async def create_sitemap_urls(*, request: Request, db: DBSession) -> str:
    """Return the sitemap urls."""
    standard_urls_xml = get_standard_urls_xml(request=request)
    blog_urls_xml = await get_blog_urls_xml(request=request, db=db)
    return f"{standard_urls_xml}{blog_urls_xml}"


def get_standard_urls_xml(request: Request) -> str:
    """Return the standard urls xml."""
    standard_urls = get_standard_urls(request)
    return "".join([produce_standard_url_xml(url) for url in standard_urls])


def get_standard_urls(request: Request) -> list[str | URL]:
    """Return the sitemap urls."""
    return [
        str(request.url_for("html:about")).removesuffix("/"),
        request.url_for("html:projects"),
        request.url_for("html:experience"),
        request.url_for("html:list_blog_posts"),
    ]


def produce_standard_url_xml(url: URL | str) -> str:
    """Return the url xml."""
    return f"\n<url>\n  <loc>{url}</loc>\n  <changefreq>weekly</changefreq></url>"


async def get_blog_urls_xml(*, request: Request, db: DBSession) -> str:
    """Return the blog urls xml."""
    paginator = await blog_handler.get_blog_posts(
        db=db,
        can_see_unpublished=False,
        results_per_page=1_000_000,
        page=1,
    )
    return "".join(
        [
            produce_blog_url_xml(request=request, blog_post=blog_post)
            for blog_post in paginator.blog_posts
        ]
    )


def produce_blog_url_xml(*, request: Request, blog_post: db_models.BlogPost) -> str:
    """Return the url xml."""
    url = request.url_for("html:read_blog_post", slug=blog_post.slug)
    last_mod = blog_post.updated_timestamp.strftime("%Y-%m-%d")
    return (
        f"\n<url>\n  <loc>{url}</loc>\n  <lastmod>{last_mod}</lastmod>"
        "\n  <changefreq>weekly</changefreq>\n</url>"
    )
