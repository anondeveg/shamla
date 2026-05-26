import asyncio
from abc import ABC, abstractmethod
from typing import Callable
from shamla.models.book import Book_data
from shamla.models.chapter import Chapter
from shamla.models.page import Page_data

class BookExporter(ABC):
    """Abstract base class for all book exporters."""
    
    @abstractmethod
    async def export_metadata(self, metadata: Book_data) -> None:
        """Export book metadata details."""
        pass

    @abstractmethod
    async def export_toc(self, chapters: list[Chapter]) -> None:
        """Export book table of contents (TOC)."""
        pass

    @abstractmethod
    async def export_page(self, page: Page_data) -> None:
        """Export a single book page contents."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Finalize and close connection or files."""
        pass

async def export_book(
    scraper,
    book_id: str,
    exporter: BookExporter,
    max_pages: int | None = None,
    progress_callback: Callable[[str, int], None] | None = None,
    concurrency: int = 1,
    **scraper_kwargs
) -> None:
    """Coordinate fetching data from scraper and exporting using exporter."""
    
    # 1. Export Metadata
    if progress_callback:
        progress_callback("metadata", 0)
    try:
        metadata = await scraper.get_book_metadata(book_id)
        await exporter.export_metadata(metadata)
    except Exception:
        # If metadata is missing/fails, we still continue to pages if possible, or raise
        pass

    # 2. Export TOC
    if progress_callback:
        progress_callback("toc", 0)
    try:
        toc = await scraper.get_book_toc(book_id)
        await exporter.export_toc(toc)
    except Exception:
        pass

    # 3. Export Pages
    page = 1
    consecutive_failures = 0
    max_consecutive_failures = 3

    while True:
        batch_size = concurrency if concurrency > 1 else 1
        pages_batch = []
        for i in range(batch_size):
            p_num = page + i
            if max_pages is not None and p_num > max_pages:
                break
            pages_batch.append(p_num)

        if not pages_batch:
            break

        # Create tasks for current batch
        tasks = []
        for p_num in pages_batch:
            if progress_callback:
                progress_callback("page", p_num)
            tasks.append(scraper.get_book_page(book_id, p_num, **scraper_kwargs))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        should_stop = False
        for p_num, res in zip(pages_batch, results):
            if isinstance(res, Exception):
                if isinstance(res, (FileNotFoundError, ValueError)):
                    should_stop = True
                    break
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= max_consecutive_failures:
                        should_stop = True
                        break
                    continue

            await exporter.export_page(res)
            consecutive_failures = 0

        if should_stop:
            break

        page += batch_size

    # 4. Finalize
    await exporter.close()
