#!/usr/bin/env python3
"""
dashboard.py — Fantasy Football Draft Dashboard (Streamlit)

Interactive dashboard for exploring a cleaned fantasy draft CSV. Provides
sidebar filters, a bar chart of fantasy points by pick number, a data table,
and a CSV download button.

Run with Streamlit (required):
    streamlit run scripts/dashboard.py
    streamlit run scripts/dashboard.py -- --data path/to/cleaned.csv

Direct help (shows this message, then exits):
    python scripts/dashboard.py --help

Dependencies:
    Cleaned CSV produced by clean_draft.py (see scripts/MANIFEST.md)
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

import altair as alt
import pandas as pd
import streamlit as st


# ---------------------------------------------------------------------------
# CLI argument handling
# ---------------------------------------------------------------------------

def _get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    parser.add_argument(
        "-h", "--help",
        action="store_true",
        help="Show this help message and exit",
    )
    parser.add_argument(
        "-d", "--data",
        metavar="CLEANED_CSV",
        default=None,
        help=(
            "Path to the cleaned draft CSV produced by clean_draft.py "
            "(default: auto-detect *-cleaned.csv in the project root)"
        ),
    )
    return parser


def _parse_cli_args() -> argparse.Namespace:
    """Parse known CLI args, ignoring Streamlit's own injected arguments."""
    parser = _get_parser()
    args, _ = parser.parse_known_args()

    if args.help:
        parser.print_help()
        print(
            "\nNote: this script must be launched via Streamlit:\n"
            f"  streamlit run {Path(__file__).name}\n"
            f"  streamlit run {Path(__file__).name} -- --data path/to/cleaned.csv"
        )
        sys.exit(0)

    return args


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _find_cleaned_csv(data_arg: Optional[str]) -> Optional[Path]:
    """Resolve the cleaned CSV path from CLI arg or by auto-detecting in the project root."""
    if data_arg:
        return Path(data_arg)
    project_root = Path(__file__).parent.parent
    candidates = sorted((project_root / "data").glob("*-cleaned.csv"))
    return candidates[-1] if candidates else None


@st.cache_data
def load_data(csv_path: str) -> pd.DataFrame:
    """Load and cache the cleaned draft CSV from *csv_path*, with correct dtypes."""
    df = pd.read_csv(csv_path)
    df["Round"] = df["Round"].astype(int)
    df["Pick"] = df["Pick"].astype(int)
    df["Pick-Num"] = df["Pick-Num"].astype(int)
    df["Total Fpts"] = pd.to_numeric(df["Total Fpts"], errors="coerce").fillna(0.0)
    df["Active Fpts"] = pd.to_numeric(df["Active Fpts"], errors="coerce").fillna(0.0)
    df["Keeper"] = df["Keeper"].astype(bool)
    df["Position"] = df["Position"].fillna("").astype(str)
    df["Team"] = df["Team"].fillna("").astype(str)
    df["Rank"] = df["Rank"].fillna("").astype(str)
    return df


# ---------------------------------------------------------------------------
# Main Streamlit app
# ---------------------------------------------------------------------------

_CLI_ARGS = _parse_cli_args()


