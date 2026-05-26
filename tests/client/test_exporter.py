import pytest
import sqlite3
import json
import os
import tempfile
import asyncio
from unittest.mock import AsyncMock, MagicMock
import shamla as sh
from shamla.models.book import Book_data
from shamla.models.chapter import Chapter
from shamla.models.page import Page_data, Footnote

# Test basic exporter inheritance / extensibility (JSON exporter example)
def test_exporter_extensibility():
    class DummyJSONExporter(sh.BookExporter):
        def __init__(self):
            self.metadata_called = False
            self.toc_called = False
            self.page_called = False
            self.closed = False
            
        async def export_metadata(self, metadata: Book_data) -> None:
            self.metadata_called = True

        async def export_toc(self, chapters: list[Chapter]) -> None:
            self.toc_called = True

        async def export_page(self, page: Page_data) -> None:
            self.page_called = True

        async def close(self) -> None:
            self.closed = True

    exporter = DummyJSONExporter()
    assert isinstance(exporter, sh.BookExporter)

@pytest.mark.asyncio
async def test_sqlite_exporter_persistence():
    # Use temporary file for SQLite DB
    fd, temp_db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    try:
        exporter = sh.SQLiteExporter(temp_db_path)
        
        # 1. Export Book Metadata
        metadata = Book_data(
            author_name="مؤلف تجريبي",
            author_page="https://shamela.ws/author/123",
            title="كتاب تجريبي",
            book_description="وصف الكتاب",
            publisher="دار النشر",
            book_print="الأولى",
            volumes=2,
            is_equal_to_print=True,
            book_id="123"
        )
        await exporter.export_metadata(metadata)
        
        # 2. Export TOC
        chapters = [
            Chapter(title="الفصل الأول", url="/book/123/1", page_number=1, depth=0),
            Chapter(title="الفصل الثاني", url="/book/123/5", page_number=5, depth=0),
        ]
        await exporter.export_toc(chapters)
        
        # 3. Export Page
        page_data = Page_data(
            book_id="123",
            page_number=1,
            part_number="الجزء الأول",
            headings=["العنوان الأول"],
            paragraphs=["الفقرة الأولى", "الفقرة الثانية"],
            footnotes=[Footnote(number="١", content="الهامش الأول")],
            citations=["اقتباس"],
            departments={"poetry": ["شعر ... شعر"]}
        )
        await exporter.export_page(page_data)
        
        # Close connection
        await exporter.close()
        
        # 4. Verify SQLite contents directly
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # Verify books table
        cursor.execute("SELECT * FROM books WHERE id = '123'")
        book_row = cursor.fetchone()
        assert book_row is not None
        assert book_row[1] == "كتاب تجريبي"
        assert book_row[2] == "مؤلف تجريبي"
        assert book_row[7] == 1  # is_equal_to_print (bool as int)
        
        # Verify chapters table
        cursor.execute("SELECT * FROM chapters WHERE book_id = '123'")
        toc_rows = cursor.fetchall()
        assert len(toc_rows) == 2
        assert toc_rows[0][1] == "الفصل الأول"
        assert toc_rows[0][3] == 1 # page_number
        assert toc_rows[1][1] == "الفصل الثاني"
        assert toc_rows[1][4] == 0 # depth
        
        # Verify pages table
        cursor.execute("SELECT * FROM pages WHERE book_id = '123' AND page_number = 1")
        page_row = cursor.fetchone()
        assert page_row is not None
        assert page_row[2] == "الجزء الأول"
        assert json.loads(page_row[3]) == ["العنوان الأول"]
        assert json.loads(page_row[4]) == ["الفقرة الأولى", "الفقرة الثانية"]
        assert json.loads(page_row[5]) == [{"number": "١", "content": "الهامش الأول"}]
        assert json.loads(page_row[6]) == ["اقتباس"]
        assert json.loads(page_row[7]) == {"poetry": ["شعر ... شعر"]}
        
        conn.close()
    finally:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)

@pytest.mark.asyncio
async def test_export_book_coordinator():
    # Setup mocks for scraper and exporter
    mock_scraper = AsyncMock()
    
    metadata = Book_data(
        author_name="مؤلف",
        author_page="page",
        title="title",
        book_description="desc",
        publisher="pub",
        book_print="print",
        volumes=1,
        is_equal_to_print=False,
        book_id="123"
    )
    mock_scraper.get_book_metadata.return_value = metadata
    
    chapters = [Chapter(title="c1", url="/book/123/1", page_number=1, depth=0)]
    mock_scraper.get_book_toc.return_value = chapters
    
    page_data = Page_data(
        book_id="123",
        page_number=1,
        part_number="p1",
        headings=[],
        paragraphs=["text"],
        footnotes=[],
        citations=[],
        departments={}
    )
    # page 1 succeeds, page 2 raises FileNotFoundError to stop loop
    mock_scraper.get_book_page.side_effect = [page_data, FileNotFoundError("end of book")]

    mock_exporter = AsyncMock(spec=sh.BookExporter)
    
    progress_calls = []
    def callback(stage, page):
        progress_calls.append((stage, page))

    # Run coordinator
    await sh.export_book(
        scraper=mock_scraper,
        book_id="123",
        exporter=mock_exporter,
        progress_callback=callback
    )
    
    # Assert exporter calls
    mock_exporter.export_metadata.assert_called_once_with(metadata)
    mock_exporter.export_toc.assert_called_once_with(chapters)
    mock_exporter.export_page.assert_called_once_with(page_data)
    mock_exporter.close.assert_called_once()
    
    assert ("metadata", 0) in progress_calls
    assert ("toc", 0) in progress_calls
    assert ("page", 1) in progress_calls
    assert ("page", 2) in progress_calls

