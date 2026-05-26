import os
import re
import urllib.request
import urllib.error
import asyncio
from typing import Callable

class BookDownloader:
    """Handles fetching and saving book index and page HTML files to a local directory."""
    def __init__(self, base_dir: str, user_agent: str | None = None, delay: float = 0.5, concurrency: int = 1):
        self.base_dir = base_dir
        self.delay = delay
        self.concurrency = concurrency
        self.headers = {
            "User-Agent": user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def _fetch_url(self, url: str) -> tuple[str, str]:
        req = urllib.request.Request(url, headers=self.headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8")
            final_url = resp.geturl()
            return content, final_url

    async def download_book(
        self,
        book_id: str,
        max_pages: int | None = None,
        progress_callback: Callable[[str, int], None] | None = None
    ) -> None:
        """Download book metadata and all pages locally."""
        book_dir = os.path.join(self.base_dir, book_id)
        pages_dir = os.path.join(book_dir, "pages")
        os.makedirs(pages_dir, exist_ok=True)

        # 1. Download metadata page
        meta_url = f"https://shamela.ws/book/{book_id}"
        if progress_callback:
            progress_callback("metadata", 0)
            
        try:
            meta_html, final_url = await asyncio.to_thread(self._fetch_url, meta_url)
            if f"/book/{book_id}" not in final_url:
                raise ValueError(f"Invalid book ID: {book_id}")
                
            with open(os.path.join(book_dir, "metadata.html"), "w", encoding="utf-8") as f:
                f.write(meta_html)
        except Exception as e:
            raise RuntimeError(f"Failed to download book index page: {e}")

        # 2. Iterate pages starting from 1 in concurrent batches
        page = 1
        consecutive_failures = 0
        max_consecutive_failures = 3

        while True:
            batch_size = self.concurrency if self.concurrency > 1 else 1
            pages_batch = []
            for i in range(batch_size):
                p_num = page + i
                if max_pages is not None and p_num > max_pages:
                    break
                pages_batch.append(p_num)

            if not pages_batch:
                break

            if self.delay > 0 and page > 1:
                await asyncio.sleep(self.delay)

            # Create tasks for current batch
            tasks = []
            for p_num in pages_batch:
                page_url = f"https://shamela.ws/book/{book_id}/{p_num}"
                if progress_callback:
                    progress_callback("page", p_num)
                tasks.append(asyncio.to_thread(self._fetch_url, page_url))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            should_stop = False
            for p_num, res in zip(pages_batch, results):
                if isinstance(res, Exception):
                    if isinstance(res, urllib.error.HTTPError) and res.code == 404:
                        should_stop = True
                        break
                    else:
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            should_stop = True
                            break
                        continue

                html, final_url = res
                
                # Check for redirects away from this specific book/page
                pattern = rf"/book/{book_id}/{p_num}(?:\b|#|\?|$)"
                if not re.search(pattern, final_url):
                    should_stop = True
                    break

                # Double check that the HTML content actually contains a page anchor
                if 'class="anchor"' not in html and "class='anchor'" not in html:
                    should_stop = True
                    break

                with open(os.path.join(pages_dir, f"{p_num}.html"), "w", encoding="utf-8") as f:
                    f.write(html)
                    
                consecutive_failures = 0

            if should_stop:
                break

            page += batch_size
