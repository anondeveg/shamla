from dataclasses import dataclass, field

@dataclass
class Footnote:
    """Represents a single footnote on a page."""
    number: str
    content: str

@dataclass
class Page_data:
    """Represents structured text and annotations on a single book page."""
    book_id: str
    page_number: int
    part_number: str
    headings: list[str]
    paragraphs: list[str]
    footnotes: list[Footnote]
    citations: list[str]
    departments: dict[str, list[str]] = field(default_factory=dict)
