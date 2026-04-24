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
CLEAN_SCRIPT = PROJECT_ROOT / "scripts" / "clean_draft.py"

# Each pair below is (raw export, expected cleaned output) for one draft year.
RAW_CSV = PROJECT_ROOT / "data" / "2025_Pre-season_Pre-season.csv"
CLEANED_CSV = PROJECT_ROOT / "data" / "2025_Pre-season_Pre-season-cleaned.csv"

RAW_CSV_2021 = PROJECT_ROOT / "data" / "2021_Ballers_draft.csv"
CLEANED_CSV_2021 = PROJECT_ROOT / "data" / "2021_Ballers_draft-cleaned.csv"

RAW_CSV_2020 = PROJECT_ROOT / "data" / "2020_Ballers_draft.csv"
CLEANED_CSV_2020 = PROJECT_ROOT / "data" / "2020_Ballers_draft-cleaned.csv"


def _run_cleaner(raw: Path, cleaned: Path) -> Path:
    """Invoke clean_draft.py as a subprocess and return the path to the cleaned CSV.

    We run the script as a subprocess rather than importing and calling main()
    directly so the test exercises the real command-line entry point, including
    argument parsing and sys.exit behaviour.
    """
    result = subprocess.run(
        [sys.executable, str(CLEAN_SCRIPT), str(raw)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"clean_draft.py failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert cleaned.exists(), f"Cleaned CSV was not created at {cleaned}"
    return cleaned


# All fixtures below use scope="session" so the cleaner script and CSV loads
# happen only once per test run, not once per test function.  This keeps the
# suite fast even when dozens of BDD scenarios share the same data.

@pytest.fixture(scope="session")
def raw_csv_path() -> Path:
    """Path to the raw 2025 draft CSV."""
    assert RAW_CSV.exists(), f"Raw CSV not found: {RAW_CSV}"
    return RAW_CSV


@pytest.fixture(scope="session")
def cleaned_csv_path() -> Path:
    """Run clean_draft.py on the 2025 file once per session."""
    assert RAW_CSV.exists(), f"Raw CSV not found: {RAW_CSV}"
    return _run_cleaner(RAW_CSV, CLEANED_CSV)


@pytest.fixture(scope="session")
def cleaned_df(cleaned_csv_path: Path) -> pd.DataFrame:
    """The cleaned 2025 draft DataFrame, loaded once per session."""
    return pd.read_csv(cleaned_csv_path)


@pytest.fixture(scope="session")
def cleaned_csv_path_2021() -> Path:
    """Run clean_draft.py on the 2021 file once per session."""
    assert RAW_CSV_2021.exists(), f"Raw CSV not found: {RAW_CSV_2021}"
    return _run_cleaner(RAW_CSV_2021, CLEANED_CSV_2021)


@pytest.fixture(scope="session")
def cleaned_df_2021(cleaned_csv_path_2021: Path) -> pd.DataFrame:
    """The cleaned 2021 draft DataFrame, loaded once per session."""
    return pd.read_csv(cleaned_csv_path_2021)


@pytest.fixture(scope="session")
def cleaned_csv_path_2020() -> Path:
    """Run clean_draft.py on the 2020 file once per session."""
    assert RAW_CSV_2020.exists(), f"Raw CSV not found: {RAW_CSV_2020}"
    return _run_cleaner(RAW_CSV_2020, CLEANED_CSV_2020)


@pytest.fixture(scope="session")
def cleaned_df_2020(cleaned_csv_path_2020: Path) -> pd.DataFrame:
    """The cleaned 2020 draft DataFrame, loaded once per session."""
    return pd.read_csv(cleaned_csv_path_2020)
