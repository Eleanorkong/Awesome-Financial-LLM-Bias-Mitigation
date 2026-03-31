"""Extract structured text from uploaded PDF papers using PyMuPDF.

Converts PDF to clean markdown for better LLM comprehension.
"""

from __future__ import annotations

import re

import fitz  # PyMuPDF

from core.schemas import ExtractedPaper


def extract_paper(pdf_bytes: bytes) -> ExtractedPaper:
    """Extract text from PDF and convert to clean markdown."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: list[str] = []
    for page in doc:
        pages.append(page.get_text("text"))
    doc.close()

    raw_text = "\n".join(pages)
    page_count = len(pages)

    title = _detect_title(pages[0] if pages else "")
    abstract = _detect_abstract(raw_text)
    sections = _detect_sections(raw_text)

    # Build clean markdown
    markdown = _to_markdown(title, abstract, sections, raw_text)

    return ExtractedPaper(
        full_text=markdown,
        title=title,
        abstract=abstract,
        sections=sections,
        page_count=page_count,
        char_count=len(markdown),
    )


def _clean_text(text: str) -> str:
    """Clean raw PDF text: remove line numbers, fix hyphenation, normalize whitespace."""
    # Remove line numbers (e.g., 001, 002, ... 999)
    text = re.sub(r"(?m)^\d{3}$", "", text)
    # Remove page headers/footers (common patterns)
    text = re.sub(r"(?m)^Confidential.*$", "", text)
    text = re.sub(r"(?m)^For ICML.*$", "", text)
    # Fix hyphenated line breaks (e.g., "evalua-\ntion" -> "evaluation")
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Normalize spaces (but keep paragraph breaks)
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            cleaned_lines.append("")
        else:
            # Collapse multiple spaces within a line
            cleaned_lines.append(re.sub(r"  +", " ", line))
    return "\n".join(cleaned_lines).strip()


def _to_markdown(
    title: str | None,
    abstract: str | None,
    sections: dict[str, str],
    raw_text: str,
) -> str:
    """Convert extracted paper parts into clean markdown."""
    parts: list[str] = []

    # Title
    if title:
        parts.append(f"# {title}\n")

    # Abstract
    if abstract:
        parts.append(f"## Abstract\n\n{abstract}\n")

    # Sections
    if sections:
        for heading, body in sections.items():
            # Determine heading level from numbering
            num_match = re.match(r"^(\d+(?:\.\d+)?)\.", heading)
            if num_match:
                depth = num_match.group(1).count(".") + 2  # "1." -> ##, "2.1." -> ###
            else:
                depth = 2
            prefix = "#" * min(depth, 4)

            clean_body = _clean_text(body)
            # Join short lines into paragraphs (PDF often breaks mid-sentence)
            clean_body = _join_paragraphs(clean_body)

            parts.append(f"{prefix} {heading}\n\n{clean_body}\n")
    elif not abstract:
        # No sections detected, use cleaned raw text
        parts.append(_clean_text(raw_text))

    return "\n".join(parts)


def _join_paragraphs(text: str) -> str:
    """Join lines that were broken mid-sentence by PDF column layout."""
    lines = text.split("\n")
    result: list[str] = []
    buffer = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Blank line = paragraph break
            if buffer:
                result.append(buffer)
                buffer = ""
            result.append("")
            continue

        # If buffer ends mid-sentence (lowercase, no period) and line starts lowercase,
        # join them
        if buffer and not buffer.endswith((".","!","?",":","。")) and stripped[0].islower():
            buffer += " " + stripped
        elif buffer and len(stripped) > 20 and not stripped[0].isupper() and not re.match(r"^[\d\-\*\(\[]", stripped):
            buffer += " " + stripped
        else:
            if buffer:
                result.append(buffer)
            buffer = stripped

    if buffer:
        result.append(buffer)

    return "\n".join(result)


def _detect_title(first_page_text: str) -> str | None:
    """Detect the paper title from the first page."""
    lines = first_page_text.strip().split("\n")
    candidate_lines: list[str] = []

    for line in lines:
        cleaned = line.strip()
        if not cleaned:
            continue
        if re.match(r"^\d{3}$", cleaned):
            continue
        if len(cleaned) < 10:
            continue
        if any(
            kw in cleaned.lower()
            for kw in ["confidential", "under review", "preprint", "arxiv"]
        ):
            continue

        candidate_lines.append(cleaned)
        if len(candidate_lines) >= 3:
            break

    if not candidate_lines:
        return None

    for line in candidate_lines:
        if line.count(",") >= 2 and any(c.isupper() for c in line.split(",")[1]):
            continue
        if "university" in line.lower() or "institute" in line.lower():
            continue
        if "@" in line:
            continue
        return line

    return candidate_lines[0] if candidate_lines else None


def _detect_abstract(full_text: str) -> str | None:
    """Extract the abstract section."""
    match = re.search(
        r"(?i)\babstract\b\s*\n(.*?)(?=\n\s*(?:1[\.\s]|introduction|keywords|index terms))",
        full_text,
        re.DOTALL,
    )
    if match:
        abstract = match.group(1).strip()
        abstract = re.sub(r"\n\d{3}\n", "\n", abstract)
        abstract = re.sub(r"\s+", " ", abstract)
        if 50 < len(abstract) < 3000:
            return abstract

    match = re.search(
        r"(?i)abstract[:\s]*(.*?)(?:1\.\s*introduction|1\s+introduction)",
        full_text,
        re.DOTALL,
    )
    if match:
        abstract = match.group(1).strip()
        abstract = re.sub(r"\s+", " ", abstract)
        if 50 < len(abstract) < 3000:
            return abstract

    return None


def _detect_sections(full_text: str) -> dict[str, str]:
    """Detect and extract paper sections."""
    sections: dict[str, str] = {}

    pattern = re.compile(
        r"^\s*(\d+(?:\.\d+)?)\s*\.?\s+([A-Z][^\n]{3,80})\s*$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(full_text))

    if not matches:
        return sections

    for i, match in enumerate(matches):
        section_num = match.group(1).strip()
        section_title = match.group(2).strip()
        section_key = f"{section_num}. {section_title}"

        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        section_text = full_text[start:end].strip()
        section_text = re.sub(r"\n\d{3}\n", "\n", section_text)
        sections[section_key] = section_text

    return sections


def truncate_for_llm(paper: ExtractedPaper, max_chars: int = 60_000) -> str:
    """Truncate paper markdown to fit within LLM context limits.

    If paper is already under the limit, returns full markdown.
    Otherwise prioritizes abstract and key sections.
    """
    if paper.char_count <= max_chars:
        return paper.full_text

    parts: list[str] = []
    remaining = max_chars

    if paper.title:
        header = f"# {paper.title}\n\n"
        parts.append(header)
        remaining -= len(header)

    if paper.abstract:
        ab = f"## Abstract\n\n{paper.abstract}\n\n"
        parts.append(ab)
        remaining -= len(ab)

    priority_keywords = [
        "method", "experiment", "evaluat", "result", "data", "model",
        "approach", "framework", "system", "implement", "setup",
        "backtest", "trading", "forecast", "portfolio",
    ]

    priority_sections: list[tuple[str, str]] = []
    other_sections: list[tuple[str, str]] = []

    for name, text in paper.sections.items():
        clean = _clean_text(text)
        clean = _join_paragraphs(clean)
        if any(kw in name.lower() for kw in priority_keywords):
            priority_sections.append((name, clean))
        else:
            other_sections.append((name, clean))

    for name, text in priority_sections + other_sections:
        chunk = f"## {name}\n\n{text}\n\n"
        if len(chunk) <= remaining:
            parts.append(chunk)
            remaining -= len(chunk)
        elif remaining > 500:
            parts.append(chunk[:remaining] + "\n\n[...truncated]")
            break

    return "".join(parts)
