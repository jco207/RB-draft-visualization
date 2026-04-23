"""
Unit tests for dashboard pure-function helpers.

Covers: compute_vbd, compute_roster_roles.
These tests do not require Streamlit and run as plain pytest.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from dashboard import (
    _vbd_baselines,
    compute_roster_roles,
    compute_vbd,
)


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def roster_df() -> pd.DataFrame:
    """
    Two-team DataFrame with known positions and Total Fpts.
    Team A: QB, 3 RBs, 3 WRs, TE, K.
    Team B: QB, RB, WR.
    """
    rows = [
        # Team A
        {"Player": "QB_A1",  "Team": "A", "Position": "QB", "Total Fpts": 400.0},
        {"Player": "RB_A1",  "Team": "A", "Position": "RB", "Total Fpts": 300.0},
        {"Player": "RB_A2",  "Team": "A", "Position": "RB", "Total Fpts": 250.0},
        {"Player": "RB_A3",  "Team": "A", "Position": "RB", "Total Fpts": 200.0},
        {"Player": "WR_A1",  "Team": "A", "Position": "WR", "Total Fpts": 280.0},
        {"Player": "WR_A2",  "Team": "A", "Position": "WR", "Total Fpts": 230.0},
        {"Player": "WR_A3",  "Team": "A", "Position": "WR", "Total Fpts": 100.0},
        {"Player": "TE_A1",  "Team": "A", "Position": "TE", "Total Fpts": 180.0},
        {"Player": "K_A1",   "Team": "A", "Position": "K",  "Total Fpts":  90.0},
        # Team B
        {"Player": "QB_B1",  "Team": "B", "Position": "QB", "Total Fpts": 350.0},
        {"Player": "RB_B1",  "Team": "B", "Position": "RB", "Total Fpts": 320.0},
        {"Player": "WR_B1",  "Team": "B", "Position": "WR", "Total Fpts": 260.0},
    ]
    df = pd.DataFrame(rows)
    for col in ("Active Fpts", "Round", "Pick", "Pick-Num"):
        df[col] = 0
    df["Keeper"] = False
    df["Rank"] = ""
    return df


# ---------------------------------------------------------------------------
# compute_vbd
# ---------------------------------------------------------------------------

class TestComputeVbd:
    def test_returns_series_same_length(self, roster_df):
        result = compute_vbd(roster_df, t=2)
        assert len(result) == len(roster_df)

    def test_rb_wr_baseline_uses_flex_multiplier(self, roster_df):
        # Baseline is computed globally across all teams.
        # All RBs by fpts desc: RB_B1(320), RB_A1(300), RB_A2(250), RB_A3(200)
        # t=2 → floor(2*1.5)=3 → 3rd-ranked RB is RB_A2 (250.0)
        t = 2
        result = compute_vbd(roster_df, t=t)
        rb_a1_idx = roster_df[roster_df["Player"] == "RB_A1"].index[0]
        assert result.iloc[rb_a1_idx] == round(300.0 - 250.0, 1)

    def test_non_flex_position_baseline_uses_t(self, roster_df):
        # All QBs by fpts desc: QB_A1(400), QB_B1(350)
        # t=2 → 2nd-ranked QB is QB_B1 (350.0)
        t = 2
        result = compute_vbd(roster_df, t=t)
        qb_a1_idx = roster_df[roster_df["Player"] == "QB_A1"].index[0]
        assert result.iloc[qb_a1_idx] == round(400.0 - 350.0, 1)

    def test_player_exactly_at_baseline_has_zero_vbd(self, roster_df):
        # RB_A2 (250.0) is the 3rd-ranked RB globally — exactly at the baseline
        result = compute_vbd(roster_df, t=2)
        rb_a2_idx = roster_df[roster_df["Player"] == "RB_A2"].index[0]
        assert result.iloc[rb_a2_idx] == 0.0

    def test_all_players_below_baseline_have_negative_vbd(self, roster_df):
        result = compute_vbd(roster_df, t=2)
        wr_a3_idx = roster_df[roster_df["Player"] == "WR_A3"].index[0]
        assert result.iloc[wr_a3_idx] < 0

    def test_baseline_clamps_to_last_player_when_pool_is_small(self, roster_df):
        # t=10 → floor(10*1.5)=15, but there are only 4 RBs total — clamp to last
        baselines = _vbd_baselines(roster_df, t=10)
        # The minimum RB fpts is RB_A3 = 200.0
        assert baselines["RB"] == pytest.approx(200.0)


# ---------------------------------------------------------------------------
# compute_roster_roles
# ---------------------------------------------------------------------------

class TestComputeRosterRoles:
    def test_returns_series_same_length(self, roster_df):
        assert len(compute_roster_roles(roster_df)) == len(roster_df)

    def test_only_valid_values(self, roster_df):
        roles = compute_roster_roles(roster_df)
        assert set(roles.unique()).issubset({"Starter", "Bench"})

    def test_top_qb_is_starter(self, roster_df):
        roles = compute_roster_roles(roster_df)
        idx = roster_df[roster_df["Player"] == "QB_A1"].index[0]
        assert roles.iloc[idx] == "Starter"

    def test_top_two_rbs_are_starters(self, roster_df):
        roles = compute_roster_roles(roster_df)
        for player in ("RB_A1", "RB_A2"):
            idx = roster_df[roster_df["Player"] == player].index[0]
            assert roles.iloc[idx] == "Starter", f"{player} should be Starter"

    def test_top_two_wrs_are_starters(self, roster_df):
        roles = compute_roster_roles(roster_df)
        for player in ("WR_A1", "WR_A2"):
            idx = roster_df[roster_df["Player"] == player].index[0]
            assert roles.iloc[idx] == "Starter", f"{player} should be Starter"

    def test_flex_is_best_remaining_rb_or_wr(self, roster_df):
        # RB_A3 (200) > WR_A3 (100) → RB_A3 should be the flex starter
        roles = compute_roster_roles(roster_df)
        rb_a3_idx = roster_df[roster_df["Player"] == "RB_A3"].index[0]
        assert roles.iloc[rb_a3_idx] == "Starter"

    def test_fourth_rb_or_wr_is_bench(self, roster_df):
        # Team A starters: RB_A1, RB_A2 (top-2 RB), WR_A1, WR_A2 (top-2 WR),
        # flex=RB_A3 (best remaining RB/WR). WR_A3 is the only one left over → Bench.
        roles = compute_roster_roles(roster_df)
        wr_a3_idx = roster_df[roster_df["Player"] == "WR_A3"].index[0]
        assert roles.iloc[wr_a3_idx] == "Bench"

    def test_te_and_k_are_starters(self, roster_df):
        roles = compute_roster_roles(roster_df)
        for player in ("TE_A1", "K_A1"):
            idx = roster_df[roster_df["Player"] == player].index[0]
            assert roles.iloc[idx] == "Starter", f"{player} should be Starter"

    def test_each_team_computed_independently(self, roster_df):
        # QB_B1 should be a starter on Team B regardless of Team A
        roles = compute_roster_roles(roster_df)
        idx = roster_df[roster_df["Player"] == "QB_B1"].index[0]
        assert roles.iloc[idx] == "Starter"

    def test_starter_count_is_correct(self, roster_df):
        # Team A: QB(1) + RB(2) + WR(2) + TE(1) + K(1) + flex(1) = 8 starters
        # Team B: QB(1) + RB(1) + WR(1) = 3 (no flex eligible — both RB and WR already starters)
        roles = compute_roster_roles(roster_df)
        team_a_starters = roles[roster_df["Team"] == "A"].value_counts().get("Starter", 0)
        assert team_a_starters == 8

    def test_no_flex_when_only_one_rb_and_one_wr(self, roster_df):
        # Team B has exactly 1 RB and 1 WR — both are positional starters, no flex pool remains
        roles = compute_roster_roles(roster_df)
        team_b = roster_df[roster_df["Team"] == "B"]
        team_b_bench = roles[team_b.index].eq("Bench").sum()
        assert team_b_bench == 0

    def test_empty_position_row_is_bench(self):
        # Rows with empty Position (e.g. skipped picks) should always be Bench,
        # not accidentally promoted to Starter via the positional groupby.
        df = pd.DataFrame([
            {"Player": "QB_X", "Team": "X", "Position": "QB", "Total Fpts": 300.0},
            {"Player": "(Skipped Pick)", "Team": "X", "Position": "", "Total Fpts": 0.0},
        ])
        for col in ("Active Fpts", "Round", "Pick", "Pick-Num"):
            df[col] = 0
        df["Keeper"] = False
        df["Rank"] = ""
        roles = compute_roster_roles(df)
        skipped_idx = df[df["Player"] == "(Skipped Pick)"].index[0]
        assert roles.iloc[skipped_idx] == "Bench"

    def test_no_flex_when_team_has_no_rb_or_wr(self):
        # A team with only a QB and TE has no RB/WR pool — no flex should be assigned.
        df = pd.DataFrame([
            {"Player": "QB_Y", "Team": "Y", "Position": "QB", "Total Fpts": 300.0},
            {"Player": "TE_Y", "Team": "Y", "Position": "TE", "Total Fpts": 150.0},
        ])
        for col in ("Active Fpts", "Round", "Pick", "Pick-Num"):
            df[col] = 0
        df["Keeper"] = False
        df["Rank"] = ""
        roles = compute_roster_roles(df)
        assert set(roles.unique()) == {"Starter"}
        assert roles.tolist() == ["Starter", "Starter"]
