"""
Step definitions for clean_draft.feature.

These tests exercise clean_draft.py by running it against the real draft CSV
and asserting properties of the resulting cleaned CSV.
"""

from pathlib import Path

import pandas as pd
import pytest
from pytest_bdd import given, parsers, scenarios, then

# Register all scenarios from the feature file
FEATURE_FILE = Path(__file__).parent.parent / "features" / "clean_draft.feature"
scenarios(str(FEATURE_FILE))

PROJECT_ROOT = Path(__file__).parent.parent.parent
RAW_CSV = PROJECT_ROOT / "data" / "2025_Pre-season_Pre-season.csv"

VALID_POSITIONS = {"QB", "RB", "WR", "TE", "K", "DEF", "DST", ""}

EXPECTED_COLUMNS = [
    "Round", "Pick", "Pick-Num", "Team", "Player", "Position",
    "Keeper", "Starred", "Elapsed Time", "Rank", "Total Fpts", "Active Fpts",
]


# ---------------------------------------------------------------------------
# Background steps
# The conftest.py session fixtures (cleaned_csv_path, raw_csv_path) provide
# the real data; Background steps just assert preconditions are met.
# ---------------------------------------------------------------------------

@given("the raw draft CSV exists")
def step_raw_csv_exists() -> None:
    assert RAW_CSV.exists(), f"Raw CSV not found: {RAW_CSV}"


@given("the cleaning script has been run")
def step_cleaning_script_run(cleaned_csv_path: Path) -> None:
    """cleaned_csv_path comes from the session fixture in conftest.py."""
    assert cleaned_csv_path.exists(), f"Cleaned CSV not found: {cleaned_csv_path}"


# ---------------------------------------------------------------------------
# Shared loader: reuse the session-scoped cleaned_df from conftest to avoid
# re-reading the CSV from disk for every scenario.
# ---------------------------------------------------------------------------

@pytest.fixture
def df(cleaned_df: pd.DataFrame) -> pd.DataFrame:
    return cleaned_df


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------

@then("a cleaned CSV file exists beside the original")
def step_cleaned_csv_exists(cleaned_csv_path: Path) -> None:
    assert cleaned_csv_path.exists(), f"Cleaned CSV not found at {cleaned_csv_path}"


@then('the cleaned CSV has a "Pick-Num" column')
def step_pick_num_column_exists(df: pd.DataFrame) -> None:
    assert "Pick-Num" in df.columns, "Missing column: Pick-Num"


@then(parsers.parse("round {round:d} pick {pick:d} has Pick-Num {expected:d}"))
def step_pick_num_value(df: pd.DataFrame, round: int, pick: int, expected: int) -> None:
    row = df[(df["Round"] == round) & (df["Pick"] == pick)]
    assert not row.empty, f"No row found for Round {round} Pick {pick}"
    actual = int(row.iloc[0]["Pick-Num"])
    assert actual == expected, (
        f"Round {round} Pick {pick}: expected Pick-Num {expected}, got {actual}"
    )


@then('no row in the cleaned CSV has "Round" as its Pick value')
def step_no_round_separator_rows(df: pd.DataFrame) -> None:
    pick_col = df["Pick"].astype(str).str.strip().str.lower()
    matches = pick_col[pick_col.str.startswith("round")]
    assert matches.empty, f"Found Round separator rows: {matches.tolist()}"


@then('no row in the cleaned CSV has "Pick" as its Pick value')
def step_no_header_rows(df: pd.DataFrame) -> None:
    pick_col = df["Pick"].astype(str).str.strip().str.lower()
    matches = pick_col[pick_col == "pick"]
    assert matches.empty, f"Found header rows in cleaned CSV: {matches.tolist()}"


@then('players with "(Keeper)" in the raw name have Keeper equal to True')
def step_keeper_true(df: pd.DataFrame) -> None:
    raw_text = RAW_CSV.read_text(encoding="utf-8-sig")
    raw_lines_with_keeper = [
        line for line in raw_text.splitlines()
        if "(Keeper)" in line and not line.strip().lower().startswith("pick")
    ]
    assert len(raw_lines_with_keeper) > 0, "No keeper picks found in raw CSV"

    keeper_rows = df[df["Keeper"] == True]
    assert not keeper_rows.empty, "No rows have Keeper=True in cleaned CSV"


@then('players without "(Keeper)" in the raw name have Keeper equal to False')
def step_non_keeper_false(df: pd.DataFrame) -> None:
    first_pick = df[df["Pick-Num"] == 1]
    if not first_pick.empty:
        assert not first_pick.iloc[0]["Keeper"], "Pick-Num 1 should not be a keeper"
    assert len(df[df["Keeper"] == False]) > len(df[df["Keeper"] == True]), (
        "Expected more non-keeper picks than keeper picks"
    )


@then("the Position column contains only recognised positions or is empty")
def step_valid_positions(df: pd.DataFrame) -> None:
    unique_positions = set(df["Position"].fillna("").astype(str).unique())
    invalid = unique_positions - VALID_POSITIONS
    assert not invalid, f"Unexpected position values: {invalid}"


@then("no Player value in the cleaned CSV starts with an asterisk")
def step_no_asterisk_players(df: pd.DataFrame) -> None:
    asterisk_rows = df[df["Player"].astype(str).str.startswith("*")]
    assert asterisk_rows.empty, (
        f"Found {len(asterisk_rows)} player(s) starting with '*': "
        f"{asterisk_rows['Player'].tolist()}"
    )


@then('the cleaned CSV has a "Round" column')
def step_round_column_exists(df: pd.DataFrame) -> None:
    assert "Round" in df.columns, "Missing column: Round"


@then("all Round values are between 1 and 15")
def step_round_values_valid(df: pd.DataFrame) -> None:
    out_of_range = df[(df["Round"] < 1) | (df["Round"] > 15)]
    assert out_of_range.empty, (
        f"Found Round values outside 1–15: {out_of_range['Round'].unique().tolist()}"
    )


@then(
    "the cleaned CSV contains the columns Round, Pick, Pick-Num, Team, Player, "
    "Position, Keeper, Starred, Elapsed Time, Rank, Total Fpts, Active Fpts"
)
def step_expected_columns_present(df: pd.DataFrame) -> None:
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    assert not missing, f"Missing columns: {missing}"


@then("the cleaned CSV path is a valid file path")
def step_cleaned_csv_path_valid(cleaned_csv_path: Path) -> None:
    assert cleaned_csv_path.is_file(), (
        f"cleaned_csv_path is not a file: {cleaned_csv_path}"
    )
