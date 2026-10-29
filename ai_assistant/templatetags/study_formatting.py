"""Readable, HTML-disabled formatting for generated study text."""

from html import unescape

from django import template
from django.utils.safestring import mark_safe
from markdown_it import MarkdownIt

register = template.Library()


@register.filter
def study_markdown(value):
    """Format generated text without trusting provider HTML or changing stored data."""
    if not value:
        return ""

    # Decode pasted entities before parsing; HTML is always escaped by the parser.
    text = unescape(str(value)).replace("\xa0", " ")
    parser = MarkdownIt("commonmark", {"html": False, "breaks": True})
    parser.disable(["image", "link", "autolink"])
    tokens = parser.parse(text)

    # AI headings belong below the page's section heading, never above it.
    headings = [token for token in tokens if token.type == "heading_open"]
    first_level = min((int(token.tag[1:]) for token in headings), default=1)
    for token in tokens:
        if token.type in {"heading_open", "heading_close"}:
            token.tag = f"h{min(6, int(token.tag[1:]) - first_level + 3)}"

    # Only the HTML-disabled parser's output is marked safe, never raw AI text.
    return mark_safe(parser.renderer.render(tokens, parser.options, {}))
