"""Typed configuration + run summary — Pydantic v2 models.

Two models with different roles:
  - Settings:    config (same every run; loaded at module init)
  - RunSummary:  observation (one row per execution; produced at run end)
"""
from __future__ import annotations
from pathlib import Path

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Runtime configuration. Validated at construction."""

    questions_csv: Path  = Path("data/questions.csv")
    results_json:  Path  = Path("results.json")
    results_db:    Path  = Path("results.db")
    batch_size:    int   = Field(5,   gt=0, le=20)
    fail_rate:     float = Field(0.0, ge=0.0, le=1.0)
    model:         str   = "gpt-4o-mini"
    use_fake:      bool  = False
    user_temperature: int = 1
    no_of_choices:  int = 1
    user_seed: int = 42
    PRICING: dict = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.150, "output": 0.600},
        "o1-preview": {"input": 15.00, "output": 60.00},
    }


class RunSummary(BaseModel):
    """One row per pipeline execution. Persisted to the `runs` table."""

    started_at:       float
    elapsed_seconds:  float = Field(ge=0.0)
    n_questions:      int   = Field(ge=0)
    n_succeeded:      int   = Field(ge=0)
    n_retries_total:  int   = Field(ge=0)
    total_cost_usd:   float = Field(ge=0.0)
    fail_rate:        float = Field(ge=0.0, le=1.0)
    use_fake:         bool
