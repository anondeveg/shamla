import os
import re
from typing import Callable, Union

from shamla.models.book import Book_data
from shamla.models.chapter import Chapter
from shamla.models.page import Page_data
from shamla.client.parser import parse_book_html, parse_toc, parse_book_page

class LocalScraper:
    """Offline scraper that reads book metadata, TOC, and pages from a local directory structure."""
    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    def _normalize_url(self, url_or_id: str) -> tuple[str, str]:
        """Normalize url/id to return both (normalized_url, book_id)."""
        url_or_id = url_or_id.strip()
        if url_or_id.isdigit():
            return f"https://shamela.ws/book/{url_or_id}", url_or_id
        
        # If it is a full URL, extract book ID
        match = re.search(r'/book/(\d+)', url_or_id)
        if match:
            return url_or_id, match.group(1)
        
        return url_or_id, ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def close(self) -> None:
        """No-op for API compatibility."""
        pass

    async def get_book_metadata(self, url_or_id: str) -> Book_data:
        """Fetch and parse book metadata details from the local file."""
        _, book_id = self._normalize_url(url_or_id)
        if not book_id:
            raise ValueError(f"Could not extract book ID from: {url_or_id}")
            
        path = os.path.join(self.base_dir, book_id, "metadata.html")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Local metadata file not found: {path}")
            
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        metadata = parse_book_html(html)
        metadata.book_id = book_id
        return metadata

    async def get_book_toc(self, url_or_id: str) -> list[Chapter]:
        """Fetch and parse book table of contents (TOC) from the local file."""
        _, book_id = self._normalize_url(url_or_id)
        if not book_id:
            raise ValueError(f"Could not extract book ID from: {url_or_id}")
            
        path = os.path.join(self.base_dir, book_id, "metadata.html")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Local metadata file not found: {path}")
            
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        return parse_toc(html)

    async def get_book_page(
        self,
        url_or_id: str,
        page_number: int,
        citation_patterns: list[Union[str, re.Pattern]] | None = None,
        custom_extractor: Callable[[str], list[str]] | None = None,
        departments: list[str] | None = None,
        ignore_diacritics: bool = False,
        keep_diacritics_in_paragraphs: bool = False
    ) -> Page_data:
        """Fetch and parse a specific book page contents from the local file."""
        _, book_id = self._normalize_url(url_or_id)
        if not book_id:
            raise ValueError(f"Could not extract book ID from: {url_or_id}")
            
        path = os.path.join(self.base_dir, book_id, "pages", f"{page_number}.html")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Local page file not found: {path}")
            
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
            
        return parse_book_page(
            html,
            book_id,
            page_number,
            citation_patterns=citation_patterns,
            custom_extractor=custom_extractor,
            departments=departments,
            ignore_diacritics=ignore_diacritics,
            keep_diacritics_in_paragraphs=keep_diacritics_in_paragraphs
        )
