#!/usr/bin/env python3
"""
Script to extract all poetry from a Shamela book and output it into a SQL file.
Uses lightweight direct HTTP requests to fetch pages and parses them using the shamla library.
Supports concurrency for high performance.
"""

import sys
import os
import re
import urllib.request
import urllib.error
import asyncio
import argparse

# Add src/ folder to Python path if running locally
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from shamla.client.parser import parse_book_page

# Robust pattern matching Arabic poetry hemistichs separated by dots or ellipsis
POETRY_PATTERN = r'([^\n\.\…\s][^\n\.\…]*[^\n\.\…\s])\s*(?:\.\.\.+|\…)\s*([^\n\.\…\s][^\n\.\…]*[^\n\.\…\s])'

def escape_sql(val: str) -> str:
    """Escape single quotes for SQL insertion."""
    return val.replace("'", "''")

def fetch_page_html(url: str, user_agent: str) -> tuple[str, str]:
    """Fetch HTML content and the final redirected URL."""
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read().decode("utf-8")
        final_url = resp.geturl()
        return content, final_url

async def extract_poetry_async(args) -> None:
    book_id = args.book_id
    output_file = args.output
    delay = args.delay
    start_page = args.start_page
    max_pages = args.max_pages
    user_agent = args.user_agent
    concurrency = args.concurrency
    
    print(f"==================================================")
    print(f"Starting concurrent poetry extraction for book ID: {book_id}")
    print(f"Output SQL file: {output_file}")
    print(f"Concurrency: {concurrency}")
    print(f"Request delay: {delay}s")
    print(f"Start page: {start_page}")
    if max_pages is not None:
        print(f"Scan limit: first {max_pages} pages")
    print(f"==================================================")

    # Initialize SQL file with table structure
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("-- SQL Dump of extracted poetry\n")
        f.write("-- Generated dynamically using the shamla library\n\n")
        f.write("CREATE TABLE IF NOT EXISTS poetry (\n")
        f.write("    id INTEGER PRIMARY KEY AUTOINCREMENT,\n")
        f.write("    book_id TEXT,\n")
        f.write("    page_number INTEGER,\n")
        f.write("    verse TEXT\n")
        f.write(");\n\n")
        f.write("BEGIN TRANSACTION;\n\n")

    page = start_page
    total_extracted = 0
    consecutive_failures = 0
    max_consecutive_failures = 3
    last_scanned_page = start_page - 1
    
    try:
        while True:
            batch_size = concurrency if concurrency > 1 else 1
            pages_batch = []
            for i in range(batch_size):
                p_num = page + i
                if max_pages is not None and (p_num - start_page) >= max_pages:
                    break
                pages_batch.append(p_num)

            if not pages_batch:
                break

            if delay > 0 and page > start_page:
                await asyncio.sleep(delay)

            # Create tasks for current batch
            tasks = []
            for p_num in pages_batch:
                page_url = f"https://shamela.ws/book/{book_id}/{p_num}"
                tasks.append(asyncio.to_thread(fetch_page_html, page_url, user_agent))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            should_stop = False
            for p_num, res in zip(pages_batch, results):
                last_scanned_page = p_num
                print(f"Scanning page {p_num}...", end="", flush=True)
                if isinstance(res, Exception):
                    if isinstance(res, urllib.error.HTTPError) and res.code == 404:
                        print(" [404 Not Found - End of book]")
                        should_stop = True
                        break
                    elif isinstance(res, urllib.error.HTTPError):
                        print(f" [HTTP Error {res.code}]")
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            should_stop = True
                            break
                        continue
                    else:
                        print(f" [Error: {res}]")
                        consecutive_failures += 1
                        if consecutive_failures >= max_consecutive_failures:
                            should_stop = True
                            break
                        continue

                html, final_url = res
                
                # Check for redirects away from this specific book/page
                pattern = rf"/book/{book_id}/{p_num}(?:\b|#|\?|$)"
                if not re.search(pattern, final_url):
                    print(" [End of book detected via redirect]")
                    should_stop = True
                    break

                # Double check that the HTML content actually contains page contents
                if 'class="anchor"' not in html and "class='anchor'" not in html:
                    print(" [End of book detected via missing page anchor]")
                    should_stop = True
                    break

                # Parse poetry citations using the regex pattern
                page_data = parse_book_page(html, book_id, p_num, citation_patterns=[POETRY_PATTERN])
                
                if page_data.citations:
                    print(f" [Found {len(page_data.citations)} verses]", flush=True)
                    with open(output_file, "a", encoding="utf-8") as f:
                        for verse in page_data.citations:
                            escaped_verse = escape_sql(verse)
                            f.write(f"INSERT INTO poetry (book_id, page_number, verse) VALUES ('{book_id}', {p_num}, '{escaped_verse}');\n")
                            total_extracted += 1
                else:
                    print(" [0 verses]", flush=True)
                    
                consecutive_failures = 0

            if should_stop:
                break

            page += batch_size
    finally:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write("\nCOMMIT;\n")
            
    print(f"==================================================")
    print(f"Poetry extraction completed successfully!")
    print(f"Total pages scanned: {last_scanned_page - start_page + 1}")
    print(f"Total poetry verses extracted: {total_extracted}")
    print(f"Output written to: {output_file}")
    print(f"==================================================")

def main():
    parser = argparse.ArgumentParser(description="Extract poetry from a Shamela book into a SQL file.")
    parser.add_argument("--book-id", type=str, default="23619", help="The book ID (default: 23619)")
    parser.add_argument("--output", type=str, default="poetry_23619.sql", help="Output SQL file name")
    parser.add_argument("--delay", type=float, default=0.0, help="Delay between requests in seconds (default: 0.0)")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent downloaders (default: 10)")
    parser.add_argument("--start-page", type=int, default=1, help="The page number to start scanning from (default: 1)")
    parser.add_argument("--max-pages", type=int, default=None, help="Maximum number of pages to scan")
    parser.add_argument("--user-agent", type=str, 
                        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        help="User agent header for requests")
    
    args = parser.parse_args()
    asyncio.run(extract_poetry_async(args))

if __name__ == "__main__":
    main()
