"""Small text helpers for rendering API content safely in Qt widgets."""
import re
from html.parser import HTMLParser


class _PlainTextExtractor(HTMLParser):
    """Collect visible text while dropping tags, scripts, and styles."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001 - HTMLParser signature
        if tag in {"script", "style"}:
            self._skip_depth += 1
        elif tag in {"br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1
        elif tag in {"p", "div", "li", "tr", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


def html_to_plain(value: object) -> str:
    """Convert an HTML fragment to readable plain text.

    Used for NASA APOD descriptions, which can contain ``<strong>``, ``<a>``,
    and other markup from the WordPress feed.
    """
    if value is None:
        return ""
    parser = _PlainTextExtractor()
    parser.feed(str(value))
    parser.close()

    lines = [re.sub(r"\s+", " ", line).strip() for line in "".join(parser.parts).splitlines()]
    return "\n".join(line for line in lines if line)
