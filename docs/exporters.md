# Chapter 4: Data Exporters

This chapter details the pluggable exporter framework and concrete SQLite database exporter.

---

## 🔌 1. The Pluggable Exporter Framework

The library uses a pluggable interface (`BookExporter`) to cleanly separate page retrieval from how and where the scraped data is saved. 

```python
from abc import ABC, abstractmethod
from shamla.models.book import Book_data
from shamla.models.chapter import Chapter
from shamla.models.page import Page_data

class BookExporter(ABC):
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
```

You run the export process using the coordinator function:
```python
await sh.export_book(scraper, book_id, exporter, max_pages=10)
```

---

## 🗄️ 2. SQLite Database Exporter (`SQLiteExporter`)

The built-in `SQLiteExporter` writes scraped book data asynchronously to a local SQLite database file, creating a clean relational schema with three tables (`books`, `chapters`, and `pages`).

### Database Export Example:
```python
import asyncio
import shamla as sh

async def main():
    db_path = "my_library.db"
    exporter = sh.SQLiteExporter(db_path)
    
    # Let's scrape offline files using LocalScraper (or sh.Scraper for online)
    async with sh.LocalScraper(base_dir="./downloads") as scraper:
        print("Starting SQLite export process...")
        
        await sh.export_book(
            scraper=scraper,
            book_id="23627",
            exporter=exporter,
            max_pages=5,
            concurrency=3
        )
        
        print(f"Export completed! Database saved to {db_path}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## ✍️ 3. Creating a Custom Exporter (JSON Lines Exporter)

To export book data to other formats (e.g. JSON Lines, CSV, Elasticsearch, or a remote REST API), inherit from `BookExporter` and implement the abstract methods.

Here is a complete, runnable example of a custom **JSON Lines Exporter** that writes metadata and pages to a text file:

```python
import asyncio
import json
import shamla as sh

class JSONLinesExporter(sh.BookExporter):
    def __init__(self, filename: str):
        self.filename = filename
        self.file = None

    async def export_metadata(self, metadata: sh.Book_data) -> None:
        # Create/open file and write metadata header line
        self.file = open(self.filename, "w", encoding="utf-8")
        meta_dict = {
            "type": "metadata",
            "title": metadata.title,
            "author": metadata.author_name,
            "publisher": metadata.publisher
        }
        self.file.write(json.dumps(meta_dict, ensure_ascii=False) + "\n")

    async def export_toc(self, chapters: list[sh.Chapter]) -> None:
        toc_dict = {
            "type": "toc",
            "chapters": [
                {"title": c.title, "page": c.page_number, "depth": c.depth} 
                for c in chapters
            ]
        }
        self.file.write(json.dumps(toc_dict, ensure_ascii=False) + "\n")

    async def export_page(self, page: sh.Page_data) -> None:
        page_dict = {
            "type": "page",
            "number": page.page_number,
            "part": page.part_number,
            "headings": page.headings,
            "paragraphs": page.paragraphs,
            "citations": page.citations,
            "departments": page.departments
        }
        self.file.write(json.dumps(page_dict, ensure_ascii=False) + "\n")

    async def close(self) -> None:
        if self.file:
            self.file.close()

async def main():
    exporter = JSONLinesExporter("book_export.jsonl")
    
    async with sh.LocalScraper(base_dir="./downloads") as scraper:
        await sh.export_book(
            scraper=scraper,
            book_id="23627",
            exporter=exporter,
            max_pages=5
        )
        print("JSONL Export complete!")

if __name__ == "__main__":
    asyncio.run(main())
```
