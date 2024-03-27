"""media_handler: service for handling media files."""

from collections.abc import Iterable
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

import PIL
from fastapi import UploadFile
from PIL import Image
from werkzeug.utils import secure_filename

from app.web.html.const import STATIC_DIR

AVATAR_UPLOAD_FOLDER = STATIC_DIR / "media" / "avatars"
BLOG_UPLOAD_FOLDER = STATIC_DIR / "media" / "blog"
for path in (AVATAR_UPLOAD_FOLDER, BLOG_UPLOAD_FOLDER):
    path.mkdir(parents=True, exist_ok=True)


CONTENT_TYPE_MAP = {
    "image/svg+xml": "svg",
}
SUFFIX_MAP = {
    "svgxml": "svg",
}


class MediaType(str, Enum):
    """Media type."""

    IMAGE = "image"
    VIDEO = "video"


class MediaFileProtocol(Protocol):
    """Protocol for image file."""

    def seek(self, *args: Any, **kwargs: Any) -> int:
        """Seek."""
        ...

    def read(self, *args: Any, **kwargs: Any) -> bytes:
        """Read."""
        ...


async def upload_avatar(pic: UploadFile, name: str) -> str:
    """Upload an avatar file."""
    name = secure_filename(f"{name}.{get_suffix(pic)}")
    path = AVATAR_UPLOAD_FOLDER / name
    try:
        pil_save(
            pic=pic.file,
            filepath=path,
            max_width=600,
            max_height=600,
            quality=90,
        )
    except PIL.UnidentifiedImageError:
        # Save file without pillow processing
        path.write_bytes(await pic.read())
    return get_path_str_from_static(path)


def upload_blog_media(media: UploadFile, name: str) -> tuple[str, str]:
    """Upload a blog media file.

    Returns
    -------
        A tuple of the path string and the media type.

    See `save_media` for more details.

    """
    name = secure_filename(f"{name}.{get_suffix(media)}")
    return save_media(media, name)


def save_media(media: UploadFile, name: str) -> tuple[str, str]:
    """Save a media file.

    Returns
    -------
        A tuple of the path string and the media type.

    The path string is a comma-separated list of paths.

    Images save a webp version as well as the original,
    if the webp version is smaller.

    """
    media_type = get_media_type_from_file(media)
    if media_type == MediaType.IMAGE:
        return save_image(name, media.file), media_type
    if media_type == MediaType.VIDEO:
        return save_video(name, media.file), media_type
    msg = f"Unknown media type {media_type}"
    raise ValueError(msg)


def save_image(name: str, image_file: MediaFileProtocol) -> str:
    """Save an image, and its webp version."""
    og_image_path = BLOG_UPLOAD_FOLDER / _fix_name_suffix(name)

    try:
        pil_save(
            pic=image_file,
            filepath=og_image_path,
            max_width=1200,
            max_height=1200,
            quality=90,
        )
    except PIL.UnidentifiedImageError:
        # Save file without pillow processing
        og_image_path.write_bytes(image_file.read())
        images: Iterable[Path] = (og_image_path,)
    else:
        webp_image_path = convert_image(og_image_path)
        if compare_image_sizes(og_image_path, webp_image_path):
            webp_image_path.unlink()
        images = (path for path in (webp_image_path, og_image_path) if path.exists())
    return ",".join(get_path_str_from_static(image) for image in images)


def _fix_name_suffix(name: str) -> str:
    """Fix a name for weird suffixes."""
    parts = name.rsplit(".", 1)
    if len(parts) == 1:
        return name
    start, suffix = parts
    mapped_suffix = SUFFIX_MAP.get(suffix)
    return f"{start}.{mapped_suffix}" if mapped_suffix else name


def save_video(name: str, video: MediaFileProtocol) -> str:
    """Save a video."""
    video_path = BLOG_UPLOAD_FOLDER / name
    video_path.write_bytes(video.read())
    return get_path_str_from_static(video_path)


def pil_save(
    pic: MediaFileProtocol,
    filepath: Path,
    max_width: int,
    max_height: int,
    quality: int,
) -> None:
    """Use pillow to resize and save image."""
    image = pil_thumbnail(pic, max_width, max_height)
    try:
        image.save(str(filepath), optimize=True, quality=quality)
    except ValueError as e:
        msg = f"Error saving image: {e}"
        raise ValueError(msg) from e


def pil_thumbnail(pic: MediaFileProtocol, max_width: int, max_height: int) -> Image:
    """Thumbnail with pillow."""
    image = Image.open(pic)
    output_size = (max_width, max_height)
    image.thumbnail(output_size)
    return image


def get_media_type_from_file(file: UploadFile) -> MediaType:
    """Get the media type from a file."""
    return get_media_type_from_suffix(get_suffix(file))


def get_suffix(file: UploadFile) -> str:
    """Get the suffix of a filename."""
    parts = str(file.filename).rsplit(".", 1)
    if len(parts) == 1:
        msg = f"File {file.filename} has no suffix"
        raise ValueError(msg)
    _, suffix = parts
    return suffix.casefold()


def get_path_str_from_static(path: Path) -> str:
    """Get a path string after the static directory."""
    # Convert the path to a string and split it on 'static'
    parts = str(path).split("static", 1)
    # The second part of the split is the path after 'static'
    return parts[1]


def del_media_from_path_str(path_str: str) -> None:
    """Delete media from a path string."""
    if "://" in path_str:
        return
    path = rebuild_path_from_static(path_str)
    path.unlink(missing_ok=True)


def rebuild_path_from_static(path_str: str) -> Path:
    """Rebuild a path from the static directory."""
    return STATIC_DIR / path_str.strip("/\\ ")


def get_media_type_from_suffix(suffix: str) -> MediaType:
    """Get the media type from a suffix string."""
    suffix = suffix.casefold()
    if suffix in {"jpg", "jpeg", "png", "gif", "webp", "svg", "svgxml"}:
        return MediaType.IMAGE
    if suffix in {"mp4", "webm"}:
        return MediaType.VIDEO
    msg = f"Unknown media type for suffix {suffix}"
    raise ValueError(msg)


def convert_image(
    image_path: Path,
    format: str = "webp",  # noqa: A002
    quality: int = 90,
) -> Path:
    """Convert an image to an alternate format."""
    image = Image.open(image_path)
    image = image.convert("RGBA")
    new_path = image_path.with_suffix(f".{format}")
    image.save(new_path, format=format, optimize=True, quality=quality)
    return new_path


def compare_image_sizes(image1: Path, image2: Path) -> bool:
    """Compare the sizes of two images, returning True if image1 is larger."""
    image1_size = Path(image1).stat().st_size
    image2_size = Path(image2).stat().st_size
    return image1_size < image2_size
