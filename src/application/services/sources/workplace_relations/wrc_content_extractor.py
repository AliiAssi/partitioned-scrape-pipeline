from bs4 import BeautifulSoup

from src.application.exceptions import ContentExtractionError
from src.application.services.sources.workplace_relations import wrc_config


class WrcContentExtractor:
    def extract(self, payload: bytes) -> bytes:
        # used for turning a saved page into just the decision text, wrapped in a minimal document
        soup = BeautifulSoup(payload, "html.parser")
        content = self._locate_content(soup)
        if content is None:
            raise ContentExtractionError("no decision content container found on page")

        for selector in wrc_config.STRIP_SELECTORS:
            for node in content.select(selector):
                node.decompose()
        for anchor in content.find_all("a"):
            if anchor.get_text(strip=True).lower() == wrc_config.RETURN_LINK_TEXT:
                anchor.decompose()

        title = soup.title.get_text(strip=True) if soup.title else ""
        return self._wrap(title, content.decode_contents()).encode("utf-8")

    def _locate_content(self, soup: BeautifulSoup):
        # used for finding the content column, tolerating the two markup variants seen on the site
        for selector in wrc_config.CONTENT_SELECTORS:
            node = soup.select_one(selector)
            if node is not None and node.get_text(strip=True):
                return node
        return None

    def _wrap(self, title: str, inner_html: str) -> str:
        # used so the curated file is still a valid standalone html document
        return wrc_config.CURATED_DOCUMENT_TEMPLATE.format(title=title, content=inner_html)
