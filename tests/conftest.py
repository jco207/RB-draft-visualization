"""
Shared pytest fixtures for the draft-visualization test suite.

Fixtures here are available to all test files without explicit import.
"""

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
RAW_CSV = PROJECT_ROOT / "data" / "2025_Pre-season_Pre-season.csv"
CLEANED_CSV = PROJECT_ROOT / "data" / "2025_Pre-season_Pre-season-cleaned.csv"
CLEAN_SCRIPT = PROJECT_ROOT / "scripts" / "clean_draft.py"


@pytest.fixture(scope="session")
def raw_csv_path() -> Path:
    """Path to the raw draft CSV (must exist in the project root)."""
    assert RAW_CSV.exists(), f"Raw CSV not found: {RAW_CSV}"
    return RAW_CSV


@pytest.fixture(scope="session")
def cleaned_csv_path() -> Path:
    """
    Run clean_draft.py once per test session and return the path to the
    resulting cleaned CSV. Uses RAW_CSV directly to avoid fixture-scope
    conflicts with function-scoped pytest-bdd step fixtures.
    """
    assert RAW_CSV.exists(), f"Raw CSV not found: {RAW_CSV}"
    result = subprocess.run(
        [sys.executable, str(CLEAN_SCRIPT), str(RAW_CSV)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"clean_draft.py failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert CLEANED_CSV.exists(), f"Cleaned CSV was not created at {CLEANED_CSV}"
    return CLEANED_CSV


@pytest.fixture(scope="session")
def cleaned_df(cleaned_csv_path: Path) -> pd.DataFrame:
    """The cleaned draft DataFrame, loaded once per session."""
    return pd.read_csv(cleaned_csv_path)
