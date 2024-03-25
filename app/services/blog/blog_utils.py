"""blog_utils: blog service utility functions."""

import math
import re


def get_slug(title: str) -> str:
    """Generate a slug from a title.

    Remove problematic characters.
    """
    title = re.sub("[!@#$%^&*()+=`~<>/:;.,]", "", title)
    return re.sub(r"[^\w]+", "-", title.lower()).strip(" -")


def calc_read_mins(content: str, image_count: int = 0) -> int:
    """Calculate an article's read time in minutes (rounded up)."""
    # Define time for an activity
    seconds_per_image = 5
    seconds_added_per_codeblock = 8
    words_per_minute = 200

    # Redefine time in terms of `per minute`
    mins_per_image = seconds_per_image / 60
    mins_per_codeblock = seconds_added_per_codeblock / 60
    mins_per_word = 1 / words_per_minute

    # Get content
    code_blocks_count = content.count("```") // 2
    # not all are words, but close
    word_count = len(strip_markdown(content).split())

    # Add time per content
    total_time = (
        (image_count * mins_per_image)
        + (code_blocks_count * mins_per_codeblock)
        + (word_count * mins_per_word)
    )
    return math.ceil(total_time)


def strip_markdown(md: str) -> str:
    """Strip markdown of weird syntax (for HTML meta description)."""
    # Remove images
    regex = r"\!\[.*?\)"
    md = re.sub(regex, "", md)
    # Remove <picture> tags
    regex = r"<picture>.*?</picture>"
    md = re.sub(regex, "", md)
    # Remove HTML classes
    regex = r"\{\:.*?\}"
    md = re.sub(regex, "", md)
    # Remove links
    regex = r"\[(.*?)\]\(.*?\)"
    md = re.sub(regex, r"\1", md)
    # Remove random "#"
    md = md.replace("#", "")
    # Replace white space with single space and return
    return " ".join(md.split())


# ------------ Blog Post Parts ------------
def get_bp_introduction(content: str) -> str:
    """Get the introduction of the blog post."""
    if re_match := re.search(r"## Introduction\n\n(.*?)(?=\n##)", content, re.DOTALL):
        return re_match[1]
    msg = "No introduction found in the blog post content."
    raise ValueError(msg)


def get_bp_tags(content: str) -> list[str]:
    """Get the tags of the blog post."""
    if re_match := re.search(r"tags: (.*)\n", content):
        return re_match[1].split(", ")
    msg = "No tags found in the blog post content."
    raise ValueError(msg)


def get_bp_thumbnail(content: str) -> str | None:
    """Get the thumbnail of the blog post."""
    if re_match := re.search(r"thumbnail:\s(.*)\n", content):
        return re_match[1].strip(" <>")
    return None


def get_bp_title(content: str) -> str:
    """Get the title of the blog post."""
    if re_match := re.search(r"# (.*)\n", content):
        return re_match[1]
    msg = "No title found in the blog post content."
    raise ValueError(msg)


def get_bp_content(content: str) -> str:
    """Get the content of the blog post."""
    if re_match := re.search(r"## Introduction\n\n(.*$)", content, re.DOTALL):
        return re_match[1]
    msg = "No content found in the blog post content."
    raise ValueError(msg)
