from dataclasses import dataclass

@dataclass
class Chapter:
    """Represents a chapter or section in the book's Table of Contents."""
    title: str
    url: str
    page_number: int
    depth: int
