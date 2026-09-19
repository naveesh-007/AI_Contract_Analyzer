"""
Clause Extraction Service — identifies sections, headings, and contractual clauses
from extracted page text without altering or inventing text.
"""
import logging
import re
from dataclasses import dataclass
from typing import Optional

from app.models.document import DocumentPage

logger = logging.getLogger(__name__)


@dataclass
class ExtractedCandidateClause:
    """Represents a candidate clause identified from raw document text."""

    section_number: Optional[str]
    section_title: Optional[str]
    clause_text: str
    page_number: Optional[int]
    char_start: Optional[int]
    char_end: Optional[int]


# Regex patterns to detect section headers
# Examples:
#   "1. TERM AND TERMINATION"
#   "Section 4. Indemnification"
#   "Article III - Confidentiality"
#   "8.2 Termination for Cause:"
#   "1.1 Scope of Work."
SECTION_HEADER_RE = re.compile(
    r"^(?:(?:Section|Article|Clause)\s+)?(\d+(?:\.\d+)*|[IVXLCDM]+)[\.\:\-\s]+([^\n\r]+)?$",
    re.IGNORECASE,
)

# Pattern to detect uppercase/title-case standalone headings
HEADING_RE = re.compile(r"^[A-Z0-9\s,\-\:\(\)\/]{3,80}$")


def extract_clauses_from_pages(
    pages: list[DocumentPage],
) -> list[ExtractedCandidateClause]:
    """
    Parses document pages to detect structured contractual sections and clauses.
    Preserves exact character offsets and verbatim text.
    """
    candidates: list[ExtractedCandidateClause] = []

    for page in pages:
        page_text = page.text or ""
        if not page_text.strip():
            continue

        page_num = page.page_number
        page_char_offset = page.char_start or 0

        # Split text into logical paragraph chunks while tracking character positions
        # Find paragraphs separated by 2 or more newlines
        paragraph_splits = re.split(r"(\n\s*\n+)", page_text)

        current_idx = 0
        current_section_num: Optional[str] = None
        current_section_title: Optional[str] = None

        i = 0
        while i < len(paragraph_splits):
            chunk = paragraph_splits[i]
            chunk_start = page_char_offset + current_idx
            chunk_end = chunk_start + len(chunk)
            current_idx += len(chunk)
            i += 1

            trimmed = chunk.strip()
            if not trimmed:
                continue

            # Check if this paragraph is a standalone heading or section header
            lines = [l.strip() for l in trimmed.split("\n") if l.strip()]
            first_line = lines[0] if lines else ""

            # Check for decorative line under heading (e.g. === or ---)
            if len(lines) >= 2 and re.match(r"^[=\-_]{3,}$", lines[1]):
                first_line = lines[0]

            header_match = SECTION_HEADER_RE.match(first_line)

            if header_match and len(lines) == 1:
                # Standalone section header: "1. TERM AND TERMINATION"
                current_section_num = header_match.group(1).strip()
                title_part = header_match.group(2)
                current_section_title = title_part.strip() if title_part else None
                continue
            elif HEADING_RE.match(first_line) and len(lines) == 1 and not first_line.endswith("."):
                # Standalone all-caps title e.g. "MUTUAL INDEMNIFICATION"
                current_section_title = first_line
                current_section_num = None
                continue

            # Check if the paragraph begins with inline section number
            # e.g. "8.2 Termination. The Company may terminate this Agreement immediately..."
            inline_match = re.match(
                r"^(?:(?:Section|Article|Clause)\s+)?(\d+(?:\.\d+)*|[IVXLCDM]+)[\.\:\-\s]+([A-Za-z\s]{2,40})?[\.\:\-]\s*([\s\S]+)$",
                trimmed,
                re.IGNORECASE,
            )

            sec_num = current_section_num
            sec_title = current_section_title
            clause_content = trimmed

            if inline_match:
                sec_num = inline_match.group(1).strip()
                inline_title = inline_match.group(2)
                if inline_title and len(inline_title.strip()) > 1:
                    sec_title = inline_title.strip()
                # Use entire trimmed paragraph as clause text to preserve full context
                clause_content = trimmed
            elif header_match and len(lines) > 1:
                sec_num = header_match.group(1).strip()
                title_part = header_match.group(2)
                if title_part:
                    sec_title = title_part.strip()

            # Ignore non-contractual small fragments (e.g. page numbers alone like "Page 1 of 5")
            if re.match(r"^Page \d+(?: of \d+)?$", trimmed, re.IGNORECASE):
                continue
            if len(trimmed) < 15 and not sec_num:
                # Skip trivial noise lines
                continue

            candidates.append(
                ExtractedCandidateClause(
                    section_number=sec_num,
                    section_title=sec_title,
                    clause_text=clause_content,
                    page_number=page_num,
                    char_start=chunk_start,
                    char_end=chunk_end,
                )
            )

    # Fallback: if no structured paragraphs found but document has text, wrap full page text
    if not candidates and any(p.text.strip() for p in pages):
        for p in pages:
            if p.text.strip():
                candidates.append(
                    ExtractedCandidateClause(
                        section_number="1",
                        section_title="General Provisions",
                        clause_text=p.text.strip(),
                        page_number=p.page_number,
                        char_start=p.char_start,
                        char_end=p.char_end,
                    )
                )

    return candidates
