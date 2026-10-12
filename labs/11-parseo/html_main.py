"""Keep only the main content of a web page (drop navigation, footer, feedback widgets).

Shared by both parsers so the comparison measures structure, not boilerplate removal: Docling's
HTML backend parses the whole page, menus and footer included.
"""

from bs4 import BeautifulSoup, Tag

NOISE = ["script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg",
         "iframe"]
MAIN = ["main", "article", "[role=main]", "#content", "#main-content", ".content"]


def main_content(soup: BeautifulSoup) -> Tag:
    for tag in NOISE:
        for t in soup.find_all(tag):
            t.decompose()
    for selector in MAIN:
        node = soup.select_one(selector)
        if node and len(node.get_text(strip=True)) > 200:
            return node
    return soup.body or soup


def clean_html(raw: bytes) -> str:
    """A standalone HTML document containing only the main content."""
    soup = BeautifulSoup(raw, "html.parser")
    title = soup.title.string if soup.title and soup.title.string else ""
    body = main_content(soup)
    return f"<html><head><title>{title}</title></head><body>{body}</body></html>"
