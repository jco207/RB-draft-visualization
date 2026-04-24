#!/usr/bin/env python3
"""
clean_draft.py — Fantasy Football Draft CSV Cleaner

Reads a raw draft CSV exported from a fantasy platform and normalizes it into
a flat table with consistent columns across all supported formats.

Supported input formats
-----------------------
Format A (e.g. 2025):
    Alternating "Round N" separator rows and repeated column-header rows.
    Data columns: Pick, Team, Player, Elapsed Time, Rank, Total Fpts, Active Fpts

Format B (e.g. 2021–2024):
    Standard flat CSV with a single header row.
    Columns: Round, Pick, Team, Player, Position, NFL Team

Format C (e.g. 2020):
    Alternating "Round N" separator rows and repeated column-header rows.
    Data columns: Pick, Team, Player, Elig, Elapsed Time (no Rank / Fpts)

Output columns (all formats)
-----------------------------
  Round, Pick, Pick-Num, Team, Player, Position, Keeper, Starred,
  Elapsed Time, Rank, Total Fpts, Active Fpts

Columns unavailable for a given format are written as empty (NaN).

Added / computed columns:
  Round      — round number (1–15)
  Pick-Num   — overall sequential pick number: ((Round - 1) * 12) + Pick
  Position   — extracted from the Player string (QB/RB/WR/TE/K/DST/DEF)
  Keeper     — True if the pick was flagged as "(Keeper)"
  Starred    — True if the player was prefixed with "*" in the raw data

Usage:
    python scripts/clean_draft.py <INPUT_CSV> [--output <PATH>]

Examples:
    python scripts/clean_draft.py data/2025_Pre-season_Pre-season.csv
    python scripts/clean_draft.py data/draft.csv --output data/draft-cleaned.csv
"""

import argparse
import csv
import re
import sys
from pathlib import Path

import pandas as pd

PICKS_PER_ROUND = 12  # Number of teams / picks in each round

# Compiled once at module level for performance.
# Matches any recognised fantasy position token as a whole word so "RB" inside
# "RB | CIN" is found but a bare "K" inside "Kirk" is not.
_POSITION_RE = re.compile(r'\b(QB|RB|WR|TE|DST|DEF|K)\b')

# Matches the two standard timer formats the platform exports: "45 sec" or "3 min 12 sec".
# Anything else (e.g. platform-specific suffixes) triggers a data-quality warning.
_ELAPSED_SIMPLE_RE = re.compile(r'^\d+ sec$|^\d+ min \d+ sec$')

OUTPUT_COLUMNS = [
    "Round", "Pick", "Pick-Num", "Team", "Player", "Position",
    "Keeper", "Starred", "Elapsed Time", "Rank", "Total Fpts", "Active Fpts",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "input",
        metavar="INPUT_CSV",
        help="Path to the raw draft CSV file",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="OUTPUT_CSV",
        default=None,
        help=(
            "Output path for the cleaned CSV "
            "(default: <input_stem>-cleaned.csv beside the input file)"
        ),
    )
    return parser.parse_args()


def extract_position(player_str: str) -> str:
    """Return the first position token found in a player string, e.g. 'RB' from 'Ja'Marr Chase RB | CIN'."""
    match = _POSITION_RE.search(player_str)
    return match.group(1) if match else ""


def clean_player_name(player_str: str) -> str:
    """Strip leading '*', remove '(Keeper)' marker, and normalize whitespace."""
    name = player_str.strip().lstrip("*")
    name = re.sub(r'\s*\(Keeper\)\s*', ' ', name, flags=re.IGNORECASE)
    name = re.sub(r'  +', ' ', name)
    return name.strip()


def is_keeper(player_str: str) -> bool:
    """Return True if the player string contains the '(Keeper)' marker."""
    return bool(re.search(r'\(Keeper\)', player_str, re.IGNORECASE))


def is_starred(player_str: str) -> bool:
    """Return True if the player string has a leading '*'."""
    return player_str.strip().startswith("*")


