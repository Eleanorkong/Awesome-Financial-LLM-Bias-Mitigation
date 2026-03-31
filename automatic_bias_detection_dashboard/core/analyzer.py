"""Analysis orchestrator: extract PDF, classify, evaluate checklist."""

from __future__ import annotations

from typing import AsyncGenerator

from core.checklist_evaluator import evaluate_checklist
from core.code_extractor import extract_code_from_github
from core.paper_classifier import classify_paper
from core.pdf_extractor import extract_paper, truncate_for_llm
from core.report_generator import generate_report


async def analyze_paper_streaming(
    pdf_bytes: bytes,
    model: str,
    repo_url: str | None = None,
) -> AsyncGenerator[dict, None]:
    """Streaming analysis with progress events.

    Sends paper to LLM once for all 12 items.
    """
    extracted = extract_paper(pdf_bytes)
    paper_text = truncate_for_llm(extracted)
    yield {"event": "extract", "status": "done"}

    classification = await classify_paper(paper_text, model)
    yield {"event": "classify", "status": "done"}

    # Fetch code if repo provided
    code_text = None
    if repo_url:
        code_text = await extract_code_from_github(repo_url)

    # Signal that evaluation is starting (UI will animate sections)
    yield {"event": "evaluate", "status": "running"}

    # Single LLM call for all 12 items
    evaluation = await evaluate_checklist(paper_text, classification, model, code_text)

    yield {"event": "evaluate", "status": "done"}

    report = generate_report(classification, evaluation.items, model)
    yield {"event": "report", "data": report.model_dump(mode="json")}
