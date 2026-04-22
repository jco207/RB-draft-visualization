"""
Step definitions for clean_draft_formats.feature.

Tests clean_draft.py against Format B (2021, flat pre-cleaned) and
Format C (2020, 5-col alternating) CSV files.
"""

from pathlib import Path

import pandas as pd
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

FEATURE_FILE = Path(__file__).parent.parent / "features" / "clean_draft_formats.feature"
scenarios(str(FEATURE_FILE))

PROJECT_ROOT = Path(__file__).parent.parent.parent
RAW_CSV_2021 = PROJECT_ROOT / "data" / "2021_Ballers_draft.csv"
RAW_CSV_2020 = PROJECT_ROOT / "data" / "2020_Ballers_draft.csv"

EXPECTED_COLUMNS = [
    "Round", "Pick", "Pick-Num", "Team", "Player", "Position",
    "Keeper", "Starred", "Elapsed Time", "Rank", "Total Fpts", "Active Fpts",
]
VALID_POSITIONS = {"QB", "RB", "WR", "TE", "K", "DEF", "DST", ""}


# ---------------------------------------------------------------------------
# Background
# ---------------------------------------------------------------------------

@given("the 2021 draft CSV exists")
def step_2021_csv_exists() -> None:
    assert RAW_CSV_2021.exists(), f"Raw CSV not found: {RAW_CSV_2021}"


@given("the 2020 draft CSV exists")
def step_2020_csv_exists() -> None:
    assert RAW_CSV_2020.exists(), f"Raw CSV not found: {RAW_CSV_2020}"


# ---------------------------------------------------------------------------
# When steps (trigger fixture evaluation)
# ---------------------------------------------------------------------------

@when("the cleaning script is run on the 2021 CSV")
def step_run_cleaner_2021(cleaned_csv_path_2021: Path) -> None:
    assert cleaned_csv_path_2021.exists()


@when("the cleaning script is run on the 2020 CSV")
def step_run_cleaner_2020(cleaned_csv_path_2020: Path) -> None:
    assert cleaned_csv_path_2020.exists()


# ---------------------------------------------------------------------------
# Shared df fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def df_2021(cleaned_df_2021: pd.DataFrame) -> pd.DataFrame:
    return cleaned_df_2021


@pytest.fixture
def df_2020(cleaned_df_2020: pd.DataFrame) -> pd.DataFrame:
    return cleaned_df_2020


# ---------------------------------------------------------------------------
# Then steps — 2021 (Format B)
# ---------------------------------------------------------------------------

@then("the 2021 cleaned CSV contains all 12 expected columns")
def step_2021_columns(df_2021: pd.DataFrame) -> None:
    missing = [c for c in EXPECTED_COLUMNS if c not in df_2021.columns]
    assert not missing, f"2021 cleaned CSV missing columns: {missing}"


@then("the 2021 cleaned CSV has empty Rank values")
def step_2021_rank_empty(df_2021: pd.DataFrame) -> None:
    assert df_2021["Rank"].isna().all(), "Expected all Rank values to be NaN for Format B"


@then("the 2021 cleaned CSV has empty Total Fpts values")
def step_2021_total_fpts_empty(df_2021: pd.DataFrame) -> None:
    assert df_2021["Total Fpts"].isna().all(), "Expected all Total Fpts to be NaN for Format B"


@then("the 2021 cleaned CSV has empty Active Fpts values")
def step_2021_active_fpts_empty(df_2021: pd.DataFrame) -> None:
    assert df_2021["Active Fpts"].isna().all(), "Expected all Active Fpts to be NaN for Format B"


@then(parsers.parse("round {round:d} pick {pick:d} in the 2021 CSV has Pick-Num {expected:d}"))
def step_2021_pick_num(df_2021: pd.DataFrame, round: int, pick: int, expected: int) -> None:
    row = df_2021[(df_2021["Round"] == round) & (df_2021["Pick"] == pick)]
    assert not row.empty, f"No row for Round {round} Pick {pick} in 2021 CSV"
    actual = int(row.iloc[0]["Pick-Num"])
    assert actual == expected, f"Round {round} Pick {pick}: expected Pick-Num {expected}, got {actual}"


@then("the 2021 cleaned CSV Position column contains only recognised positions")
def step_2021_valid_positions(df_2021: pd.DataFrame) -> None:
    unique = set(df_2021["Position"].fillna("").astype(str).unique())
    invalid = unique - VALID_POSITIONS
    assert not invalid, f"2021 CSV: unexpected position values: {invalid}"


@then("no Player value in the 2021 cleaned CSV starts with an asterisk")
def step_2021_no_asterisk(df_2021: pd.DataFrame) -> None:
    hits = df_2021[df_2021["Player"].astype(str).str.startswith("*")]
    assert hits.empty, f"2021 CSV: players starting with '*': {hits['Player'].tolist()}"


# ---------------------------------------------------------------------------
# Then steps — 2020 (Format C)
# ---------------------------------------------------------------------------

@then("the 2020 cleaned CSV contains all 12 expected columns")
def step_2020_columns(df_2020: pd.DataFrame) -> None:
    missing = [c for c in EXPECTED_COLUMNS if c not in df_2020.columns]
    assert not missing, f"2020 cleaned CSV missing columns: {missing}"


@then("the 2020 cleaned CSV has empty Rank values")
def step_2020_rank_empty(df_2020: pd.DataFrame) -> None:
    assert df_2020["Rank"].isna().all(), "Expected all Rank values to be NaN for Format C"


@then("the 2020 cleaned CSV has empty Total Fpts values")
def step_2020_total_fpts_empty(df_2020: pd.DataFrame) -> None:
    assert df_2020["Total Fpts"].isna().all(), "Expected all Total Fpts to be NaN for Format C"


@then("the 2020 cleaned CSV has empty Active Fpts values")
def step_2020_active_fpts_empty(df_2020: pd.DataFrame) -> None:
    assert df_2020["Active Fpts"].isna().all(), "Expected all Active Fpts to be NaN for Format C"


@then(parsers.parse("round {round:d} pick {pick:d} in the 2020 CSV has Pick-Num {expected:d}"))
def step_2020_pick_num(df_2020: pd.DataFrame, round: int, pick: int, expected: int) -> None:
    row = df_2020[(df_2020["Round"] == round) & (df_2020["Pick"] == pick)]
    assert not row.empty, f"No row for Round {round} Pick {pick} in 2020 CSV"
    actual = int(row.iloc[0]["Pick-Num"])
    assert actual == expected, f"Round {round} Pick {pick}: expected Pick-Num {expected}, got {actual}"


@then("the 2020 cleaned CSV Position column contains only recognised positions")
def step_2020_valid_positions(df_2020: pd.DataFrame) -> None:
    unique = set(df_2020["Position"].fillna("").astype(str).unique())
    invalid = unique - VALID_POSITIONS
    assert not invalid, f"2020 CSV: unexpected position values: {invalid}"


@then("no Player value in the 2020 cleaned CSV starts with an asterisk")
def step_2020_no_asterisk(df_2020: pd.DataFrame) -> None:
    hits = df_2020[df_2020["Player"].astype(str).str.startswith("*")]
    assert hits.empty, f"2020 CSV: players starting with '*': {hits['Player'].tolist()}"
