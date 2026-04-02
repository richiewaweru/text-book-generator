from .cover import generate_cover_page
from .toc import generate_toc
from .answers import generate_answer_key
from .assembly import merge_pdfs, add_page_numbers, add_metadata

__all__ = [
    "generate_cover_page",
    "generate_toc",
    "generate_answer_key",
    "merge_pdfs",
    "add_page_numbers",
    "add_metadata",
]
