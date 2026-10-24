import sqlite3
from pathlib import Path

import pandas as pd

# Project paths
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "nba.db"
PROCESSED_DIR = ROOT / "data" / "processed"

# Stats that our neural networks will predict
TARGET_STATS = [
    "pts", "reb", "ast", "stl", "blk",
    "tov", "fgm", "fga", "fg3m", "ftm", "fta"
]

# Minutes is a useful input, but not currently a target
HISTORICAL_STATS = ["min"] + TARGET_STATS

ROLLING_WINDOWS = [3, 5, 10]

def load_game_data() -> pd.DataFrame:
    """Load historical player games from SQLite."""

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(
            "SELECT * FROM player_game_stats",
            conn
        )

    if df.empty:
        raise ValueError("The database contains no games")

    df["game_date"] = pd.to_datetime(
        df["game_date"],
        format="mixed",
        errors="raise"
    )

    df = df.sort_values(
        ["player_id", "season", "game_date", "game_id"]
    ).reset_index(drop=True)

    return df

def add_matchup_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract opponent and home/away information
    from the NBA matchup string.
    """

    df = df.copy()

    # Example: "LAL vs. BOS" or "LAL @ GSW"
    matchup_parts = df["matchup"].str.extract(
        r"^\s*([A-Z]{3})\s+(vs\.|@)\s+([A-Z]{3})\s*$"
    )

    # Verify every matchup was parsed successfully.
    if matchup_parts.isna().any().any():
        raise ValueError("Invalid or missing matchup format")

    df["opponent"] = matchup_parts[2]

    # Home = 1, Away = 0
    df["is_home"] = (
        matchup_parts[1] == "vs."
    ).astype(int)

    return df

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construct pregame features using historical games only.

    Each output row corresponds to one player-game.
    """

    df = df.copy()

    # Add matchup information
    df = add_matchup_features(df)

    # Process a player's history separately per season.
    groups = df.groupby(
        ["player_id", "season"],
        sort=False
    )

    # Number of games completed before this one
    df["games_played"] = groups.cumcount()

    # Rest between the previous and current games
    df["rest_days"] = (
        groups["game_date"]
        .diff()
        .dt.days - 1
    )

    # Create historical features for every stat.
    for stat in HISTORICAL_STATS:
        # Exclude the current game's result.
        previous = groups[stat].shift(1)

        # Season-to-date mean, excluding current game.
        df[f"{stat}_season_avg"] = (
            previous.groupby(
                [df["player_id"], df["season"]]
            )
            .transform(
                lambda s: s.expanding(min_periods=1).mean()
            )
        )

        # Rolling historical averages.
        for window in ROLLING_WINDOWS:
            feature_name = f"{stat}_avg_{window}"

            df[feature_name] = (
                previous.groupby(
                    [df["player_id"], df["season"]]
                )
                .transform(
                    lambda s: s.rolling(
                        window=window,
                        min_periods=window
                    ).mean()
                )
            )

    return df

def validate_features(df: pd.DataFrame):
    """Verify our engineered data is usable."""

    if df.empty:
        raise ValueError("Feature dataset is empty")

    expected = [
        f"{stat}_avg_{window}"
        for stat in HISTORICAL_STATS
        for window in ROLLING_WINDOWS
    ]

    expected += [
        f"{stat}_season_avg"
        for stat in HISTORICAL_STATS
    ]

    expected += ["games_played", "rest_days", "is_home"]

    missing = set(expected + ["opponent"]) - set(df.columns)
    if missing:
        raise ValueError(f"Missing features: {missing}")

    # Matchup context must be valid even during the history warm-up.
    if not df["is_home"].isin([0, 1]).all():
        raise ValueError("is_home must contain only 0 or 1")

    valid_opponents = (
        df["opponent"].astype("string")
        .str.fullmatch(r"[A-Z]{3}", na=False)
    )
    if not valid_opponents.all():
        raise ValueError("opponent must contain three uppercase letters")

    missing_targets = set(TARGET_STATS) - set(df.columns)
    if missing_targets:
        raise ValueError(f"Missing prediction targets: {missing_targets}")

    # After 10 previous games, all rolling features
    # should be available.
    ready = df[df["games_played"] >= 10]

    if ready.empty:
        raise ValueError("No players have sufficient history")

    if ready[expected].isna().any().any():
        raise ValueError(
            "Missing values in training-ready features"
        )

    # Every target must also be available.
    if ready[TARGET_STATS].isna().any().any():
        raise ValueError("Missing prediction targets")

def save_features(df: pd.DataFrame):
    """Save the model-ready dataset as CSV."""

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Require 10 previous games for our first experiment.
    df = df[df["games_played"] >= 10].copy()

    # Explicitly identify which columns are model inputs.
    feature_columns = (
        ["games_played", "rest_days", "is_home"]
        + [
            f"{stat}_season_avg"
            for stat in HISTORICAL_STATS
        ]
        + [
            f"{stat}_avg_{window}"
            for stat in HISTORICAL_STATS
            for window in ROLLING_WINDOWS
        ]
    )
    metadata_columns = [
        "player_id",
        "player_name",
        "season",
        "game_id",
        "game_date",
        "opponent"
    ]

    output_columns = (
        metadata_columns
        + feature_columns
        + TARGET_STATS
    )

    output_path = (
        PROCESSED_DIR / "player_game_features.csv"
    )

    df[output_columns].to_csv(
        output_path,
        index=False
    )

    print(f"Saved {len(df)} examples")
    print(f"Features per example: {len(feature_columns)}")
    print(f"Prediction targets: {len(TARGET_STATS)}")
    print(f"Output: {output_path}")

if __name__ == "__main__":
    print("Loading historical NBA games...")
    games = load_game_data()

    print(f"Loaded {len(games)} player-game records")

    print("Building historical features...")
    featured_games = build_features(games)

    validate_features(featured_games)
    save_features(featured_games)

    print("Feature building complete!")
