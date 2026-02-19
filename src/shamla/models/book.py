from dataclasses import dataclass


@dataclass
class Book_data:
    "A class for holding all Book info"

    author_name: str
    author_page: str
    title: str
    book_description: str
    publisher: str
    book_print: str
    volumes: int
    is_equal_to_print: bool
