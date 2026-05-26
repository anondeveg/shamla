# Chapter 1: Getting Started

This chapter covers the installation of the `shamla` library, browser requirements, and a minimal quick-start script.

---

## 🛠️ Quick Installation

Set up a virtual environment and install the required dependencies (such as `zendriver` for browser automation):

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (ensure zendriver is available)
pip install zendriver pytest pytest-asyncio pytest-cov
```

---

## 🔍 Headless Browser Requirements

The online scraper uses a headless Chromium/Google Chrome browser. The library includes automated binary detection which searches locations in this order:

1. **System PATH**: Looks for `google-chrome`, `google-chrome-stable`, `chromium`, or `chromium-browser`.
2. **Playwright Cache**: Searches local Playwright installations under `~/.cache/ms-playwright` for compatible chrome executables.

> [!TIP]
> If Chrome is not installed on your system, you can easily install the Playwright browser binaries to satisfy this dependency:
> ```bash
> pip install playwright
> playwright install chrome
> ```

---

## 🚀 Quick Start Example

Here is a minimal, fully functional asynchronous Python script to fetch a book's metadata, table of contents, and a specific page. 

```python
import asyncio
import shamla as sh

async def main():
    # 1. Initialize browser-based scraper in headless mode
    async with sh.Scraper.create_scraper(headless=True) as scraper:
        book_id = "23627"  # الكشاف للزمخشري
        
        # 2. Fetch metadata
        print("Fetching book details...")
        meta = await scraper.get_book_metadata(book_id)
        print(f"Title:  {meta.title}")
        print(f"Author: {meta.author_name}")
        
        # 3. Fetch Table of Contents
        print("\nFetching table of contents...")
        toc = await scraper.get_book_toc(book_id)
        print(f"Retrieved {len(toc)} sections.")
        for chapter in toc[:5]:
            indent = "  " * chapter.depth
            print(f"{indent}- {chapter.title} (Page {chapter.page_number})")
            
        # 4. Fetch Page 5
        print("\nFetching page 5 content...")
        page = await scraper.get_book_page(book_id, page_number=5)
        print(f"--- Page {page.page_number} (Part {page.part_number}) ---")
        for i, paragraph in enumerate(page.paragraphs[:3], 1):
            print(f"Paragraph {i}: {paragraph[:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
```
