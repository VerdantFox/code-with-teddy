"""bundler: get static files from CDNs and bundle them into files to host locally."""

import asyncio
import re
from pathlib import Path

import aiohttp
from pydantic import BaseModel

STATIC_BASE = Path(__file__).parent.parent / "app" / "web" / "html" / "static"
JS_BUNDLED_DEFERRED = STATIC_BASE / "js" / "libraries" / "bundled-deferred.js"
JS_BUNDLED_NON_DEFERRED = STATIC_BASE / "js" / "libraries" / "bundled-non-deferred.js"
CSS_BUNDLED = STATIC_BASE / "css" / "libraries" / "bundled.css"

JS_DELIVER_API = "https://data.jsdelivr.com/v1/packages/npm"
MINIFIER_API = "https://www.toptal.com/developers/javascript-minifier/api/raw"


class Dependency(BaseModel):
    """A static file dependency."""

    name: str  # display name
    api_name: str  # Name to lookup in API
    url: str  # Includes {version} string where version goes
    bundle_path: Path
    add_version: bool  # Whether to include a version string before
    version_pin: str | None = None  # If not use latest version
    minify: bool = False  # Whether to minify the file

    # Generated dynamically
    version: str = ""  # The version of the dependency
    content: str = ""  # The content of the CDN


DEPENDENCIES = {
    "Alpine JS--focus plugin": Dependency(
        name="Alpine JS--focus plugin",
        api_name="@alpinejs/focus",
        url="https://cdn.jsdelivr.net/npm/@alpinejs/focus@{version}/dist/cdn.min.js",
        bundle_path=JS_BUNDLED_DEFERRED,
        add_version=True,
    ),
    "Alpine JS--intersect plugin": Dependency(
        name="Alpine JS--intersect plugin",
        api_name="@alpinejs/intersect",
        url="https://cdn.jsdelivr.net/npm/@alpinejs/intersect@{version}/dist/cdn.min.js",
        bundle_path=JS_BUNDLED_DEFERRED,
        add_version=True,
    ),
    "Alpine JS--morph plugin": Dependency(
        name="Alpine JS--morph plugin",
        api_name="@alpinejs/morph",
        url="https://cdn.jsdelivr.net/npm/@alpinejs/morph@{version}/dist/cdn.min.js",
        bundle_path=JS_BUNDLED_DEFERRED,
        add_version=True,
    ),
    "Alpine JS--persist plugin": Dependency(
        name="Alpine JS--persist plugin",
        api_name="@alpinejs/persist",
        url="https://cdn.jsdelivr.net/npm/@alpinejs/persist@{version}/dist/cdn.min.js",
        bundle_path=JS_BUNDLED_DEFERRED,
        add_version=True,
    ),
    "Alpine JS": Dependency(
        name="Alpine JS",
        api_name="alpinejs",
        url="https://cdn.jsdelivr.net/npm/alpinejs@{version}/dist/cdn.min.js",
        bundle_path=JS_BUNDLED_DEFERRED,
        add_version=True,
    ),
    "Popper.js": Dependency(
        name="Popper.js",
        api_name="@popperjs/core",
        url="https://unpkg.com/@popperjs/core@{version}/dist/umd/popper.min.js",
        bundle_path=JS_BUNDLED_NON_DEFERRED,
        add_version=False,
    ),
    "Tippy.js": Dependency(
        name="Tippy.js",  # Depends on popper.js
        api_name="tippy.js",
        url="https://unpkg.com/tippy.js@{version}/dist/tippy-bundle.umd.min.js",
        bundle_path=JS_BUNDLED_NON_DEFERRED,
        add_version=True,
    ),
    "Tippy--Scale subtle animation": Dependency(
        name="Tippy--Scale subtle animation",
        api_name="tippy.js",
        url="https://unpkg.com/tippy.js@{version}/animations/scale-subtle.css",
        bundle_path=CSS_BUNDLED,
        add_version=True,
    ),
    "Sweet Alert 2": Dependency(
        name="Sweet Alert 2",
        api_name="sweetalert2",
        url="https://cdn.jsdelivr.net/npm/sweetalert2@{version}/dist/sweetalert2.all.min.js",
        bundle_path=JS_BUNDLED_NON_DEFERRED,
        add_version=False,
    ),
    "HTMX": Dependency(
        name="HTMX",
        api_name="htmx.org",
        url="https://unpkg.com/htmx.org@{version}/dist/htmx.min.js",
        bundle_path=JS_BUNDLED_NON_DEFERRED,
        add_version=True,
    ),
    "HTMX--response targets extension": Dependency(
        name="HTMX--response targets extension",
        api_name="htmx-ext-response-targets",
        url="https://cdn.jsdelivr.net/npm/htmx-ext-response-targets@{version}",
        bundle_path=JS_BUNDLED_NON_DEFERRED,
        add_version=True,
        minify=True,
        version_pin="2.0.2",  # For some reason 2.0.3 uses module imports that break things...
    ),
    "HTMX--alpine morph extension": Dependency(
        name="HTMX--alpine morph extension",
        api_name="htmx-ext-alpine-morph",
        url="https://unpkg.com/htmx-ext-alpine-morph@{version}/alpine-morph.js",
        bundle_path=JS_BUNDLED_NON_DEFERRED,
        add_version=True,
        minify=True,
    ),
    "Simple Notify--JS": Dependency(
        name="Simple Notify--JS",
        api_name="simple-notify",
        url="https://cdn.jsdelivr.net/npm/simple-notify@{version}/dist/simple-notify.min.js",
        bundle_path=JS_BUNDLED_NON_DEFERRED,
        add_version=True,
    ),
    "Simple Notify--CSS": Dependency(
        name="Simple Notify--CSS",
        api_name="simple-notify",
        url="https://cdn.jsdelivr.net/npm/simple-notify@{version}/dist/simple-notify.css",
        bundle_path=CSS_BUNDLED,
        add_version=True,
    ),
    "Freezeframe": Dependency(
        name="Freezeframe",
        api_name="freezeframe",
        url="https://unpkg.com/freezeframe@{version}/dist/freezeframe.min.js",
        bundle_path=JS_BUNDLED_NON_DEFERRED,
        add_version=True,
    ),
}


