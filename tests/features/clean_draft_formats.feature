Feature: Multi-Format Draft CSV Cleaning
  As a fantasy football analyst
  I want clean_draft.py to handle CSV files from different years
  So that I can analyse draft data consistently across all seasons

  # ---------------------------------------------------------------------------
  # Format B: flat pre-cleaned CSVs (2021–2024)
  # ---------------------------------------------------------------------------

  Background:
    Given the 2021 draft CSV exists
    And the 2020 draft CSV exists

  Scenario: Format B cleaned CSV has the expected output schema
    When the cleaning script is run on the 2021 CSV
    Then the 2021 cleaned CSV contains all 12 expected columns

  Scenario: Format B has NaN for columns not present in source
    When the cleaning script is run on the 2021 CSV
    Then the 2021 cleaned CSV has empty Rank values
    And the 2021 cleaned CSV has empty Total Fpts values
    And the 2021 cleaned CSV has empty Active Fpts values

  Scenario: Format B Pick-Num is computed correctly
    When the cleaning script is run on the 2021 CSV
    Then round 2 pick 1 in the 2021 CSV has Pick-Num 13

  Scenario: Format B Position values are valid
    When the cleaning script is run on the 2021 CSV
    Then the 2021 cleaned CSV Position column contains only recognised positions

  Scenario: Format B player names have no asterisk prefix
    When the cleaning script is run on the 2021 CSV
    Then no Player value in the 2021 cleaned CSV starts with an asterisk

  # ---------------------------------------------------------------------------
  # Format C: 5-col alternating CSVs (2020)
  # ---------------------------------------------------------------------------

  Scenario: Format C cleaned CSV has the expected output schema
    When the cleaning script is run on the 2020 CSV
    Then the 2020 cleaned CSV contains all 12 expected columns

  Scenario: Format C has NaN for columns not present in source
    When the cleaning script is run on the 2020 CSV
    Then the 2020 cleaned CSV has empty Rank values
    And the 2020 cleaned CSV has empty Total Fpts values
    And the 2020 cleaned CSV has empty Active Fpts values

  Scenario: Format C Pick-Num is computed correctly
    When the cleaning script is run on the 2020 CSV
    Then round 2 pick 1 in the 2020 CSV has Pick-Num 13

  Scenario: Format C Position is extracted from player string
    When the cleaning script is run on the 2020 CSV
    Then the 2020 cleaned CSV Position column contains only recognised positions

  Scenario: Format C player names have no asterisk prefix
    When the cleaning script is run on the 2020 CSV
    Then no Player value in the 2020 cleaned CSV starts with an asterisk
