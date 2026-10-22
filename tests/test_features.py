import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.features.build_features import build_features


def test_no_future_data_leakage():
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

    print("Feature engineering tests passed!")


if __name__ == "__main__":
    test_no_future_data_leakage()
