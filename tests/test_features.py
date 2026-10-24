import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.features.build_features import build_features, validate_features


def make_games():
    # Simulate 12 games for a single player.
    df = pd.DataFrame({
        "player_id": [1] * 12,
        "season": ["2024-25"] * 12,
        "game_id": [str(i) for i in range(12)],
        "game_date": pd.date_range(
            "2025-01-01", periods=12, freq="2D"
        ),
        "min": [30] * 12,
        "pts": list(range(10, 22)),
        "reb": [5] * 12,
        "ast": [4] * 12,
        "stl": [1] * 12,
        "blk": [1] * 12,
        "tov": [2] * 12,
        "fgm": [4] * 12,
        "fga": [10] * 12,
        "fg3m": [1] * 12,
        "ftm": [1] * 12,
        "fta": [2] * 12,
        "matchup": ["LAL vs. BOS", "LAL @ GSW"] * 6,
    })

    return df


def test_no_future_data_leakage():
    df = make_games()
    result = build_features(df)

    # Matchup validation
    assert result.loc[0, "opponent"] == "BOS"
    assert result.loc[0, "is_home"] == 1

    assert result.loc[1, "opponent"] == "GSW"
    assert result.loc[1, "is_home"] == 0

    # Game 4 should only use games 1, 2, and 3.
    assert result.loc[3, "pts_avg_3"] == 11.0

    # Game 11 uses points from the first 10 games.
    assert result.loc[10, "pts_avg_10"] == 14.5

    # Two days between games means one full rest day.
    assert result.loc[1, "rest_days"] == 1

    # Changing the final game's result must not change
    # any features for the final game.
    original = result.loc[11, "pts_avg_5"]

    df.loc[11, "pts"] = 999
    changed = build_features(df)

    assert changed.loc[11, "pts_avg_5"] == original


class FeatureValidationTests(unittest.TestCase):
    def setUp(self):
        self.features = build_features(make_games())

    def test_valid_features_and_leakage(self):
        validate_features(self.features)
        test_no_future_data_leakage()

    def test_missing_matchup_columns(self):
        for column in ["is_home", "opponent"]:
            with self.subTest(column=column):
                with self.assertRaisesRegex(ValueError, "Missing features"):
                    validate_features(self.features.drop(columns=column))

    def test_invalid_home_flags(self):
        for value in [None, 2, -1, "1"]:
            with self.subTest(value=value):
                invalid = self.features.astype({"is_home": object})
                invalid.loc[0, "is_home"] = value
                with self.assertRaisesRegex(ValueError, "is_home"):
                    validate_features(invalid)

    def test_invalid_opponents(self):
        for value in [None, "", "bos", "BOSTON", " BOS", 123]:
            with self.subTest(value=value):
                invalid = self.features.astype({"opponent": object})
                invalid.loc[0, "opponent"] = value
                with self.assertRaisesRegex(ValueError, "opponent"):
                    validate_features(invalid)

    def test_missing_targets(self):
        with self.assertRaisesRegex(ValueError, "Missing prediction targets"):
            validate_features(self.features.drop(columns="pts"))
        self.features.loc[11, "pts"] = float("nan")
        with self.assertRaisesRegex(ValueError, "Missing prediction targets"):
            validate_features(self.features)

    def test_missing_history_and_empty_data(self):
        with self.assertRaisesRegex(ValueError, "Feature dataset is empty"):
            validate_features(self.features.iloc[:0])
        with self.assertRaisesRegex(ValueError, "No players have sufficient history"):
            validate_features(self.features.iloc[:10])
        self.features.loc[11, "pts_avg_10"] = float("nan")
        with self.assertRaisesRegex(ValueError, "Missing values"):
            validate_features(self.features)


if __name__ == "__main__":
    unittest.main()