def main() -> None:
    st.set_page_config(
        page_title="Fantasy Football Draft Dashboard",
        layout="wide",
    )

    st.title("Fantasy Football Draft Dashboard")

    # Resolve data path
    csv_path = _find_cleaned_csv(_CLI_ARGS.data)

    if csv_path is None or not csv_path.exists():
        st.error(
            "Cleaned draft CSV not found. "
            "Run the cleaner first:\n\n"
            "```\n"
            "python scripts/clean_draft.py data/2025_Pre-season_Pre-season.csv\n"
            "```"
        )
        return

    df = load_data(str(csv_path))

    if df.empty:
        st.warning("The cleaned CSV contains no data.")
        return

    # -----------------------------------------------------------------------
    # Sidebar filters
    # -----------------------------------------------------------------------
    st.sidebar.header("Filters")

    all_rounds = sorted(df["Round"].unique().tolist())
    selected_rounds = st.sidebar.multiselect(
        "Round", options=all_rounds, default=all_rounds
    )

    # Include the empty-string position so rows like "(Skipped Pick)" are visible
    all_positions = sorted(df["Position"].unique().tolist())
    selected_positions = st.sidebar.multiselect(
        "Position", options=all_positions, default=all_positions
    )

    all_teams = sorted(df["Team"].unique().tolist())
    selected_teams = st.sidebar.multiselect(
        "Team", options=all_teams, default=all_teams
    )

    keeper_only = st.sidebar.checkbox("Keeper picks only", value=False)

    min_total = float(df["Total Fpts"].min())
    max_total = float(df["Total Fpts"].max())
    # Guard against min == max, which Streamlit's slider does not allow
    if min_total == max_total:
        max_total = min_total + 1.0
    total_range = st.sidebar.slider(
        "Total Fantasy Points",
        min_value=min_total,
        max_value=max_total,
        value=(min_total, max_total),
        step=0.1,
    )

    min_active = float(df["Active Fpts"].min())
    max_active = float(df["Active Fpts"].max())
    if min_active == max_active:
        max_active = min_active + 1.0
    active_range = st.sidebar.slider(
        "Active Fantasy Points",
        min_value=min_active,
        max_value=max_active,
        value=(min_active, max_active),
        step=0.1,
    )

    rank_filter = st.sidebar.text_input(
        "Filter by Rank position (e.g. RB)",
        value="",
        help="Type a position abbreviation to show only picks whose Rank field contains it.",
    )

    # -----------------------------------------------------------------------
    # Apply filters
    # -----------------------------------------------------------------------
    mask = (
        df["Round"].isin(selected_rounds)
        & df["Position"].isin(selected_positions)
        & df["Team"].isin(selected_teams)
        & df["Total Fpts"].between(total_range[0], total_range[1])
        & df["Active Fpts"].between(active_range[0], active_range[1])
    )
    filtered = df[mask].copy()

    if keeper_only:
        filtered = filtered[filtered["Keeper"]]

    if rank_filter.strip():
        filtered = filtered[
            filtered["Rank"].str.contains(rank_filter.strip(), case=False, na=False)
        ]

    # -----------------------------------------------------------------------
    # Metric toggle — shared by both charts
    # -----------------------------------------------------------------------
    metric = st.radio(
        "Fantasy points metric",
        options=["Total Fpts", "Active Fpts"],
        horizontal=True,
    )
    metric_title = "Total Fantasy Points" if metric == "Total Fpts" else "Active Fantasy Points"

    if filtered.empty:
        st.info("No picks match the current filters.")
    else:
        # -------------------------------------------------------------------
        # Bar chart — Fantasy Points by Pick Number
        # -------------------------------------------------------------------
        st.subheader(f"{metric_title} by Overall Pick Number")
        chart_pick = (
            alt.Chart(filtered)
            .mark_bar()
            .encode(
                x=alt.X("Pick-Num:O", title="Overall Pick #", sort="ascending"),
                y=alt.Y(f"{metric}:Q", title=metric_title),
                color=alt.Color(
                    "Position:N",
                    scale=alt.Scale(scheme="category10"),
                    legend=alt.Legend(title="Position"),
                ),
                tooltip=[
                    alt.Tooltip("Pick-Num:O", title="Pick #"),
                    alt.Tooltip("Player:N"),
                    alt.Tooltip("Team:N"),
                    alt.Tooltip("Position:N"),
                    alt.Tooltip("Round:O"),
                    alt.Tooltip("Rank:N"),
                    alt.Tooltip("Total Fpts:Q", format=".1f"),
                    alt.Tooltip("Active Fpts:Q", format=".1f"),
                ],
            )
            .properties(height=420)
        )
        st.altair_chart(chart_pick, use_container_width=True)

        # -------------------------------------------------------------------
        # Bar chart — Fantasy Points by Team
        # -------------------------------------------------------------------
        st.subheader(f"{metric_title} by Team")
        team_df = (
            filtered.groupby("Team", as_index=False)[metric]
            .sum()
            .sort_values(metric, ascending=False)
        )
        chart_team = (
            alt.Chart(team_df)
            .mark_bar()
            .encode(
                x=alt.X("Team:N", sort="-y", title="Team"),
                y=alt.Y(f"{metric}:Q", title=metric_title),
                tooltip=[
                    alt.Tooltip("Team:N"),
                    alt.Tooltip(f"{metric}:Q", title=metric_title, format=".1f"),
                ],
            )
            .properties(height=420)
        )
        st.altair_chart(chart_team, use_container_width=True)

    # -----------------------------------------------------------------------
    # Data table
    # -----------------------------------------------------------------------
    st.subheader(f"Draft Picks  ({len(filtered):,} shown of {len(df):,})")
    st.dataframe(filtered.reset_index(drop=True), use_container_width=True)

    # -----------------------------------------------------------------------
    # Download button
    # -----------------------------------------------------------------------
    csv_bytes = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download filtered view as CSV",
        data=csv_bytes,
        file_name="draft_filtered.csv",
        mime="text/csv",
    )


main()
