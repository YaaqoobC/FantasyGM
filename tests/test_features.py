import sys
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.features.build_features import (
    FEATURE_COLUMNS, OPPONENT_FEATURE, TARGET_STATS,
    build_features, save_features, training_ready_rows, validate_features,
)


def make_games():
    # Four teams, two players each. Change opponents for the last round.
    rows = []
    teams = {"LAL": (1, 2), "BOS": (3, 4), "GSW": (5, 6), "NYK": (7, 8)}
    for i, date in enumerate(pd.date_range("2025-01-01", periods=12, freq="2D")):
        pairs = [("LAL", "BOS"), ("GSW", "NYK")]
        if i == 11:
            pairs = [("LAL", "GSW"), ("BOS", "NYK")]
        points = [10 + i, 20, 40 + i, 5, 60 + i, 15, 80 + i, 25]
        for pair_id, (first, second) in enumerate(pairs):
            for team, opponent in [(first, second), (second, first)]:
                home = (team == first) == (i % 2 == 0)
                for player_id in teams[team]:
                    rows.append({
                        "player_id": player_id, "player_name": f"Player {player_id}",
                        "team_id": teams[team][0], "season": "2024-25",
                        "game_id": f"{i:02d}-{pair_id}", "game_date": date,
                        "matchup": f"{team} {'vs.' if home else '@'} {opponent}",
                        "min": 30, "pts": points[player_id - 1],
                        "reb": 5, "ast": 4, "stl": 1, "blk": 1, "tov": 2,
                        "fgm": 4, "fga": 10, "fg3m": 1, "ftm": 1, "fta": 2,
                    })
    return pd.DataFrame(rows).sort_values(
        ["player_id", "game_date"]
    ).reset_index(drop=True)


def test_no_future_data_leakage():
    df = make_games()
    result = build_features(df)

    # Matchup validation
    assert result.loc[0, "opponent"] == "BOS"
    assert result.loc[0, "is_home"] == 1

    assert result.loc[1, "opponent"] == "BOS"
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
        for column in ["is_home", "opponent", OPPONENT_FEATURE, "opponent_games_played"]:
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


class OpponentFeatureTests(unittest.TestCase):
    def test_team_totals_opponent_identity_and_join_cardinality(self):
        games = make_games()
        result = build_features(games)
        # BOS conceded LAL's 30..39 points; LAL conceded BOS's 45..54.
        self.assertEqual(result.loc[10, OPPONENT_FEATURE], 34.5)
        bos = result[result["player_id"] == 3].reset_index(drop=True)
        self.assertEqual(bos.loc[10, OPPONENT_FEATURE], 49.5)
        # The last game's opponent is GSW, which conceded NYK's 106..115.
        self.assertEqual(result.loc[11, OPPONENT_FEATURE], 110.5)
        self.assertEqual(result.loc[10, "opponent_games_played"], 10)
        self.assertEqual(len(result), len(games))
        pd.testing.assert_frame_equal(
            result[["player_id", "game_id"]], games[["player_id", "game_id"]]
        )
        self.assertTrue(result.loc[:9, OPPONENT_FEATURE].isna().all())

    def test_current_and_future_results_cannot_change_pregame_features(self):
        games = make_games()
        original = build_features(games)
        # Change both teams' scores in round 10 and every later result.
        cutoff = pd.Timestamp("2025-01-21")
        games.loc[games["game_date"] >= cutoff, "pts"] += 100
        changed = build_features(games)
        before_or_at = original["game_date"] <= cutoff
        pd.testing.assert_frame_equal(
            original.loc[before_or_at, FEATURE_COLUMNS],
            changed.loc[before_or_at, FEATURE_COLUMNS],
        )
        # Earlier games must affect a later opponent's historical average.
        self.assertNotEqual(original.loc[11, OPPONENT_FEATURE], changed.loc[11, OPPONENT_FEATURE])

    def test_unsorted_input_and_season_resets(self):
        games = make_games()
        following = games.copy()
        following["season"] = "2025-26"
        following["game_id"] = "next-" + following["game_id"]
        following["game_date"] += pd.DateOffset(years=1)
        following["pts"] += 100
        combined = pd.concat([games, following], ignore_index=True)
        expected = build_features(combined)
        actual = build_features(combined.sample(frac=1, random_state=7))
        pd.testing.assert_frame_equal(expected, actual)
        next_player = actual[
            (actual["player_id"] == 1) & (actual["season"] == "2025-26")
        ].reset_index(drop=True)
        self.assertTrue(next_player.loc[:9, OPPONENT_FEATURE].isna().all())
        self.assertEqual(next_player.loc[10, OPPONENT_FEATURE], 234.5)
        self.assertEqual(next_player.loc[0, "games_played"], 0)

    def test_opponent_warmup_and_export(self):
        games = make_games()
        # Remove two complete GSW/NYK games; LAL retains its full history.
        games = games[~games["game_id"].isin(["00-1", "01-1"])].copy()
        result = build_features(games)
        lal_last = result[(result["player_id"] == 1) & (result["games_played"] == 11)]
        self.assertEqual(lal_last["opponent_games_played"].iloc[0], 9)
        self.assertTrue(lal_last[OPPONENT_FEATURE].isna().all())
        validate_features(result)
        ready = training_ready_rows(result)
        self.assertFalse(((ready["player_id"] == 1) & (ready["games_played"] == 11)).any())
        with TemporaryDirectory() as directory:
            with patch("src.features.build_features.PROCESSED_DIR", Path(directory)):
                save_features(result)
            saved = pd.read_csv(Path(directory) / "player_game_features.csv")
        self.assertEqual(len(FEATURE_COLUMNS), 52)
        self.assertEqual(len(saved), len(ready))
        self.assertEqual(saved.columns.tolist(), [
            "player_id", "player_name", "season", "game_id", "game_date", "opponent",
            *FEATURE_COLUMNS, *TARGET_STATS,
        ])
        self.assertFalse(saved[FEATURE_COLUMNS].isna().any().any())

    def test_invalid_pairings_duplicates_and_missing_scores(self):
        games = make_games()
        cases = [
            (games[games["team_id"] != 3], "exactly two teams"),
            (pd.concat([games, games.iloc[:1]]), "Duplicate player-game"),
            (games.assign(pts=float("nan")), "Missing values"),
            (games.assign(pts=float("inf")), "finite nonnegative"),
        ]
        for invalid, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    build_features(invalid)
        wrong_matchup = games.copy()
        wrong_matchup.loc[wrong_matchup["team_id"] == 3, "matchup"] = "BOS @ NYK"
        with self.assertRaisesRegex(ValueError, "reciprocal matchups"):
            build_features(wrong_matchup)

    def test_ambiguous_same_day_games_are_rejected(self):
        games = make_games()
        games.loc[games["game_id"].str.startswith("01-"), "game_date"] = pd.Timestamp("2025-01-01")
        with self.assertRaisesRegex(ValueError, "same date"):
            build_features(games)

    def test_missing_or_invalid_ready_opponent_feature_is_rejected(self):
        result = build_features(make_games())
        for value, message in [(float("nan"), "Missing values"), (-1, "finite"), (float("inf"), "finite")]:
            with self.subTest(value=value):
                invalid = result.copy()
                invalid.loc[10, OPPONENT_FEATURE] = value
                with self.assertRaisesRegex(ValueError, message):
                    validate_features(invalid)


if __name__ == "__main__":
    unittest.main()
