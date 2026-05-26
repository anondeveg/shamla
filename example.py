import asyncio
import sys
import os
import re
import json

# Add src/ folder to Python path if running locally
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

import shamla as sh


async def main():
    print("=========================================")
    print("Shamela Library Extractor (shamla) Demo")
    print("=========================================")

    # 1. Initialize the scraper
    # By default, it runs headless. It dynamically detects available Chrome/Chromium
    # executables or falls back to locally installed playwright binaries.
    print("\n[1] Starting the scraper...")
    async with sh.Scraper.create_scraper(headless=True) as scraper:
        print("Scraper started successfully!")

        # 2. Fetch Book Metadata
        # We will fetch metadata for book ID 172
        book_id = "23627"
        print(f"\n[2] Fetching metadata for book ID '{book_id}'...")
        try:
            metadata = await scraper.get_book_metadata(book_id)
            print("\n--- Book Metadata ---")
            print(f"Title:        {metadata.title}")
            print(f"Author:       {metadata.author_name}")
            print(f"Author Page:  {metadata.author_page}")
            print(f"Publisher:    {metadata.publisher or 'N/A'}")
            print(f"Print Info:   {metadata.book_print or 'N/A'}")
            print(f"Volumes:      {metadata.volumes}")
            print(f"Matches Print: {metadata.is_equal_to_print}")
            print(f"Description:\n{metadata.book_description}")
            print("---------------------")
        except Exception as e:
            print(f"Failed to fetch metadata: {e}")

        # 3. Fetch Table of Contents (TOC)
        # We will fetch TOC for book ID 23627 (تفسير الكشاف)
        book_id_toc = "23627"
        print(f"\n[3] Fetching Table of Contents for book ID '{book_id_toc}'...")
        try:
            toc = await scraper.get_book_toc(book_id_toc)
            print(f"Successfully retrieved {len(toc)} TOC entries.")
            print("\n--- TOC Structure (First 15 entries) ---")
            for chapter in toc[:15]:
                indent = "  " * chapter.depth
                print(
                    f"{indent}- {chapter.title} (Page: {chapter.page_number}, Depth: {chapter.depth})"
                )
            print("----------------------------------------")
        except Exception as e:
            print(f"Failed to fetch TOC: {e}")

        # 4. Fetch Page Content
        # We will fetch page 5 of book ID 23627 (الكشاف)
        page_num = 347
        print(f"\n[4] Fetching Page {page_num} of book ID '{book_id_toc}'...")
        try:
            page_data = await scraper.get_book_page(book_id_toc, page_num)
            print("\n--- Structured Page Data ---")
            print(f"Book ID:     {page_data.book_id}")
            print(f"Page Number: {page_data.page_number}")
            print(f"Part Number: {page_data.part_number}")

            print(f"\nHeadings ({len(page_data.headings)}):")
            for heading in page_data.headings:
                print(f"  * {heading}")

            print(f"\nParagraphs ({len(page_data.paragraphs)}):")
            for i, p in enumerate(page_data.paragraphs, start=1):
                # Print preview of the first few paragraphs
                preview = p[:120] + "..." if len(p) > 120 else p
                print(f"  {i}. {preview}")

            print(f"\nFootnotes ({len(page_data.footnotes)}):")
            for fn in page_data.footnotes:
                print(f"  [{fn.number}] {fn.content}")

            print(f"\nCitations/Quotes ({len(page_data.citations)}):")
            for cit in page_data.citations:
                print(f'  " {cit} "')
            print("----------------------------")
        except Exception as e:
            print(f"Failed to fetch page data: {e}")

        # 4.5. Dynamic loading of custom extraction rules
        print("\n[4.5] Loading custom extraction rules from 'my_custom_rules.py'...")
        try:
            sh.load_extractors_from_file("my_custom_rules.py")
            print("Successfully loaded custom extraction rules!")
        except Exception as e:
            print(f"Failed to load custom rules: {e}")

        # 4.6. Fetching page with registered departments
        print(f"\n[4.6] Fetching Page {page_num} and running all registered departments...")
        try:
            page_data_dept = await scraper.get_book_page(book_id_toc, page_num)
            
            # Print page departments info
            for dept_name, citations in page_data_dept.departments.items():
                print(f"\nDepartment '{dept_name}' extracted {len(citations)} citations:")
                for cit in citations[:5]:
                    print(f"  * {cit}")
            print("------------------------------------------------------------------")
        except Exception as e:
            print(f"Failed to fetch page with registered departments: {e}")

        # 4.7. Download Book locally and export to SQLite (with concurrency)
        print(f"\n[4.7] Downloading book metadata and first 5 pages for book '{book_id_toc}' locally with concurrency...")
        local_dir = "./offline_downloads"
        db_path = os.path.join(local_dir, "export_23627.db")
        try:
            downloader = sh.BookDownloader(base_dir=local_dir, concurrency=3, delay=0.1)
            
            def progress(stage, num):
                print(f"  -> Download progress: {stage} {num if num > 0 else ''}")
                
            await downloader.download_book(book_id_toc, max_pages=5, progress_callback=progress)
            print("Download completed successfully!")
            
            # Now run offline scraper on the downloaded files
            print("\nInitializing LocalScraper for offline parsing...")
            async with sh.LocalScraper(base_dir=local_dir) as local_scraper:
                # Initialize SQLite exporter
                print(f"Initializing SQLiteExporter at: {db_path}")
                exporter = sh.SQLiteExporter(db_path)
                
                # Export the book locally using the LocalScraper (with concurrency)
                print("Exporting book metadata, TOC, and pages to SQLite DB with concurrency...")
                await sh.export_book(
                    scraper=local_scraper,
                    book_id=book_id_toc,
                    exporter=exporter,
                    max_pages=5,
                    progress_callback=progress,
                    concurrency=3
                )
                print("Export completed successfully!")

            # 4.8. Verify and query database directly using sqlite3
            print("\n[4.8] Verifying exported database using direct SQL queries...")
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Query metadata
            cursor.execute("SELECT title, author_name, publisher FROM books LIMIT 1")
            meta_row = cursor.fetchone()
            print("\n--- SQL Query (books table) ---")
            print(f"Title:     {meta_row[0]}")
            print(f"Author:    {meta_row[1]}")
            print(f"Publisher: {meta_row[2]}")
            
            # Query TOC chapters count
            cursor.execute("SELECT COUNT(*) FROM chapters")
            toc_count = cursor.fetchone()[0]
            print(f"TOC Chapters count stored: {toc_count}")
            
            # Query page data for page 5
            cursor.execute("SELECT part_number, paragraphs, citations, departments FROM pages WHERE page_number = 5")
            page_row = cursor.fetchone()
            print("\n--- SQL Query (pages table for page 5) ---")
            print(f"Part Number:      {page_row[0]}")
            
            paragraphs = json.loads(page_row[1])
            print(f"Paragraphs count: {len(paragraphs)}")
            
            citations = json.loads(page_row[2])
            print(f"Citations count:  {len(citations)}")
            print(f"Citations list:   {citations}")
            
            departments = json.loads(page_row[3])
            print(f"Poetry Department: {departments.get('poetry')}")
            print("------------------------------------------")
            
            conn.close()
            print("Offline parsing and database export verified successfully!")
        except Exception as e:
            print(f"Offline demonstration failed: {e}")

    print("\n[5] Scraper stopped and cleaned up successfully.")
    print("Demo completed!")


if __name__ == "__main__":
    # Run the async loop
    asyncio.run(main())
