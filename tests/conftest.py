"""Pytest fixtures shared across all tests."""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def simple_df() -> pd.DataFrame:
    """A small DataFrame with intentional issues for rule testing."""
    return pd.DataFrame(
        {
            "Titre": [
                "Introduction ",    # trailing space
                "  Méthodes",       # leading space
                "Histoire  médiévale",  # double space
                "Analyse",
                "Analyse",          # duplicate value
                "N/A",              # pseudo-missing
                "Corpus\u200b",     # invisible char
                "\u201cCognition\u201d",  # curly quotes
            ],
            "Date": [
                "2021-03-15",
                "2020-11-01",
                "not-a-date",       # soft typing outlier
                "2019-07-22",
                "2018-05-10",
                "2021-09-01",
                "2022-01-30",
                "2023-02-28",
            ],
            "Type": [
                "Article",
                "Rapport",
                "Article",
                "Thèse",
                "Artcile",          # near-duplicate typo
                "Article",
                "Rapport",
                "Article",
            ],
        }
    )


@pytest.fixture
def empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["A", "B"])


@pytest.fixture
def dup_rows_df() -> pd.DataFrame:
    data = {"A": ["x", "x", "y"], "B": ["1", "1", "2"]}
    return pd.DataFrame(data)
