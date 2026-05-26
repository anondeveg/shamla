# Chapter 5: Advanced Performance & Concurrency

This chapter covers the multi-threaded concurrent crawling features of the `shamla` library, and best-practice crawler etiquette parameters.

---

## ⚡ 1. The Concurrency Model

Since page fetching uses synchronous library requests inside worker threads (via `urllib`), concurrent requests are managed using `asyncio.to_thread` and `asyncio.gather`. 

Concurrency operates in **batches**:
1. Pages are queried in chunks of size `concurrency` (e.g. `[101, 102, 103]` if `concurrency=3`).
2. If any page returns a redirect or `404 Not Found` (signaling the end of the book), all subsequent pages inside that batch are discarded and the loop terminates cleanly.

---

## ⚙️ 2. Configuration Examples

### Configure `BookDownloader` Concurrency
Specify `concurrency` during instantiation. 

```python
import asyncio
import shamla as sh

async def main():
    # Setup 10 concurrent downloaders with a tiny batch-delay of 0.05 seconds
    downloader = sh.BookDownloader(
        base_dir="./downloads", 
        concurrency=10, 
        delay=0.05
    )
    
    await downloader.download_book("23627", max_pages=100)
    print("Downloaded 100 pages concurrently!")

if __name__ == "__main__":
    asyncio.run(main())
```

---

### Configure Database Export Concurrency
Specify `concurrency` inside the `export_book` function call.

```python
import asyncio
import shamla as sh

async def main():
    exporter = sh.SQLiteExporter("concurrent_library.db")
    
    async with sh.LocalScraper(base_dir="./downloads") as scraper:
        # Stream and export page data to SQLite concurrently in groups of 5 pages
        await sh.export_book(
            scraper=scraper,
            book_id="23627",
            exporter=exporter,
            concurrency=5,
            max_pages=100
        )

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🚦 3. Rate-Limiting & Crawling Etiquette

While concurrent batching is extremely fast, scraping servers at very high concurrency can result in rate-limiting, IP throttling, or temporary blocks. 

To maintain healthy scraper operations, follow these recommendations:

| Parameter | Recommended Value | Description |
|---|---|---|
| `concurrency` | `3` to `5` | Balanced speed without overloading server request queues. |
| `delay` | `0.1` to `0.2` seconds | Add a slight pause between batch iterations. |
| `User-Agent` | Custom string | Provide a descriptive headers User-Agent to avoid generic blocks. |

> [!WARNING]
> By default, `concurrency` is set to `1` in both `BookDownloader` and `export_book`. You must explicitly pass a higher concurrency value if you wish to run concurrent downloads.
