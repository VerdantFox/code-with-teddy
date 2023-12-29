"""media_handler: service for handling media files."""
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Protocol

from fastapi import UploadFile
from PIL import Image

from app.web.html.const import STATIC_DIR

AVATAR_UPLOAD_FOLDER = STATIC_DIR / "media" / "avatars"
BLOG_UPLOAD_FOLDER = STATIC_DIR / "media" / "blog"
for path in (AVATAR_UPLOAD_FOLDER, BLOG_UPLOAD_FOLDER):
    path.mkdir(exist_ok=True)


class ImageFileProtocol(Protocol):
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
    pil_save(
        pic=pic.file,
        filepath=path,
        max_width=600,
        max_height=600,
        quality=90,
    )
    return get_path_str_from_static(path)


def pil_save(
    pic: ImageFileProtocol,
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


def pil_thumbnail(pic: ImageFileProtocol, max_width: int, max_height: int) -> Image:
    """Thumbnail with pillow."""
    image = Image.open(pic)
    output_size = (max_width, max_height)
    image.thumbnail(output_size)
    return image


def secure_filename(filename: str) -> str:
    """Pass it a filename and it will return a secure version of it.

    From werkzeug.utils.secure_filename.
    """
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")

    for sep in os.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, "_")

    _filename_ascii_strip_re = re.compile(r"[^A-Za-z0-9_.-]")
    return str(_filename_ascii_strip_re.sub("", "_".join(filename.split()))).strip("._")


def get_suffix(file: UploadFile) -> str:
    """Get the suffix of a filename."""
    if not file.content_type:
        msg = "File has no content type."
        raise ValueError(msg)
    return file.content_type.split("/")[-1].lower()


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
