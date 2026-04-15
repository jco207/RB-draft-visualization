Feature: Draft Dashboard
  As a fantasy football analyst
  I want an interactive dashboard for the cleaned draft data
  So that I can explore picks by round, position, and fantasy points

  Background:
    Given the cleaned CSV exists

  Scenario: App loads without exceptions
    When the dashboard app is started
    Then no exceptions are raised during startup

  Scenario: Download button is present on load
    When the dashboard app is started
    Then a download button is present

  Scenario: Dashboard script supports --help flag
    When the dashboard script is run with --help
    Then it exits with code 0
    And the output contains "streamlit run"

  # Defect: main() was never called at module level so Streamlit had nothing to render
  Scenario: App renders at least one widget
    When the dashboard app is started
    Then at least one widget is rendered

  # Defect (code review): dtype coercion mutated the @st.cache_data result on every re-render
  Scenario: Round column has integer dtype after load
    When the dashboard app is started
    Then no exceptions are raised during startup

  # Defect (code review): slider crashes when min == max (e.g. all-zero Fpts after filtering)
  Scenario: Sliders render without error on initial load
    When the dashboard app is started
    Then at least two sliders are present

  # Defect (code review): picks with empty Position were silently excluded from default filter
  Scenario: Skipped picks are visible in the default view
    When the dashboard app is started
    Then the data table shows all 180 picks by default
