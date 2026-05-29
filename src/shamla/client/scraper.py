import zendriver as zd
import asyncio
from contextlib import asynccontextmanager
import time
import shutil
import os
import glob
import re
from typing import Callable, Union

from shamla.models.book import Book_data
from shamla.models.chapter import Chapter
from shamla.models.page import Page_data
from shamla.client.parser import parse_book_html, parse_toc, parse_book_page

def find_browser_executable() -> str | None:
    """Dynamically search for google-chrome or chromium browser binary."""
    # 1. Search standard PATH
    for name in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]:
        path = shutil.which(name)
        if path:
            return path

    # 2. Search local Playwright cache directory
    playwright_dir = os.path.expanduser("~/.cache/ms-playwright")
    if os.path.exists(playwright_dir):
        # Look for typical path structure: **/chrome-linux/chrome or **/chrome
        chrome_paths = glob.glob(os.path.join(playwright_dir, "**/chrome-linux/chrome"), recursive=True)
        if chrome_paths:
            return chrome_paths[0]
        chrome_paths_alt = glob.glob(os.path.join(playwright_dir, "**/chrome"), recursive=True)
        if chrome_paths_alt:
            return chrome_paths_alt[0]

    return None

class Network:
    def __init__(self, browser: zd.Browser, verbose: bool):
        self.browser = browser
        self.verbose = verbose

    @classmethod
    async def create(cls, headless: bool, verbose: bool = True):
        # Configure executable path dynamically
        exec_path = find_browser_executable()
        if verbose:
            print(f"Using browser executable at: {exec_path}")
            
        config = zd.Config(headless=headless, browser_executable_path=exec_path)
        
        browser = await zd.start(config=config)
        return cls(browser, verbose)

    async def wait_for_selector(
        self, page, selector: str, timeout: float = 15, checking_interval: float = 0.2
    ):
        start = time.monotonic()

        while (time.monotonic() - start) < timeout:
            try:
                el = await page.query_selector(selector)
                if el:
                    return el
            except Exception as e:
                if self.verbose:
                    print(f"Exception {e} while waiting for selector")

            await asyncio.sleep(checking_interval)

        raise TimeoutError(f"Timeout waiting for selector: {selector}")

    async def get(self, url: str, wait_for: str | None = None, timeout=15, retries=1):
        page = await self.browser.get(url, new_tab=True)
        if wait_for:
            for attempt in range(retries):
                try:
                    await self.wait_for_selector(page, wait_for, timeout=timeout)
                    break
                except TimeoutError:
                    if self.verbose:
                        print(f"Attempt {attempt + 1}/{retries} failed for {url}")
                    await page.close()
                    if attempt < retries - 1:
                        page = await self.browser.get(url, new_tab=True)
                    else:
                        raise
        return page


class Scraper:
    def __init__(self, network: Network):
        self.network = network

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

    async def get_book(self, url: str) -> str:
        """Fetch raw HTML content of the main book metadata/index page."""
        page = await self.network.get(url, ".text-center")
        html = await page.get_content()
        await page.close()
        return html

    async def get_book_metadata(self, url_or_id: str) -> Book_data:
        """Fetch and parse book metadata details."""
        url, book_id = self._normalize_url(url_or_id)
        html = await self.get_book(url)
        metadata = parse_book_html(html)
        metadata.book_id = book_id
        return metadata

    async def get_book_toc(self, url_or_id: str) -> list[Chapter]:
        """Fetch and parse book table of contents (TOC)."""
        url, _ = self._normalize_url(url_or_id)
        html = await self.get_book(url)
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
        """Fetch and parse a specific book page contents."""
        _, book_id = self._normalize_url(url_or_id)
        if not book_id:
            raise ValueError(f"Could not extract book ID from: {url_or_id}")
            
        page_url = f"https://shamela.ws/book/{book_id}/{page_number}"
        # Pages have page anchor elements rather than .text-center
        page = await self.network.get(page_url, ".anchor")
        html = await page.get_content()
        await page.close()
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

    @classmethod
    @asynccontextmanager
    async def create_scraper(cls, headless=False):
        network = await Network.create(headless)
        scraper = cls(network)
        try:
            yield scraper
        finally:
            await scraper.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        await self.network.browser.stop()

# Helper import to normalize URLs inside Scraper class methods
