# Chapter 2: Scrapers & Offline Mode

This chapter explains the difference between the three scraper and scraper-like classes in the library:
1. **`Scraper`**: Live online parsing via headless browser automation.
2. **`BookDownloader`**: Concurrent local bulk down-loader.
3. **`LocalScraper`**: High-performance parser that reads downloaded pages offline without browser overhead.

---

## 🌐 1. Live Online Scraper (`Scraper`)

The `Scraper` class uses a headless browser to render pages dynamically. This is useful for real-time reads.

```python
import asyncio
import shamla as sh

async def main():
    # Instantiate live scraper
    async with sh.Scraper.create_scraper(headless=True) as scraper:
        # Fetch live pages
        page_data = await scraper.get_book_page("23627", page_number=10)
        print(f"Read online page: {page_data.paragraphs[0][:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📥 2. Book Downloader (`BookDownloader`)

The `BookDownloader` class uses Python's standard library `urllib` to fetch HTML files and save them to a structured local directory. It supports **concurrency** and custom delays to reduce server load.

### Download Directory Structure:
```text
./downloads/
└── 23627/
    ├── metadata.html
    └── pages/
        ├── 1.html
        ├── 2.html
        └── 3.html
```

### Complete Downloading Example:
```python
import asyncio
import shamla as sh

async def main():
    # Download with 3 concurrent workers and 0.1s delay between batches
    downloader = sh.BookDownloader(base_dir="./downloads", concurrency=3, delay=0.1)
    
    def on_progress(stage: str, page_num: int):
        print(f"Downloaded: {stage} {page_num if page_num > 0 else ''}")

    # Downloads metadata and first 5 pages of book 23627
    await downloader.download_book(
        book_id="23627",
        max_pages=5,
        progress_callback=on_progress
    )
    print("Download finished!")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📴 3. Offline Local Scraper (`LocalScraper`)

Once a book has been saved to disk, you can extract its contents using the zero-dependency `LocalScraper`. It matches the API signature of the live `Scraper` class exactly, making switching online/offline seamless.

```python
import asyncio
import shamla as sh

async def main():
    # Point LocalScraper to your downloads directory
    async with sh.LocalScraper(base_dir="./downloads") as local_scraper:
        
        # 1. Fetch metadata offline
        meta = await local_scraper.get_book_metadata("23627")
        print(f"[Offline] Title: {meta.title}")
        
        # 2. Fetch page offline
        page = await local_scraper.get_book_page("23627", page_number=2)
        print(f"[Offline] Page 2 Paragraphs: {len(page.paragraphs)}")

if __name__ == "__main__":
    asyncio.run(main())
```
