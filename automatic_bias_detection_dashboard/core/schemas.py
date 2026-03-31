"""Pydantic v2 data models for the Bias Detection system."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"


class PaperType(str, Enum):
    TRADING_AGENT = "trading_agent"
    FORECASTING = "forecasting"
    FINANCIAL_QA = "financial_qa"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    BENCHMARK = "benchmark"
    PORTFOLIO = "portfolio"
    RISK_MANAGEMENT = "risk_management"
    INFORMATION_EXTRACTION = "information_extraction"
    OTHER = "other"


class PaperClassification(BaseModel):
    title: str
    paper_type: PaperType
    paper_type_reasoning: str
    methodology_summary: str
    uses_llm: bool
    uses_rag: bool
    uses_external_data: bool = Field(
        description="Whether the paper uses external time-varying data (news, web search, retrieval, filings, APIs)"
    )
    uses_backtesting: bool
    evaluation_period: Optional[str] = None
    models_used: list[str] = Field(default_factory=list)
    datasets_used: list[str] = Field(default_factory=list)


class ChecklistItemResult(BaseModel):
    """Result for one of the 12 checklist items."""

    item_id: str = Field(description="e.g. '1.1', '3.2', '5.1'")
    item_name: str = Field(description="e.g. 'Parametric Knowledge Cutoff Disclosure'")
    section: str = Field(description="e.g. 'Temporal Sanitation'")
    sin: str = Field(description="e.g. 'Look-Ahead Bias'")
    question: str = Field(description="The checklist question")
    verdict: Verdict
    description: str = Field(
        description="Detailed explanation: what the LLM found in the paper regarding this item"
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Direct quotes or section references from the paper",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable bullet points if verdict is not pass",
    )


class ChecklistEvaluation(BaseModel):
    """LLM output: evaluation of all 12 checklist items."""

    items: list[ChecklistItemResult] = Field(
        min_length=12, max_length=12, description="Exactly 12 checklist item results"
    )


class BiasReport(BaseModel):
    """Complete assessment report."""

    model_config = {"protected_namespaces": ()}

    report_id: str
    paper_title: str
    classification: PaperClassification
    analysis_timestamp: datetime
    model_used: str
    overall_verdict: Verdict
    checklist_score: float = Field(
        ge=0.0, le=1.0, description="Fraction of applicable items that pass"
    )
    items: list[ChecklistItemResult] = Field(
        min_length=12, max_length=12, description="The 12 checklist results"
    )
    executive_summary: str
    cross_check_interactions: list[str] = Field(default_factory=list)


class ExtractedPaper(BaseModel):
    full_text: str
    title: Optional[str] = None
    abstract: Optional[str] = None
    sections: dict[str, str] = Field(default_factory=dict)
    page_count: int
    char_count: int
