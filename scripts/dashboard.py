#!/usr/bin/env python3
"""
dashboard.py — Fantasy Football Draft Dashboard (Streamlit)

Interactive dashboard for exploring a cleaned fantasy draft CSV. Provides
sidebar filters, charts, VBD analysis, best/worst pick tables, a data table,
a CSV download button, and a per-team roster breakdown.

Sidebar filters: year, round, position, team, keeper status (all / exclude /
only), roster view (Entire Team / Starters / Bench), total/active fantasy
points range, and rank substring.

Metric toggle (shared by all charts and tables): Total Fpts, Active Fpts, VBD.

VBD (Value Based Drafting): each player's Total Fpts minus the positional
baseline for a league of t teams. Baseline = t-th ranked player at the
position (floor(t * 1.5)-th for RB and WR). VBD/g = VBD / 17 games.

Roster classification (Starter / Bench): computed per team on the full
unfiltered dataset. Starters = best player at each non-RB/WR position + top-2
RBs + top-2 WRs + one FLEX (highest Total Fpts RB or WR not already a
starter). Everyone else is Bench.

Team Roster table: shown below the draft picks table. Always reflects the full
season roster regardless of other sidebar filters. Starters are listed first
(QB → RB → WR → TE → K → DST), followed by bench players in the same order.

Run with Streamlit (required):
    streamlit run scripts/dashboard.py
    streamlit run scripts/dashboard.py -- --data path/to/cleaned.csv

Direct help (shows this message, then exits):
    python scripts/dashboard.py --help

Dependencies:
    Cleaned CSV produced by clean_draft.py (see scripts/MANIFEST.md)
"""

import argparse
import math
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


def _get_available_years() -> dict:
    """Return a dict mapping year string to Path for each cleaned CSV in the data directory."""
    project_root = Path(__file__).parent.parent
    candidates = sorted((project_root / "data").glob("*-cleaned.csv"))
    years = {}
    for path in candidates:
        year = path.name[:4]
        if year.isdigit():
            years[year] = path
    return years


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
# Roster roles (Starter / Bench)
# ---------------------------------------------------------------------------

_POS_ORDER = ["QB", "RB", "WR", "TE", "K", "DST"]


def _pos_sort_key(pos: str) -> int:
    try:
        return _POS_ORDER.index(pos)
    except ValueError:
        return len(_POS_ORDER)


def compute_roster_roles(df: pd.DataFrame) -> pd.Series:
    """Return a Series of 'Starter' or 'Bench' for each row based on team rosters.

    Starters: best player at each non-RB/WR position, top-2 RBs, top-2 WRs,
    plus one FLEX (highest Total Fpts RB or WR not already a starter).
    """
    roles = pd.Series("Bench", index=df.index, dtype=str)
    for team, team_df in df.groupby("Team"):
        if not team:
            continue
        starter_indices: set = set()
        for pos, pos_df in team_df.groupby("Position"):
            if not pos:
                continue
            n = 2 if pos in ("RB", "WR") else 1
            starter_indices.update(pos_df.nlargest(n, "Total Fpts").index)
        flex_pool = team_df[
            team_df["Position"].isin(("RB", "WR"))
            & ~team_df.index.isin(starter_indices)
        ]
        if not flex_pool.empty:
            starter_indices.add(flex_pool["Total Fpts"].idxmax())
        roles.loc[list(starter_indices)] = "Starter"
    return roles


# ---------------------------------------------------------------------------
# VBD (Value Based Drafting)
# ---------------------------------------------------------------------------

_VBD_FLEX_POSITIONS = {"RB", "WR"}
_FANTASY_GAMES_PER_SEASON = 17


def _vbd_baselines(df: pd.DataFrame, t: int) -> dict:
    """
    Compute the VBD baseline Total Fpts for each position in a t-team league.

    Baseline = Total Fpts of the t-th ranked player at the position (by Total
    Fpts descending).  RB and WR use floor(t * 1.5) as the rank threshold to
    account for flex roster spots.  If fewer players exist at a position than
    the threshold, the lowest-scoring player is used as the baseline.
    """
    baselines: dict = {}
    for pos, pos_df in df.groupby("Position"):
        if not pos:
            continue
        multiplier = 1.5 if pos in _VBD_FLEX_POSITIONS else 1.0
        rank = math.floor(t * multiplier)
        sorted_fpts = (
            pos_df["Total Fpts"]
            .sort_values(ascending=False)
            .reset_index(drop=True)
        )
        idx = min(rank - 1, len(sorted_fpts) - 1)
        baselines[pos] = float(sorted_fpts.iloc[idx])
    return baselines


