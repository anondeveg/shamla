# Chapter 6: API Reference

This chapter documents the key model schemas and developer testing instructions for the `shamla` library.

---

## 🗃️ 1. Data Models Schema

The following models represent the structured database layout of parsed book files. All models inherit from `dataclasses.dataclass`.

### 📖 `Book_data` (Metadata)
Represents the main attributes of a book index.

| Field Name | Type | Description |
|---|---|---|
| `book_id` | `str` | Unique identification number of the book. |
| `title` | `str` | Title of the book. |
| `author_name` | `str` | Full name of the author. |
| `author_page` | `str` | URL pointing to the author's biography on Shamela. |
| `book_description` | `str` | Detailed textual index description. |
| `publisher` | `str` | Publisher name (optional). |
| `book_print` | `str` | Print edition details (optional). |
| `volumes` | `int` | Total volume/part count (defaults to `1`). |
| `is_equal_to_print` | `bool` | Matches the official printed pages layout. |

---

### 📂 `Chapter` (Table of Contents)
Represents a single nested chapter heading within the book's index.

| Field Name | Type | Description |
|---|---|---|
| `title` | `str` | Title text of the section. |
| `url` | `str` | Path link pointing to the starting page of the section. |
| `page_number` | `int` | Page index integer. |
| `depth` | `int` | Hierarchy depth level (e.g. `0` for Part, `1` for Surah, etc.). |

---

### 📄 `Page_data` (Page Content)
Represents the full contents extracted from a single book page.

| Field Name | Type | Description |
|---|---|---|
| `book_id` | `str` | Book ID owner. |
| `page_number` | `int` | Page sequence number. |
| `part_number` | `str` | Volume number (e.g. `الجزء الأول`). |
| `headings` | `list[str]` | Titles and headers present on the page. |
| `paragraphs` | `list[str]` | Main paragraphs text content. |
| `footnotes` | `list[Footnote]` | Footnotes list objects. |
| `citations` | `list[str]` | Text quotes matching standard and custom extraction rules. |
| `departments` | `dict[str, list[str]]` | Map categorization of custom extraction verses (e.g. `{"poetry": [...]}`). |

---

### 📝 `Footnote` (Page Footnote)
Represents a single footnotes item.

| Field Name | Type | Description |
|---|---|---|
| `number` | `str` | Footnote identification tag (e.g., `١` or `[1]`). |
| `content` | `str` | Footnote explanation content text. |

---

## 🧪 2. Running Tests & Code Coverage

The library target is **100% test coverage**. You can verify and run tests inside a configured virtual environment.

### Run Tests
```bash
# Run pytest with the src/ path configured in PYTHONPATH
PYTHONPATH=src .venv/bin/pytest
```

### Run Tests with Coverage Report
To execute test validations and verify coverage metrics for all modules:
```bash
PYTHONPATH=src .venv/bin/pytest --cov=src --cov-report=term-missing
```
