"""Assemble checklist results into a BiasReport."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from core.schemas import (
    BiasReport,
    ChecklistItemResult,
    PaperClassification,
    Verdict,
)


def generate_report(
    classification: PaperClassification,
    items: list[ChecklistItemResult],
    model_used: str,
) -> BiasReport:
    items = sorted(items, key=lambda i: i.item_id)

    applicable = [i for i in items if i.verdict != Verdict.NOT_APPLICABLE]
    passed = [i for i in applicable if i.verdict == Verdict.PASS]
    failed = [i for i in applicable if i.verdict == Verdict.FAIL]

    if not applicable:
        overall_verdict = Verdict.NOT_APPLICABLE
    elif len(passed) == len(applicable):
        overall_verdict = Verdict.PASS
    else:
        overall_verdict = Verdict.FAIL

    score = len(passed) / len(applicable) if applicable else 0.0

    summary = _build_summary(classification, items)
    interactions = _detect_interactions(items)

    return BiasReport(
        report_id=str(uuid.uuid4())[:8],
        paper_title=classification.title,
        classification=classification,
        analysis_timestamp=datetime.now(timezone.utc),
        model_used=model_used,
        overall_verdict=overall_verdict,
        checklist_score=round(score, 2),
        items=items,
        executive_summary=summary,
        cross_check_interactions=interactions,
    )


def _build_summary(
    cls: PaperClassification,
    items: list[ChecklistItemResult],
) -> str:
    passed = [i for i in items if i.verdict == Verdict.PASS]
    failed = [i for i in items if i.verdict == Verdict.FAIL]

    s = f"{cls.methodology_summary}\n\n"

    if failed:
        s += "Key issues identified:\n"
        for i in failed:
            s += f"\n- {i.item_name}: {i.description[:200]}"
            if i.recommendations:
                s += f"\n  Recommendation: {i.recommendations[0]}"
        s += "\n\n"

    if passed:
        s += "Strengths: " + ", ".join(i.item_name for i in passed) + "."

    return s.strip()


def _detect_interactions(items: list[ChecklistItemResult]) -> list[str]:
    interactions = []
    by_id = {i.item_id: i for i in items}

    if (
        by_id.get("1.1") and by_id["1.1"].verdict == Verdict.FAIL
        and by_id.get("2.1") and by_id["2.1"].verdict == Verdict.FAIL
    ):
        interactions.append(
            "Look-Ahead + Survivorship: Temporal leakage combined with survivor-only "
            "universe creates a doubly biased evaluation."
        )

    if (
        by_id.get("3.1") and by_id["3.1"].verdict == Verdict.FAIL
        and by_id.get("4.1") and by_id["4.1"].verdict == Verdict.FAIL
    ):
        interactions.append(
            "Narrative + Objective: Ungrounded rationales with no abstention option "
            "means the model generates confident stories without evidence."
        )

    if (
        by_id.get("1.1") and by_id["1.1"].verdict == Verdict.FAIL
        and by_id.get("5.2") and by_id["5.2"].verdict == Verdict.FAIL
    ):
        interactions.append(
            "Look-Ahead + Cost: Future information inflates gross returns, and "
            "missing cost accounting hides the gap between reported and achievable performance."
        )

    return interactions
