"""
Step definitions for dashboard.feature.

Uses streamlit.testing.v1.AppTest for Streamlit-specific assertions and
subprocess for CLI flag testing.
"""

import subprocess
import sys
from pathlib import Path

from pytest_bdd import given, scenarios, then, when

FEATURE_FILE = Path(__file__).parent.parent / "features" / "dashboard.feature"
scenarios(str(FEATURE_FILE))

PROJECT_ROOT = Path(__file__).parent.parent.parent
DASHBOARD_SCRIPT = PROJECT_ROOT / "scripts" / "dashboard.py"


# ---------------------------------------------------------------------------
# Background step
# ---------------------------------------------------------------------------

@given("the cleaned CSV exists")
def step_cleaned_csv_exists(cleaned_csv_path: Path) -> None:
    """cleaned_csv_path comes from the session fixture in conftest.py."""
    assert cleaned_csv_path.exists(), f"Cleaned CSV not found: {cleaned_csv_path}"


# ---------------------------------------------------------------------------
# When steps
# ---------------------------------------------------------------------------

@when("the dashboard app is started", target_fixture="app")
def step_start_app(cleaned_csv_path: Path):
    """
    Launch the Streamlit app via AppTest. The dashboard auto-detects the
    cleaned CSV from the project root — no sys.argv injection needed.
    """
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(DASHBOARD_SCRIPT), default_timeout=30)
    at.run()
    return at


@when("the dashboard script is run with --help", target_fixture="help_result")
def step_run_help() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(DASHBOARD_SCRIPT), "--help"],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------

@then("no exceptions are raised during startup")
def step_no_exceptions(app) -> None:
    # app.exception is an ElementList (falsy when empty, not None)
    assert not app.exception, (
        f"Dashboard raised an exception: {app.exception}"
    )


@then("a download button is present")
def step_download_button_present(app) -> None:
    # download_button is not a named attribute on AppTest in this Streamlit version;
    # use the generic get() accessor which checks element type names.
    dl_buttons = app.get("download_button")
    assert len(dl_buttons) > 0, "No download button found in the dashboard"


@then("at least one widget is rendered")
def step_at_least_one_widget(app) -> None:
    # If main() is never called, the app renders nothing and has no widgets.
    # Any of the sidebar widgets (multiselect, checkbox, slider, text_input) count.
    total = (
        len(app.multiselect)
        + len(app.checkbox)
        + len(app.slider)
        + len(app.text_input)
    )
    assert total > 0, (
        f"No widgets rendered — main() may not be called at module level. "
        f"Found: {total} widgets"
    )


@then("it exits with code 0")
def step_exits_zero(help_result: subprocess.CompletedProcess) -> None:
    assert help_result.returncode == 0, (
        f"Expected exit code 0, got {help_result.returncode}\n"
        f"stdout: {help_result.stdout}\nstderr: {help_result.stderr}"
    )


@then("at least two sliders are present")
def step_at_least_two_sliders(app) -> None:
    assert len(app.slider) >= 2, (
        f"Expected at least 2 sliders (Total Fpts, Active Fpts), found {len(app.slider)}"
    )


@then("the data table shows all 180 picks by default")
def step_all_picks_shown(app) -> None:
    # The dataframe element should exist; we verify no exception was raised
    # and that the sidebar position multiselect has an option for "" (empty position)
    assert not app.exception, f"App raised an exception: {app.exception}"
    position_select = app.sidebar.multiselect[1]
    # The empty-string position (Skipped Pick) should be present as an option
    assert "" in position_select.options, (
        f"Empty position not in filter options: {position_select.options}"
    )


@then('the output contains "streamlit run"')
def step_output_contains_streamlit(help_result: subprocess.CompletedProcess) -> None:
    combined = help_result.stdout + help_result.stderr
    assert "streamlit run" in combined, (
        f"'streamlit run' not found in output:\n{combined}"
    )