async def main() -> None:
    """Coordinate and run the script."""
    dependencies = DEPENDENCIES.copy()
    await update_versions(dependencies)
    await update_contents(dependencies)
    write_to_files(dependencies)


async def update_versions(dependencies: dict[str, Dependency]) -> None:
    """Update the versions of the dependencies in-place."""
    coroutines = [get_and_update_version(dep) for dep in dependencies.values()]
    await asyncio.gather(*coroutines)


async def get_and_update_version(dependency: Dependency) -> None:
    """Get an individual dependency's version and update the version attribute in place."""
    if dependency.version_pin:
        dependency.version = dependency.version_pin
        return

    url = f"{JS_DELIVER_API}/{dependency.api_name}"
    async with aiohttp.ClientSession() as session, session.get(url) as resp:
        resp.raise_for_status()
        data = await resp.json()
        version = data["tags"]["latest"]
    assert version
    dependency.version = version


async def update_contents(dependencies: dict[str, Dependency]) -> None:
    """Update the contents of the dependencies in-place."""
    coroutines = [get_and_update_content(dep) for dep in dependencies.values()]
    await asyncio.gather(*coroutines)


async def get_and_update_content(dependency: Dependency) -> None:
    """Get an individual dependency's content and update the content attribute in place."""
    url = dependency.url.replace("{version}", dependency.version)
    async with aiohttp.ClientSession() as session, session.get(url) as resp:
        resp.raise_for_status()
        content = await resp.text()
    content = strip_source_map(content)
    if dependency.minify:
        content = await minify(content)
    assert content
    if dependency.add_version:
        if dependency.bundle_path == CSS_BUNDLED:
            content = f"/* {dependency.name} v{dependency.version} */\n{content}"
        else:
            content = f"// {dependency.name} v{dependency.version}\n{content}"
    dependency.content = f"{content.strip()}\n\n"


async def minify(content: str) -> str:
    """Minify the content."""
    async with (
        aiohttp.ClientSession() as session,
        session.post(MINIFIER_API, data={"input": content}) as resp,
    ):
        resp.raise_for_status()
        return await resp.text()


def strip_source_map(content: str) -> str:
    """Strip the source map from the content."""
    content = re.sub(r"/\*#\s*sourceMappingURL=.*\.map\s*\*/", "", content)
    content = re.sub(r"//#\s*sourceMappingURL=.*\.map", "", content)
    return content.strip()


def write_to_files(dependencies: dict[str, Dependency]) -> None:
    """Write the contents of the dependencies to their respective files."""
    clear_files(JS_BUNDLED_DEFERRED, JS_BUNDLED_NON_DEFERRED, CSS_BUNDLED)
    for dependency in dependencies.values():
        write_to_file(dependency)


def clear_files(*path: Path) -> None:
    """Clear the contents of the files."""
    # First create file if it doesn't exist
    for p in path:
        p.touch(exist_ok=True)

    # Then clear the contents
    for p in path:
        p.write_text("")


def write_to_file(dependency: Dependency) -> None:
    """Write the content of an individual dependency to a file."""
    with dependency.bundle_path.open("a") as file_:
        file_.write(dependency.content)


if __name__ == "__main__":
    asyncio.run(main())
