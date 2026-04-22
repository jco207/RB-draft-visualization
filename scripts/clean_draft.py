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
_POSITION_RE = re.compile(r'\b(QB|RB|WR|TE|DST|DEF|K)\b')
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
                continue
            first = row[0].strip().lower()
            # Format B: flat header — first cell is the word "round" in a multi-field row
            if first == "round" and len(row) > 1:
                return "B"
            # Formats A and C both start with a "Round N" single-cell separator row.
            # Peek at the next non-empty row (the column header) to distinguish them.
            for header_row in reader:
                if not header_row or all(c.strip() == "" for c in header_row):
                    continue
                fields = [f.strip() for f in header_row if f.strip()]
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
    current_round = 0

    with open(input_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        for raw_row in reader:
            if not raw_row or all(cell.strip() == "" for cell in raw_row):
                continue

            first = raw_row[0].strip()

            round_match = re.match(r'^Round\s+(\d+)$', first, re.IGNORECASE)
            if round_match:
                current_round = int(round_match.group(1))
                continue

            if first.lower() == "pick":
                continue

            if current_round == 0:
                warnings.append(f"Row found before any 'Round N' marker, skipped: {raw_row}")
                continue

            try:
                pick = int(first)
            except ValueError:
                warnings.append(
                    f"Round {current_round}: could not parse Pick from '{first}', row skipped"
                )
                continue

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

            pick_num = (current_round - 1) * PICKS_PER_ROUND + pick
            position = extract_position(player_raw)
            keeper = is_keeper(player_raw)
            starred = is_starred(player_raw)
            player_clean = clean_player_name(player_raw)

            if not rank:
                warnings.append(f"{label} ({player_clean}): missing Rank")
            if total_fpts == 0.0 and "(skipped pick)" not in player_clean.lower():
                warnings.append(f"{label} ({player_clean}): zero Total Fpts")
            if elapsed_time:
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
    """Parse Format B: flat pre-cleaned CSV with Round, Pick, Team, Player, Position columns."""
    warnings: list = []
    rows: list = []

    df_raw = pd.read_csv(input_path, dtype=str)

    for _, raw in df_raw.iterrows():
        current_round = int(raw["Round"])
        pick = int(raw["Pick"])
        team = raw["Team"].strip()
        player_raw = raw["Player"].strip()
        raw_position = raw.get("Position", "")
        position = str(raw_position).strip() if pd.notna(raw_position) else ""
        position = position or extract_position(player_raw)
        keeper = is_keeper(player_raw)
        starred = is_starred(player_raw)
        player_clean = clean_player_name(player_raw)
        pick_num = (current_round - 1) * PICKS_PER_ROUND + pick

        rows.append({
            "Round": current_round,
            "Pick": pick,
            "Pick-Num": pick_num,
            "Team": team,
            "Player": player_clean,
            "Position": position,
            "Keeper": keeper,
            "Starred": starred,
            "Elapsed Time": float("nan"),
            "Rank": float("nan"),
            "Total Fpts": float("nan"),
            "Active Fpts": float("nan"),
        })

    return rows, warnings


def _parse_format_c(input_path: Path) -> tuple:
    """Parse Format C: alternating 'Round N' rows, 5-col data (Pick, Team, Player, Elig, Elapsed Time)."""
    rows: list = []
    warnings: list = []
    current_round = 0

    with open(input_path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        for raw_row in reader:
            if not raw_row or all(cell.strip() == "" for cell in raw_row):
                continue

            first = raw_row[0].strip()

            round_match = re.match(r'^Round\s+(\d+)$', first, re.IGNORECASE)
            if round_match:
                current_round = int(round_match.group(1))
                continue

            if first.lower() == "pick":
                continue

            if current_round == 0:
                warnings.append(f"Row found before any 'Round N' marker, skipped: {raw_row}")
                continue

            try:
                pick = int(first)
            except ValueError:
                warnings.append(
                    f"Round {current_round}: could not parse Pick from '{first}', row skipped"
                )
                continue

            while len(raw_row) < 5:
                raw_row.append("")

            team = raw_row[1].strip()
            player_raw = raw_row[2].strip()
            # raw_row[3] is Elig — not used
            elapsed_time = raw_row[4].strip()

            pick_num = (current_round - 1) * PICKS_PER_ROUND + pick
            position = extract_position(player_raw)
            keeper = is_keeper(player_raw)
            starred = is_starred(player_raw)
            player_clean = clean_player_name(player_raw)

            if elapsed_time:
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
