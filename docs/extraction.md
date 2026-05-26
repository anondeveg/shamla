# Chapter 3: Custom Text & Poetry Extraction

This chapter details how to use the extensible extraction engine in the `shamla` library to parse custom categories (departments), such as poetry or specific citation formats, using regex heuristic rules.

---

## 🔍 1. How Custom Extraction Works

By default, the library extracts standard double-quoted citations. However, many books contain poetry (verses split by `...` or `…`) or other structured notations that you can capture dynamically by passing custom rules.

When scraping a page, the results are populated into the `citations` and `departments` fields of the returned `Page_data`.

---

## 📝 2. Defining Custom Extraction Rules

You can write extraction rules directly in Python. A rule requires:
1. **Department Name**: The category under which matched text is filed (e.g., `"poetry"`, `"hadith"`).
2. **Regex Pattern**: A compiled pattern (or list of patterns) matching the text.

### Example: Manual Custom Extraction
```python
import asyncio
import re
import shamla as sh

async def main():
    async with sh.Scraper.create_scraper(headless=True) as scraper:
        # Define a pattern for poetry: hemistichs separated by ellipsis ... or …
        poetry_pattern = re.compile(
            r'([^\n\.\…\s][^\n\.\…]*[^\n\.\…\s])\s*(?:\.\.\.+|\…)\s*([^\n\.\…\s][^\n\.\…]*[^\n\.\…\s])'
        )
        
        # Scrape and run the custom extractor on the page
        page = await scraper.get_book_page(
            url_or_id="23627",
            page_number=347,
            citation_patterns=[poetry_pattern],
            departments=["poetry"]  # Tag matched quotes as 'poetry'
        )
        
        # Output results
        print(f"Extracted {len(page.citations)} custom verses:")
        for verse in page.citations:
            print(f"  * {verse}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🗃️ 3. Using the Extraction Registry

For cleaner architectures, the library provides a global **`ExtractionRegistry`**. You can register rules globally once, and all page requests will automatically process them.

```python
import asyncio
import shamla as sh

# 1. Register a rule globally
sh.register_extractor(
    department="poetry",
    pattern=r'([^\n\.\…\s][^\n\.\…]*[^\n\.\…\s])\s*(?:\.\.\.+|\…)\s*([^\n\.\…\s][^\n\.\…]*[^\n\.\…\s])'
)

async def main():
    # 2. Scraper automatically uses globally registered rules
    async with sh.Scraper.create_scraper(headless=True) as scraper:
        page = await scraper.get_book_page("23627", 347)
        
        # Globally registered rules are populated in page.departments
        poetry_verses = page.departments.get("poetry", [])
        print(f"Found {len(poetry_verses)} registered poetry verses:")
        for v in poetry_verses:
            print(f"  - {v}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📂 4. Loading Extraction Rules Dynamically from a File

If you have complex rules (e.g. for different book genres), you can store them in standalone Python files and import them dynamically using `load_extractors_from_file`.

### Step 1: Create a Rules File (`my_custom_rules.py`)
Create a file containing your rule registrations:

```python
# my_custom_rules.py
import re
import shamla as sh

# Poetry separator rule
sh.register_extractor(
    department="poetry",
    pattern=re.compile(r'([^\n\.\…\s][^\n\.\…]*[^\n\.\…\s])\s*(?:\.\.\.+|\…)\s*([^\n\.\…\s][^\n\.\…]*[^\n\.\…\s])')
)

# Hadith citations starting with a specific word
sh.register_extractor(
    department="hadith",
    pattern=re.compile(r'«([^«]*?(?:قال|سمعت|حدثنا|أنبأنا)[^»]*?)»')
)
```

### Step 2: Load the Rules in Your Application
```python
import asyncio
import shamla as sh

async def main():
    # Load rules dynamically from the file
    sh.load_extractors_from_file("my_custom_rules.py")
    print("Custom rules loaded dynamically!")

    async with sh.Scraper.create_scraper(headless=True) as scraper:
        page = await scraper.get_book_page("23627", 347)
        print("Extracted Departments:", list(page.departments.keys()))
        print("Poetry matched:", page.departments.get("poetry"))
        print("Hadith matched:", page.departments.get("hadith"))

if __name__ == "__main__":
    asyncio.run(main())
```
