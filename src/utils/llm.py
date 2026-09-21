"""
Model routing — Tier 1 (fast) and Tier 2 (frontier) LLM selection.

Tier 1 (Gemini Flash): intent routing, column classification, schema inference
Tier 2 (Gemini Pro): complex Q&A narrative, multi-supplier synthesis
"""

from __future__ import annotations

import os
from enum import Enum

from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()


class TaskType(str, Enum):
    """Categories of LLM tasks, mapped to model tiers."""

    # Tier 1 — fast/cheap
    INTENT_CLASSIFICATION = "intent"
    SCHEMA_INFERENCE = "schema"
    COLUMN_CLASSIFICATION = "classify"

    # Tier 2 — frontier/reasoning
    QA_SYNTHESIS = "qa"
    NARRATIVE_GENERATION = "narrative"
    ROOT_CAUSE_ANALYSIS = "root_cause"
    MULTI_SUPPLIER_COMPARISON = "comparison"


# Tier boundaries
TIER_1_TASKS = {
    TaskType.INTENT_CLASSIFICATION,
    TaskType.SCHEMA_INFERENCE,
    TaskType.COLUMN_CLASSIFICATION,
}


class ModelRouter:
    """
    Routes LLM tasks to the appropriate model tier.

    Tier 1 (fast): Gemini 2.0 Flash — intent routing, classification, schema proposals
    Tier 2 (frontier): Gemini 2.5 Pro — complex narrative, synthesis, reasoning
    """

    def __init__(
        self,
        tier1_model: str | None = None,
        tier2_model: str | None = None,
        api_key: str | None = None,
    ):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        t1 = tier1_model or os.getenv("GEMINI_TIER1_MODEL", "gemini-2.5-flash")
        t2 = tier2_model or os.getenv("GEMINI_TIER2_MODEL", "gemini-2.5-flash")

        self._tier1 = ChatGoogleGenerativeAI(
            model=t1,
            google_api_key=self.api_key,
            temperature=0.1,  # Low temp for classification tasks
            max_output_tokens=2048,
        )

        self._tier2 = ChatGoogleGenerativeAI(
            model=t2,
            google_api_key=self.api_key,
            temperature=0.3,  # Slightly higher for narrative
            max_output_tokens=4096,
        )

    def get_model(self, task_type: TaskType) -> ChatGoogleGenerativeAI:
        """Get the appropriate model for a task type."""
        if task_type in TIER_1_TASKS:
            return self._tier1
        return self._tier2

    @property
    def tier1(self) -> ChatGoogleGenerativeAI:
        """Direct access to Tier 1 model."""
        return self._tier1

    @property
    def tier2(self) -> ChatGoogleGenerativeAI:
        """Direct access to Tier 2 model."""
        return self._tier2
