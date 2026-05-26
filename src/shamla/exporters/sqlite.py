import sqlite3
import json
import asyncio
import re
from shamla.models.book import Book_data
from shamla.models.chapter import Chapter
from shamla.models.page import Page_data
from shamla.exporters.base import BookExporter

class SQLiteExporter(BookExporter):
    """Concrete exporter implementation that writes book data to a SQLite database asynchronously."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = None
        self._init_db()

    def _init_db(self) -> None:
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = self._conn.cursor()
        
        # 1. Create books table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id TEXT PRIMARY KEY,
                title TEXT,
                author_name TEXT,
                author_page TEXT,
                publisher TEXT,
                book_print TEXT,
                volumes INTEGER,
                is_equal_to_print INTEGER,
                book_description TEXT
            )
        """)
        
        # 2. Create chapters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chapters (
                book_id TEXT,
                title TEXT,
                url TEXT,
                page_number INTEGER,
                depth INTEGER
            )
        """)
        
        # 3. Create pages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                book_id TEXT,
                page_number INTEGER,
                part_number TEXT,
                headings TEXT,
                paragraphs TEXT,
                footnotes TEXT,
                citations TEXT,
                departments TEXT,
                PRIMARY KEY (book_id, page_number)
            )
        """)
        self._conn.commit()

    def _write_metadata(self, metadata: Book_data) -> None:
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO books (
                id, title, author_name, author_page, publisher, book_print, volumes, is_equal_to_print, book_description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metadata.book_id or "unknown",
            metadata.title,
            metadata.author_name,
            metadata.author_page,
            metadata.publisher,
            metadata.book_print,
            metadata.volumes,
            1 if metadata.is_equal_to_print else 0,
            metadata.book_description
        ))
        self._conn.commit()

    def _write_toc(self, book_id: str, chapters: list[Chapter]) -> None:
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM chapters WHERE book_id = ?", (book_id,))
        for ch in chapters:
            cursor.execute("""
                INSERT INTO chapters (book_id, title, url, page_number, depth)
                VALUES (?, ?, ?, ?, ?)
            """, (book_id, ch.title, ch.url, ch.page_number, ch.depth))
        self._conn.commit()

    def _write_page(self, page: Page_data) -> None:
        cursor = self._conn.cursor()
        
        headings_str = json.dumps(page.headings, ensure_ascii=False)
        paragraphs_str = json.dumps(page.paragraphs, ensure_ascii=False)
        
        footnotes_list = [{"number": f.number, "content": f.content} for f in page.footnotes]
        footnotes_str = json.dumps(footnotes_list, ensure_ascii=False)
        
        citations_str = json.dumps(page.citations, ensure_ascii=False)
        departments_str = json.dumps(page.departments, ensure_ascii=False)
        
        cursor.execute("""
            INSERT OR REPLACE INTO pages (
                book_id, page_number, part_number, headings, paragraphs, footnotes, citations, departments
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            page.book_id,
            page.page_number,
            page.part_number,
            headings_str,
            paragraphs_str,
            footnotes_str,
            citations_str,
            departments_str
        ))
        self._conn.commit()

    def _close_conn(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    async def export_metadata(self, metadata: Book_data) -> None:
        await asyncio.to_thread(self._write_metadata, metadata)

    async def export_toc(self, chapters: list[Chapter]) -> None:
        book_id = "unknown"
        if chapters:
            match = re.search(r'/book/(\d+)', chapters[0].url)
            if match:
                book_id = match.group(1)
        await asyncio.to_thread(self._write_toc, book_id, chapters)

    async def export_page(self, page: Page_data) -> None:
        await asyncio.to_thread(self._write_page, page)

    async def close(self) -> None:
        await asyncio.to_thread(self._close_conn)