def compute_vbd(df: pd.DataFrame, t: int) -> pd.Series:
    """Return a Series of VBD scores (Total Fpts minus positional baseline)."""
    baselines = _vbd_baselines(df, t)
    return df.apply(
        lambda row: round(row["Total Fpts"] - baselines.get(row["Position"], 0.0), 1),
        axis=1,
    )


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

    st.sidebar.header("Filters")

    # Resolve data path — CLI flag takes precedence; otherwise use year picker
    if _CLI_ARGS.data:
        csv_path = _find_cleaned_csv(_CLI_ARGS.data)
        if csv_path is None or not csv_path.exists():
            st.error(f"Cleaned draft CSV not found: {_CLI_ARGS.data}")
            return
    else:
        available_years = _get_available_years()
        if not available_years:
            st.error(
                "Cleaned draft CSV not found. "
                "Run the cleaner first:\n\n"
                "```\n"
                "python scripts/clean_draft.py data/2025_Pre-season_Pre-season.csv\n"
                "```"
            )
            return
        year_options = sorted(available_years.keys(), reverse=True)
        selected_year = st.sidebar.selectbox("Year", options=year_options, index=0)
        csv_path = available_years[selected_year]

    df = load_data(str(csv_path)).copy()

    if df.empty:
        st.warning("The cleaned CSV contains no data.")
        return

    t = df["Team"].nunique()
    df["VBD"] = compute_vbd(df, t)
    df["VBD/g"] = (df["VBD"] / _FANTASY_GAMES_PER_SEASON).round(2)
    df["Roster"] = compute_roster_roles(df)

    # -----------------------------------------------------------------------
    # Remaining sidebar filters
    # -----------------------------------------------------------------------

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

    keeper_filter = st.sidebar.selectbox(
        "Keepers",
        options=["All players", "Exclude keepers", "Keepers only"],
        index=0,
    )

    roster_filter = st.sidebar.selectbox(
        "Roster",
        options=["Entire Team", "Starters", "Bench"],
        index=0,
    )

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

    if keeper_filter == "Keepers only":
        filtered = filtered[filtered["Keeper"]]
    elif keeper_filter == "Exclude keepers":
        filtered = filtered[~filtered["Keeper"]]

    if roster_filter == "Starters":
        filtered = filtered[filtered["Roster"] == "Starter"]
    elif roster_filter == "Bench":
        filtered = filtered[filtered["Roster"] == "Bench"]

    if rank_filter.strip():
        filtered = filtered[
            filtered["Rank"].str.contains(rank_filter.strip(), case=False, na=False)
        ]

    # -----------------------------------------------------------------------
    # Metric toggle — shared by both charts
    # -----------------------------------------------------------------------
    metric = st.radio(
        "Fantasy points metric",
        options=["Total Fpts", "Active Fpts", "VBD"],
        horizontal=True,
    )
    metric_titles = {
        "Total Fpts": "Total Fantasy Points",
        "Active Fpts": "Active Fantasy Points",
        "VBD": "Value Based Drafting (VBD)",
    }
    metric_title = metric_titles[metric]

    if filtered.empty:
        st.info("No picks match the current filters.")
    else:
        # -------------------------------------------------------------------
        # Bar chart — Fantasy Points by Pick Number
        # -------------------------------------------------------------------
        st.subheader(f"{metric_title} by Overall Pick Number")
        # Show "Round N" label only at the first pick of each round; blank otherwise.
        label_expr = (
            f"(parseInt(datum.value) - 1) % {t} == 0"
            f" ? 'Round ' + ceil(parseInt(datum.value) / {t}) : ''"
        )
        chart_pick = (
            alt.Chart(filtered)
            .mark_bar()
            .encode(
                x=alt.X(
                    "Pick-Num:O",
                    title="Round",
                    sort="ascending",
                    axis=alt.Axis(labelExpr=label_expr),
                ),
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
                    alt.Tooltip("VBD:Q", format=".1f"),
                ],
            )
            .properties(height=420)
        )
        st.altair_chart(chart_pick, use_container_width=True)

        # -------------------------------------------------------------------
        # Bar chart — Fantasy Points by Team
        # -------------------------------------------------------------------
        st.subheader(f"{metric_title} by Team")
        team_totals = (
            filtered.groupby("Team", as_index=False)[metric]
            .sum()
            .sort_values(metric, ascending=False)
        )
        chart_team = (
            alt.Chart(team_totals)
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

        # -------------------------------------------------------------------
        # Best / Worst pick tables — only when fantasy-points data is present
        # -------------------------------------------------------------------
        has_fpts = (filtered["Total Fpts"] > 0).any()

        if has_fpts:
            st.subheader("Best & Worst Pick by Round")
            round_rows = []
            for rnd in sorted(filtered["Round"].unique()):
                rnd_df = filtered[filtered["Round"] == rnd]
                best = rnd_df.loc[rnd_df[metric].idxmax()]
                worst = rnd_df.loc[rnd_df[metric].idxmin()]
                round_rows.append({
                    "Round": rnd,
                    "Best Pick": best["Player"],
                    "Best Team": best["Team"],
                    f"Best {metric}": round(float(best[metric]), 1),
                    "Worst Pick": worst["Player"],
                    "Worst Team": worst["Team"],
                    f"Worst {metric}": round(float(worst[metric]), 1),
                })
            round_df = pd.DataFrame(round_rows)
            st.dataframe(
                round_df,
                use_container_width=True,
                hide_index=True,
                height=38 + 35 * len(round_df),
            )

            st.subheader("Best & Worst Pick by Team")
            team_rows = []
            for team in sorted(filtered["Team"].unique()):
                team_df = filtered[filtered["Team"] == team]
                best = team_df.loc[team_df[metric].idxmax()]
                worst = team_df.loc[team_df[metric].idxmin()]
                team_rows.append({
                    "Team": team,
                    "Best Pick": best["Player"],
                    "Best Round": int(best["Round"]),
                    f"Best {metric}": round(float(best[metric]), 1),
                    "Worst Pick": worst["Player"],
                    "Worst Round": int(worst["Round"]),
                    f"Worst {metric}": round(float(worst[metric]), 1),
                })
            team_df = pd.DataFrame(team_rows)
            st.dataframe(
                team_df,
                use_container_width=True,
                hide_index=True,
                height=38 + 35 * len(team_df),
            )

    # -----------------------------------------------------------------------
    # Data table — "Roster" is an internal classification column; omit it here
    # so the display stays clean (it is still included in the CSV download).
    # -----------------------------------------------------------------------
    st.subheader(f"Draft Picks  ({len(filtered):,} shown of {len(df):,})")
    st.dataframe(
        filtered.drop(columns="Roster").reset_index(drop=True),
        use_container_width=True,
    )

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

    # -----------------------------------------------------------------------
    # Team roster breakdown — always uses the full unfiltered df so the
    # lineup reflects the true roster regardless of sidebar filters.
    # -----------------------------------------------------------------------
    st.subheader("Team Roster (full season, unfiltered)")
    roster_teams = sorted(df["Team"].unique().tolist())
    if roster_teams:
        selected_roster_team = st.selectbox(
            "Select team", options=roster_teams, key="roster_team_select"
        )
        team_roster = df[df["Team"] == selected_roster_team].copy()

        starters = team_roster[team_roster["Roster"] == "Starter"].copy()
        bench = team_roster[team_roster["Roster"] == "Bench"].copy()

        starters["_pos_order"] = starters["Position"].apply(_pos_sort_key)
        bench["_pos_order"] = bench["Position"].apply(_pos_sort_key)

        starters = starters.sort_values("_pos_order").drop(columns="_pos_order")
        bench = bench.sort_values("_pos_order").drop(columns="_pos_order")

        roster_display_cols = [
            "Roster", "Position", "Player", "Round", "Pick",
            "Total Fpts", "Active Fpts", "VBD",
        ]
        roster_table = pd.concat([starters, bench])[roster_display_cols].reset_index(drop=True)

        st.dataframe(
            roster_table,
            use_container_width=True,
            hide_index=True,
            height=38 + 35 * len(roster_table),
        )


main()
