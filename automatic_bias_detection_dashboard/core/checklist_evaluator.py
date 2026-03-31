"""Evaluate a paper against the 12-item structural validity checklist.

Single LLM call for all 12 items — sends paper text only once.
"""

from __future__ import annotations

from core.llm_client import structured_completion
from core.prompts.checklist_prompt import (
    CODE_SECTION_TEMPLATE,
    NO_CODE_SECTION,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)
from core.schemas import ChecklistEvaluation, PaperClassification


async def evaluate_checklist(
    paper_text: str,
    classification: PaperClassification,
    model: str,
    code_text: str | None = None,
) -> ChecklistEvaluation:
    """Evaluate all 12 checklist items in a single LLM call.

    Sends the paper text once, asks the LLM to evaluate all 12 items.
    """
    if code_text and code_text.strip():
        code_section = CODE_SECTION_TEMPLATE.format(code_text=code_text)
    else:
        code_section = NO_CODE_SECTION

    user_prompt = USER_PROMPT_TEMPLATE.format(
        paper_type=classification.paper_type.value,
        uses_llm=classification.uses_llm,
        uses_external_data=classification.uses_external_data,
        uses_backtesting=classification.uses_backtesting,
        evaluation_period=classification.evaluation_period or "Not specified",
        models_used=", ".join(classification.models_used) or "Not specified",
        paper_text=paper_text,
        code_section=code_section,
    )

    return await structured_completion(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        response_model=ChecklistEvaluation,
    )
