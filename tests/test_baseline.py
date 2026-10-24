import math
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evaluation.baseline import (
    DEVELOPMENT_SEASONS, TEST_SEASON, TRAIN_SEASONS, VALIDATION_SEASON,
    evaluate_predictions, fantasy_points, load_development_games,
    rolling_predictions, run_baseline, season_date_ranges,
)
from src.features.build_features import TARGET_STATS, build_features, training_ready_rows
from test_features import make_games


def development_games(include_test=False):
    seasons = (*DEVELOPMENT_SEASONS, TEST_SEASON) if include_test else DEVELOPMENT_SEASONS
    frames = []
    for season in seasons:
        games = make_games()
        games["season"] = season
        games["game_id"] = season + "-" + games["game_id"]
        # Synthetic January games fall within the labelled season.
        games["game_date"] += pd.DateOffset(years=int(season[:4]) - 2024)
        frames.append(games)
    return pd.concat(frames, ignore_index=True)


class BaselineTests(unittest.TestCase):
    def test_script_and_module_commands_produce_the_same_report(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "games.db"
            with sqlite3.connect(path) as connection:
                development_games(include_test=True).to_sql(
                    "player_game_stats", connection, index=False
                )
            script = subprocess.run(
                [sys.executable, str(ROOT / "src/evaluation/baseline.py"), "--db", str(path)],
                cwd=directory, capture_output=True, text=True, timeout=30,
            )
            module = subprocess.run(
                [sys.executable, "-m", "src.evaluation.baseline", "--db", str(path)],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
        self.assertEqual(script.returncode, 0, script.stderr)
        self.assertEqual(module.returncode, 0, module.stderr)
        self.assertEqual(script.stdout, module.stdout)

    def test_fantasy_scoring_weights(self):
        # Score one unit of each statistic independently, including penalties.
        stats = pd.DataFrame(0.0, index=TARGET_STATS, columns=TARGET_STATS)
        for stat in TARGET_STATS:
            stats.loc[stat, stat] = 1
        self.assertEqual(fantasy_points(stats).tolist(), [1, 1, 2, 4, 4, -2, 2, -1, 1, 1, -1])

    def test_known_errors_and_fantasy_error_cancellation(self):
        actual = pd.DataFrame(0.0, index=[5, 9], columns=TARGET_STATS)
        predicted = actual.copy()
        predicted["pts"] = [3.0, 4.0]
        predicted["tov"] = [1.5, 2.0]
        metrics = evaluate_predictions(actual, predicted)
        self.assertEqual(metrics["pts"]["mae"], 3.5)
        self.assertAlmostEqual(metrics["pts"]["rmse"], math.sqrt(12.5))
        self.assertEqual(metrics["fantasy_points"], {"mae": 0.0, "rmse": 0.0})

    def test_metrics_reject_misaligned_missing_or_invalid_inputs(self):
        actual = pd.DataFrame(0.0, index=[0, 1], columns=TARGET_STATS)
        cases = [
            (actual.iloc[::-1], "identical unique indices"),
            (actual.drop(columns="pts"), "Missing statistics"),
            (actual.assign(pts=float("nan")), "finite numeric"),
            (actual.assign(pts=float("inf")), "finite numeric"),
            (actual.assign(pts="3"), "finite numeric"),
        ]
        for predicted, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    evaluate_predictions(actual, predicted)
        with self.assertRaisesRegex(ValueError, "empty"):
            evaluate_predictions(actual.iloc[:0], actual.iloc[:0])
        duplicate = actual.set_axis([0, 0])
        with self.assertRaisesRegex(ValueError, "unique indices"):
            evaluate_predictions(duplicate, duplicate)

    def test_splits_reject_missing_unexpected_and_overlapping_seasons(self):
        games = development_games()
        cases = [
            (games[games["season"] != TRAIN_SEASONS[0]], "Season mismatch"),
            (development_games(include_test=True), "Season mismatch"),
            (games.assign(game_date=pd.Timestamp("2025-01-01")), "overlap"),
            (games.assign(game_date=pd.NaT), "missing"),
        ]
        for invalid, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    season_date_ranges(invalid, DEVELOPMENT_SEASONS)
        # Even different times on the boundary day must stay in the same split.
        boundary = games.copy()
        boundary.loc[boundary["season"] == VALIDATION_SEASON, "game_date"] = (
            games.loc[games["season"] == TRAIN_SEASONS[-1], "game_date"].max()
            + pd.Timedelta(hours=12)
        )
        with self.assertRaisesRegex(ValueError, "overlap"):
            season_date_ranges(boundary, DEVELOPMENT_SEASONS)

    def test_loader_excludes_test_statistics_and_checks_test_boundary(self):
        games = development_games(include_test=True)
        # Invalid held-out stats would break the builder if they were loaded.
        games["pts"] = games["pts"].astype(object)
        games.loc[games["season"] == TEST_SEASON, "pts"] = "RESERVED"
        with TemporaryDirectory() as directory:
            path = Path(directory) / "games.db"
            with sqlite3.connect(path) as connection:
                games.to_sql("player_game_stats", connection, index=False)
            loaded = load_development_games(path)
            self.assertEqual(set(loaded["season"]), set(DEVELOPMENT_SEASONS))
            self.assertNotIn("RESERVED", loaded["pts"].values)
            # A bad test date is still rejected without examining its scores.
            with sqlite3.connect(path) as connection:
                connection.execute(
                    "UPDATE player_game_stats SET game_date=? WHERE season=?",
                    ("2024-01-01", TEST_SEASON),
                )
            with self.assertRaisesRegex(ValueError, "overlap"):
                load_development_games(path)
        with self.assertRaises(FileNotFoundError):
            load_development_games(Path(directory) / "missing.db")

    def test_reproducible_validation_report_and_warmup(self):
        games = development_games()
        report = run_baseline(games)
        self.assertEqual(report, run_baseline(games.sample(frac=1, random_state=7)))
        self.assertEqual(report["training_seasons"], list(TRAIN_SEASONS))
        self.assertEqual(report["reserved_test_season"], TEST_SEASON)
        self.assertNotIn(TEST_SEASON, report["seasons"])
        self.assertEqual(report["seasons"][VALIDATION_SEASON]["eligible_rows"], 16)
        self.assertEqual(report["seasons"][VALIDATION_SEASON]["warmup_excluded_rows"], 80)
        self.assertEqual(set(report["validation_metrics"]), {*TARGET_STATS, "fantasy_points"})
        # Four of eight players gain one point per game: mean lags by 5.5.
        self.assertEqual(report["validation_metrics"]["pts"]["mae"], 2.75)
        self.assertEqual(report["validation_metrics"]["reb"]["rmse"], 0)

    def test_current_and_future_results_do_not_change_earlier_predictions(self):
        games = development_games()
        ready = training_ready_rows(build_features(games))
        original = ready[ready["season"] == VALIDATION_SEASON]
        cutoff = original["game_date"].min()
        changed_games = games.copy()
        changed_games.loc[changed_games["game_date"] >= cutoff, "pts"] += 100
        changed = training_ready_rows(build_features(changed_games))
        current = original["game_date"] == cutoff
        pd.testing.assert_frame_equal(
            rolling_predictions(original.loc[current]),
            rolling_predictions(changed.loc[original.loc[current].index]),
        )
        # Later predictions should incorporate the now-completed earlier game.
        self.assertFalse(rolling_predictions(original).equals(rolling_predictions(changed.loc[original.index])))

    def test_empty_eligible_season_is_rejected(self):
        games = development_games()
        games = games[
            (games["season"] != VALIDATION_SEASON)
            | (games["game_date"] <= pd.Timestamp("2025-01-19"))
        ]
        with self.assertRaisesRegex(ValueError, "Each development season"):
            run_baseline(games)


if __name__ == "__main__":
    unittest.main()
