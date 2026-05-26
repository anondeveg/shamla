# Shamla Library Documentation

Welcome to the official documentation for the **Shamla Library (`shamla`)**, a lightweight, robust, and extensible Python library designed for scraping, downloading, extracting, and exporting Islamic books from the المكتبة الشاملة (Shamela.ws).

---

## 🌟 Key Features

* **Browser-based Scraper**: Automated headless scraper powered by Chromium/Google Chrome.
* **Zero-Dependency Offline Mode**: High-performance parser that runs on offline HTML structures.
* **Heuristic Custom Quote & Poetry Extraction**: Fully customizable patterns and extractors.
* **Pluggable Exporter System**: Easily export scraped books into relational databases (SQLite) or custom data formats (JSON, CSV).
* **Multi-threaded Concurrency**: Concurrently download or export large books in batches.

---

## 📚 Table of Contents

### [Chapter 1: Getting Started](file:///home/anondev/ai-lab/shamla/docs/getting_started.md)
* Learn about installation, prerequisites (Chromium binary detection), and a runnable quick-start script.

### [Chapter 2: Scrapers & Offline Mode](file:///home/anondev/ai-lab/shamla/docs/scrapers.md)
* Deep dive into `Scraper`, `BookDownloader`, and `LocalScraper` (offline local scraping).

### [Chapter 3: Custom Text & Poetry Extraction](file:///home/anondev/ai-lab/shamla/docs/extraction.md)
* Configure custom heuristic patterns, define scraper departments, and dynamically load rules from external files.

### [Chapter 4: Data Exporters](file:///home/anondev/ai-lab/shamla/docs/exporters.md)
* Standardize database output using `BookExporter`, set up SQLite database stores, and write your own custom data exporters.

### [Chapter 5: Advanced Performance & Concurrency](file:///home/anondev/ai-lab/shamla/docs/performance.md)
* Scale up downloading speeds using async concurrent batching safely.

### [Chapter 6: Developer & API Reference](file:///home/anondev/ai-lab/shamla/docs/api_reference.md)
* Comprehensive overview of model classes, schemas, and test suite details.
