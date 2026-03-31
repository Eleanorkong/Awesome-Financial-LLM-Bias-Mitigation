"""Paper type classifier using LLM analysis."""

from __future__ import annotations

from core.llm_client import structured_completion
from core.prompts.classification_prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from core.schemas import PaperClassification


async def classify_paper(paper_text: str, model: str) -> PaperClassification:
    """Classify a paper's type and extract key methodology details."""
    return await structured_completion(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=USER_PROMPT_TEMPLATE.format(paper_text=paper_text),
        response_model=PaperClassification,
    )
