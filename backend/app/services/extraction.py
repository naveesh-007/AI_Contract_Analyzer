"""
Text extraction service.

Supports:
  - PDF  via pdfplumber (page-by-page)
  - TXT  line-by-line with character offsets
"""
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ExtractedPage:
    """Represents text extracted from one page."""

    page_number: int      # 1-indexed
    text: str
    char_start: int | None
    char_end: int | None


class ExtractionError(RuntimeError):
    """Raised when text extraction fails."""


def extract_pdf(file_path: Path) -> list[ExtractedPage]:
    """
    Extract text from a PDF file page-by-page using pdfplumber.

    Returns one ExtractedPage per PDF page.
    Character offsets represent positions within the concatenated
    full-document string (pages joined by newline).
    """
    import pdfplumber  # local import so non-PDF paths don't pay the import cost

    pages: list[ExtractedPage] = []
    char_cursor = 0

    try:
        with pdfplumber.open(file_path) as pdf:
            if len(pdf.pages) == 0:
                raise ExtractionError("PDF has no pages.")

            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                text = text.strip()

                char_start = char_cursor
                char_end = char_cursor + len(text)
                char_cursor = char_end + 1  # +1 for newline separator

                pages.append(
                    ExtractedPage(
                        page_number=i,
                        text=text,
                        char_start=char_start,
                        char_end=char_end,
                    )
                )

    except ExtractionError:
        raise
    except Exception as exc:
        logger.exception("PDF extraction failed for %s", file_path)
        raise ExtractionError(f"Could not extract text from PDF: {exc}") from exc

    return pages


def extract_txt(file_path: Path) -> list[ExtractedPage]:
    """
    Extract text from a TXT file.

    Treats the entire file as a single "page" and records char offsets
    for the full text. If the file is empty, returns one empty page.
    """
    try:
        raw = file_path.read_bytes()
        # Try UTF-8 first, fall back to latin-1
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")

        text = text.strip()

        return [
            ExtractedPage(
                page_number=1,
                text=text,
                char_start=0,
                char_end=len(text),
            )
        ]

    except Exception as exc:
        logger.exception("TXT extraction failed for %s", file_path)
        raise ExtractionError(f"Could not read TXT file: {exc}") from exc


def extract_document(file_path: Path, file_type: str) -> list[ExtractedPage]:
    """
    Dispatch to the correct extractor based on file_type ('pdf' or 'txt').
    """
    if file_type == "pdf":
        return extract_pdf(file_path)
    elif file_type == "txt":
        return extract_txt(file_path)
    else:
        raise ExtractionError(f"Unsupported file type for extraction: {file_type}")
