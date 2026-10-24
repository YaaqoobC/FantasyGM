"""Validation-only benchmark: predict each stat from its previous 10 games."""

import argparse
import json
from pathlib import Path
import sqlite3
import sys

import pandas as pd

# Direct script execution puts src/evaluation, rather than the repository root,
# on the import path. Module execution already resolves the src package.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.features.build_features import (
    DB_PATH, TARGET_STATS, build_features, training_ready_rows, validate_features,
)

# Fixed partitions: adding data must not silently move the evaluation boundary.
TRAIN_SEASONS = ("2020-21", "2021-22", "2022-23", "2023-24")
VALIDATION_SEASON = "2024-25"
TEST_SEASON = "2025-26"
DEVELOPMENT_SEASONS = (*TRAIN_SEASONS, VALIDATION_SEASON)
SCORING_WEIGHTS = {
    "pts": 1, "reb": 1, "ast": 2, "stl": 4, "blk": 4, "tov": -2,
    "fgm": 2, "fga": -1, "fg3m": 1, "ftm": 1, "fta": -1,
}


def season_date_ranges(games, expected_seasons):
    """Reject missing partitions and date overlap, even with plausible labels."""
    required = {"season", "game_date"}
    if not required.issubset(games.columns):
        raise ValueError("Season splits require season and game_date columns")
    if games[list(required)].isna().any().any():
        raise ValueError("Season splits cannot contain missing seasons or dates")
    actual = set(games["season"])
    expected = set(expected_seasons)
    if actual != expected:
        raise ValueError(
            f"Season mismatch: missing={sorted(expected - actual)}, "
            f"unexpected={sorted(actual - expected)}"
        )
    dates = games[["season", "game_date"]].copy()
    dates["game_date"] = pd.to_datetime(dates["game_date"], format="mixed", errors="raise")
    if dates["game_date"].isna().any():
        raise ValueError("Season splits cannot contain missing dates")
    dates["game_date"] = dates["game_date"].dt.normalize()
    ranges = dates.groupby("season")["game_date"].agg(["min", "max"])
    for earlier, later in zip(expected_seasons, expected_seasons[1:]):
        if ranges.loc[earlier, "max"] >= ranges.loc[later, "min"]:
            raise ValueError(f"Season dates overlap or are out of order: {earlier}, {later}")
    return {
        season: {
            "first_date": ranges.loc[season, "min"].date().isoformat(),
            "last_date": ranges.loc[season, "max"].date().isoformat(),
        }
        for season in expected_seasons
    }


def load_development_games(db_path=DB_PATH):
    """Read train/validation results only; inspect test dates, never its stats."""
    db_path = Path(db_path).resolve()
    if not db_path.is_file():
        raise FileNotFoundError(f"Database not found: {db_path}")
    with sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True) as connection:
        dates = pd.read_sql_query(
            "SELECT DISTINCT season, game_date FROM player_game_stats", connection
        )
        season_date_ranges(dates, (*DEVELOPMENT_SEASONS, TEST_SEASON))
        placeholders = ",".join("?" for _ in DEVELOPMENT_SEASONS)
        return pd.read_sql_query(
            f"SELECT * FROM player_game_stats WHERE season IN ({placeholders})",
            connection, params=DEVELOPMENT_SEASONS,
        )


def checked_stats(frame):
    """Keep metric inputs numeric, finite, and explicit about missing targets."""
    missing = set(TARGET_STATS) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing statistics: {sorted(missing)}")
    stats = frame[TARGET_STATS]
    if stats.empty:
        raise ValueError("Cannot score an empty set of predictions")
    if (
        not all(pd.api.types.is_numeric_dtype(stats[column]) for column in TARGET_STATS)
        or stats.isna().any().any()
        or stats.isin([float("inf"), float("-inf")]).any().any()
    ):
        raise ValueError("Statistics must be finite numeric values without missing data")
    return stats


def fantasy_points(stats):
    """Convert each complete stat line using the documented league weights."""
    stats = checked_stats(stats)
    return stats.mul(pd.Series(SCORING_WEIGHTS)).sum(axis=1)


def rolling_predictions(features):
    """Use pregame 10-game averages as predictions without fitting parameters."""
    predictions = features[[f"{stat}_avg_10" for stat in TARGET_STATS]].copy()
    predictions.columns = TARGET_STATS
    return checked_stats(predictions)


def evaluate_predictions(actual, predicted):
    """Measure per-stat and fantasy errors for the same player-game rows."""
    if not actual.index.is_unique or not actual.index.equals(predicted.index):
        raise ValueError("Actual and predicted rows must have identical unique indices")
    actual = checked_stats(actual)
    predicted = checked_stats(predicted)
    errors = predicted - actual
    # Score each player's predicted stat line first; stat errors can cancel.
    errors["fantasy_points"] = fantasy_points(predicted) - fantasy_points(actual)
    return pd.DataFrame({
        "mae": errors.abs().mean(),
        "rmse": errors.pow(2).mean().pow(0.5),
    }).to_dict(orient="index")


def run_baseline(games):
    """Build eligible development examples and score only the validation season."""
    ranges = season_date_ranges(games, DEVELOPMENT_SEASONS)
    features = build_features(games)
    validate_features(features)
    ready = training_ready_rows(features)
    counts = ready.groupby("season").size()
    if any(counts.get(season, 0) == 0 for season in DEVELOPMENT_SEASONS):
        raise ValueError("Each development season must have training-ready examples")
    validation = ready[ready["season"] == VALIDATION_SEASON]
    raw_counts = games.groupby("season").size()
    return {
        "benchmark": "previous_10_games_mean",
        "training_seasons": list(TRAIN_SEASONS),
        "validation_season": VALIDATION_SEASON,
        "reserved_test_season": TEST_SEASON,
        "seasons": {
            season: {
                **ranges[season],
                "source_rows": int(raw_counts[season]),
                "eligible_rows": int(counts[season]),
                "warmup_excluded_rows": int(raw_counts[season] - counts[season]),
            }
            for season in DEVELOPMENT_SEASONS
        },
        "validation_metrics": evaluate_predictions(validation, rolling_predictions(validation)),
    }


def main():
    """Print the validation report without saving datasets or model artifacts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DB_PATH, help="Read-only SQLite source")
    args = parser.parse_args()
    report = run_baseline(load_development_games(args.db))
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