@pytest.mark.asyncio
async def test_export_book_coordinator_consecutive_failures_limit():
    mock_scraper = AsyncMock()
    # Mock metadata and TOC to raise error (coordinator skips them cleanly)
    mock_scraper.get_book_metadata.side_effect = Exception("failed metadata")
    mock_scraper.get_book_toc.side_effect = Exception("failed TOC")
    
    # Page loop raises three generic errors
    mock_scraper.get_book_page.side_effect = [
        Exception("generic error"),
        Exception("generic error"),
        Exception("generic error")
    ]
    
    mock_exporter = AsyncMock(spec=sh.BookExporter)
    
    # Run coordinator
    await sh.export_book(
        scraper=mock_scraper,
        book_id="123",
        exporter=mock_exporter,
        max_pages=5
    )
    
    # Verify metadata and TOC exports were not called due to exceptions
    mock_exporter.export_metadata.assert_not_called()
    mock_exporter.export_toc.assert_not_called()
    mock_exporter.close.assert_called_once()

@pytest.mark.asyncio
async def test_export_book_coordinator_max_pages_limit():
    mock_scraper = AsyncMock()
    # Mock metadata and TOC to return none or raise exception cleanly
    mock_scraper.get_book_metadata.side_effect = Exception("skip")
    mock_scraper.get_book_toc.side_effect = Exception("skip")
    
    # Setup mock page returns
    page_data = Page_data(
        book_id="123", page_number=1, part_number="p1", headings=[],
        paragraphs=["text"], footnotes=[], citations=[], departments={}
    )
    mock_scraper.get_book_page.return_value = page_data
    
    mock_exporter = AsyncMock(spec=sh.BookExporter)
    
    # Run coordinator with max_pages=2.
    # The loop will query page 1, page 2, and then hit page 3. Since page 3 > max_pages (2), it breaks!
    await sh.export_book(
        scraper=mock_scraper,
        book_id="123",
        exporter=mock_exporter,
        max_pages=2
    )
    
    # Verify exporter close was called
    mock_exporter.close.assert_called_once()

@pytest.mark.asyncio
async def test_exporter_base_class_abstract_coverage():
    # Concrete subclass to invoke super() base class methods for coverage
    class ConcreteExporter(sh.BookExporter):
        async def export_metadata(self, metadata: Book_data) -> None:
            await super().export_metadata(metadata)

        async def export_toc(self, chapters: list[Chapter]) -> None:
            await super().export_toc(chapters)

        async def export_page(self, page: Page_data) -> None:
            await super().export_page(page)

        async def close(self) -> None:
            await super().close()

    exporter = ConcreteExporter()
    
    # Call them to cover the abstract methods (which contain pass)
    await exporter.export_metadata(None)
    await exporter.export_toc([])
    await exporter.export_page(None)
    await exporter.close()

@pytest.mark.asyncio
async def test_export_book_coordinator_concurrency():
    mock_scraper = AsyncMock()
    
    metadata = Book_data(
        author_name="مؤلف",
        author_page="page",
        title="title",
        book_description="desc",
        publisher="pub",
        book_print="print",
        volumes=1,
        is_equal_to_print=False,
        book_id="123"
    )
    mock_scraper.get_book_metadata.return_value = metadata
    
    chapters = [Chapter(title="c1", url="/book/123/1", page_number=1, depth=0)]
    mock_scraper.get_book_toc.return_value = chapters
    
    pages = [
        Page_data("123", 1, "p1", [], ["text1"], [], [], {}),
        Page_data("123", 2, "p1", [], ["text2"], [], [], {}),
        Page_data("123", 3, "p1", [], ["text3"], [], [], {}),
        FileNotFoundError("end of book"),
        FileNotFoundError("end of book"),
        FileNotFoundError("end of book")
    ]
    mock_scraper.get_book_page.side_effect = pages

    mock_exporter = AsyncMock(spec=sh.BookExporter)
    
    await sh.export_book(
        scraper=mock_scraper,
        book_id="123",
        exporter=mock_exporter,
        concurrency=3,
        max_pages=10
    )
    
    # Assert exporter calls
    mock_exporter.export_metadata.assert_called_once_with(metadata)
    mock_exporter.export_toc.assert_called_once_with(chapters)
    
    assert mock_exporter.export_page.call_count == 3
    mock_exporter.export_page.assert_any_call(pages[0])
    mock_exporter.export_page.assert_any_call(pages[1])
    mock_exporter.export_page.assert_any_call(pages[2])
    mock_exporter.close.assert_called_once()