def _safe_float(value: str, label: str, warnings: list) -> float:
    """Parse a float string, appending a warning and returning 0.0 on failure."""
    if not value.strip():
        return 0.0
    try:
        return float(value.strip())
    except ValueError:
        warnings.append(f"{label}: could not parse float from '{value}'")
        return 0.0


def detect_format(input_path: Path) -> str:
    """Return 'A', 'B', or 'C' based on CSV structure of the first two non-empty rows."""
    with open(input_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if not row or all(c.strip() == "" for c in row):
                continue  # skip blank lines at the top of the file

            first = row[0].strip().lower()

            # Format B: a true header row where the first cell is the literal
            # word "round" and the row contains multiple columns (Round, Pick, …).
            if first == "round" and len(row) > 1:
                return "B"

            # Formats A and C both open with a "Round N" separator row (a single
            # non-empty cell).  We need to peek at the *next* non-empty row — the
            # per-round column headers — to tell them apart.
            for header_row in reader:
                if not header_row or all(c.strip() == "" for c in header_row):
                    continue
                fields = [f.strip() for f in header_row if f.strip()]
                # Format C has an "Elig" column that Format A never has, and
                # generally has only 5 fields vs. Format A's 7.
                return "C" if "Elig" in fields or len(fields) <= 5 else "A"
            break
    raise ValueError(
        f"Cannot determine CSV format for {input_path}. "
        "Expected Format A (7-col alternating), B (flat Round/Pick/Position), "
        "or C (5-col alternating with Elig column)."
    )


def build_output_df(rows: list) -> pd.DataFrame:
    """Build the output DataFrame with a guaranteed consistent column order."""
    return pd.DataFrame(rows).reindex(columns=OUTPUT_COLUMNS)


def parse_csv(input_path: Path) -> tuple:
    """
    Auto-detect the CSV format and parse into a list of normalised row dicts.

    Returns:
        rows     — list of dict, one per draft pick
        warnings — list of human-readable quality issue strings
    """
    fmt = detect_format(input_path)
    if fmt == "B":
        return _parse_format_b(input_path)
    if fmt == "C":
        return _parse_format_c(input_path)
    return _parse_format_a(input_path)


def _parse_format_a(input_path: Path) -> tuple:
    """Parse Format A: alternating 'Round N' rows, 7-col data (Elapsed Time, Rank, Fpts)."""
    rows: list = []
    warnings: list = []
    current_round = 0  # tracks the most recent "Round N" separator seen

    with open(input_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        for raw_row in reader:
            if not raw_row or all(cell.strip() == "" for cell in raw_row):
                continue  # ignore blank / spacer lines between rounds

            first = raw_row[0].strip()

            # "Round 1", "Round 2", … separator rows set the round counter and
            # are otherwise discarded — they are not pick data.
            round_match = re.match(r'^Round\s+(\d+)$', first, re.IGNORECASE)
            if round_match:
                current_round = int(round_match.group(1))
                continue

            # Each round section repeats the column-header row ("Pick, Team, …");
            # skip it so we only process actual pick rows.
            if first.lower() == "pick":
                continue

            # Sanity check: a data row appearing before the first "Round N" line
            # indicates a malformed file; record it and skip.
            if current_round == 0:
                warnings.append(f"Row found before any 'Round N' marker, skipped: {raw_row}")
                continue

            try:
                pick = int(first)  # first column is the within-round pick number (1–12)
            except ValueError:
                warnings.append(
                    f"Round {current_round}: could not parse Pick from '{first}', row skipped"
                )
                continue

            # Some platform exports strip trailing empty cells; pad to 7 so the
            # column index lookups below never raise IndexError.
            while len(raw_row) < 7:
                raw_row.append("")

            team = raw_row[1].strip()
            player_raw = raw_row[2].strip()
            elapsed_time = raw_row[3].strip()
            rank = raw_row[4].strip()
            total_fpts_str = raw_row[5].strip()
            active_fpts_str = raw_row[6].strip()

            label = f"Round {current_round} Pick {pick}"
            total_fpts = _safe_float(total_fpts_str, f"{label} Total Fpts", warnings)
            active_fpts = _safe_float(active_fpts_str, f"{label} Active Fpts", warnings)

            # Sequential pick number across all rounds, 1-indexed.
            # e.g. Round 2 Pick 3 in a 12-team league → (2-1)*12 + 3 = 15
            pick_num = (current_round - 1) * PICKS_PER_ROUND + pick
            position = extract_position(player_raw)
            keeper = is_keeper(player_raw)
            starred = is_starred(player_raw)
            player_clean = clean_player_name(player_raw)

            # Data-quality checks: missing Rank and zero Fpts are common export
            # glitches worth surfacing without failing the whole parse.
            if not rank:
                warnings.append(f"{label} ({player_clean}): missing Rank")
            if total_fpts == 0.0 and "(skipped pick)" not in player_clean.lower():
                warnings.append(f"{label} ({player_clean}): zero Total Fpts")
            if elapsed_time:
                # The platform sometimes appends a parenthetical note like "(auto)"
                # after the timer value; strip it before validating the format.
                base_elapsed = elapsed_time.split("(")[0].strip()
                if base_elapsed and not _ELAPSED_SIMPLE_RE.match(base_elapsed):
                    warnings.append(
                        f"{label}: non-standard Elapsed Time format '{elapsed_time}'"
                    )

            rows.append({
                "Round": current_round,
                "Pick": pick,
                "Pick-Num": pick_num,
                "Team": team,
                "Player": player_clean,
                "Position": position,
                "Keeper": keeper,
                "Starred": starred,
                "Elapsed Time": elapsed_time,
                "Rank": rank,
                "Total Fpts": total_fpts,
                "Active Fpts": active_fpts,
            })

    return rows, warnings


def _parse_format_b(input_path: Path) -> tuple:
    """Parse Format B: flat CSV with Round, Pick, Team, Player, Position columns.

    Optional columns read when present: Elapsed Time, Total Fpts, Active Fpts.
    """
    warnings: list = []
    rows: list = []

    # Read every column as a string so we can handle mixed-type cells (e.g. a
    # numeric Rank next to a plain-text one) without silent coercions.
    df_raw = pd.read_csv(input_path, dtype=str)

    # Format B never guarantees the time/fpts columns, so check once up front
    # rather than row-by-row.
    has_elapsed = "Elapsed Time" in df_raw.columns
    has_fpts = "Total Fpts" in df_raw.columns and "Active Fpts" in df_raw.columns

    def _col(raw, col):
        """Return the string value of *col*, or '' if the cell is missing/NaN."""
        val = raw.get(col, "")
        return "" if pd.isna(val) else str(val).strip()

    for _, raw in df_raw.iterrows():
        current_round = int(raw["Round"])
        pick = int(raw["Pick"])
        team = raw["Team"].strip()
        player_raw = raw["Player"].strip()
        raw_position = raw.get("Position", "")
        # Prefer the explicit Position column if present and non-null; fall back to
        # extracting the position token embedded in the Player string.
        position = str(raw_position).strip() if pd.notna(raw_position) else ""
        position = position or extract_position(player_raw)
        keeper = is_keeper(player_raw)
        starred = is_starred(player_raw)
        player_clean = clean_player_name(player_raw)
        pick_num = (current_round - 1) * PICKS_PER_ROUND + pick

        elapsed = _col(raw, "Elapsed Time") if has_elapsed else float("nan")
        label = f"Round {current_round} Pick {pick}"
        total_fpts = _safe_float(_col(raw, "Total Fpts"), f"{label} Total Fpts", warnings) if has_fpts else float("nan")
        active_fpts = _safe_float(_col(raw, "Active Fpts"), f"{label} Active Fpts", warnings) if has_fpts else float("nan")

        rows.append({
            "Round": current_round,
            "Pick": pick,
            "Pick-Num": pick_num,
            "Team": team,
            "Player": player_clean,
            "Position": position,
            "Keeper": keeper,
            "Starred": starred,
            "Elapsed Time": elapsed,
            # Format B has no Rank column; NaN keeps the output schema consistent.
            "Rank": float("nan"),
            "Total Fpts": total_fpts,
            "Active Fpts": active_fpts,
        })

    return rows, warnings


def _parse_format_c(input_path: Path) -> tuple:
    """Parse Format C: alternating 'Round N' rows, 5-col data (Pick, Team, Player, Elig, Elapsed Time)."""
    rows: list = []
    warnings: list = []
    current_round = 0  # tracks the most recent "Round N" separator seen

    with open(input_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        for raw_row in reader:
            if not raw_row or all(cell.strip() == "" for cell in raw_row):
                continue  # skip blank / spacer lines between rounds

            first = raw_row[0].strip()

            # "Round N" separator rows update the round counter; they are not picks.
            round_match = re.match(r'^Round\s+(\d+)$', first, re.IGNORECASE)
            if round_match:
                current_round = int(round_match.group(1))
                continue

            # Each round section repeats the column-header row; skip it.
            if first.lower() == "pick":
                continue

            # Data row seen before any "Round N" line — malformed file.
            if current_round == 0:
                warnings.append(f"Row found before any 'Round N' marker, skipped: {raw_row}")
                continue

            try:
                pick = int(first)  # within-round pick number (1–12)
            except ValueError:
                warnings.append(
                    f"Round {current_round}: could not parse Pick from '{first}', row skipped"
                )
                continue

            # Pad to 5 columns in case trailing empty cells were stripped on export.
            while len(raw_row) < 5:
                raw_row.append("")

            team = raw_row[1].strip()
            player_raw = raw_row[2].strip()
            # raw_row[3] is the "Elig" (eligible positions) column — not needed for
            # our output schema, so we read past it without storing it.
            elapsed_time = raw_row[4].strip()

            pick_num = (current_round - 1) * PICKS_PER_ROUND + pick
            position = extract_position(player_raw)
            keeper = is_keeper(player_raw)
            starred = is_starred(player_raw)
            player_clean = clean_player_name(player_raw)

            if elapsed_time:
                # Strip any parenthetical annotation before validating the timer format.
                base_elapsed = elapsed_time.split("(")[0].strip()
                if base_elapsed and not _ELAPSED_SIMPLE_RE.match(base_elapsed):
                    warnings.append(
                        f"Round {current_round} Pick {pick}: non-standard Elapsed Time format '{elapsed_time}'"
                    )

            rows.append({
                "Round": current_round,
                "Pick": pick,
                "Pick-Num": pick_num,
                "Team": team,
                "Player": player_clean,
                "Position": position,
                "Keeper": keeper,
                "Starred": starred,
                "Elapsed Time": elapsed_time,
                # Format C has no Rank, Total Fpts, or Active Fpts columns; NaN
                # keeps the output schema uniform across all formats.
                "Rank": float("nan"),
                "Total Fpts": float("nan"),
                "Active Fpts": float("nan"),
            })

    return rows, warnings


def print_quality_report(rows: list, warnings: list) -> None:
    """Print a summary of parsed data and any quality issues to stdout."""
    print("\n=== Data Quality Report ===")
    print(f"Total picks parsed : {len(rows)}")

    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(f"  • {w}")
    else:
        print("\nNo data quality issues detected.")

    keepers = sum(1 for r in rows if r["Keeper"])
    starred = sum(1 for r in rows if r["Starred"])

    positions: dict = {}
    for r in rows:
        pos = r["Position"] or "Unknown"
        positions[pos] = positions.get(pos, 0) + 1

    print(f"\nKeeper picks : {keepers}")
    print(f"Starred (*)  : {starred}")
    print("\nPicks by position:")
    for pos, count in sorted(positions.items()):
        print(f"  {pos:>8} : {count}")
    print()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: file not found — {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading : {input_path}")
    rows, warnings = parse_csv(input_path)
    print_quality_report(rows, warnings)

    df = build_output_df(rows)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / (input_path.stem + "-cleaned.csv")

    df.to_csv(output_path, index=False)
    print(f"Saved   : {output_path}")


if __name__ == "__main__":
    main()
