from __future__ import annotations

from html import escape


def escape_html(value: object) -> str:
    """Escape dynamic content before placing it into HTML-formatted messages."""

    return escape(str(value), quote=True)


def html_code(value: object) -> str:
    return f"<code>{escape_html(value)}</code>"
