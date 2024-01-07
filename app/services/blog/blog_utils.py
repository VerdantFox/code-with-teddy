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
