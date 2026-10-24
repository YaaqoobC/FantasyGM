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
HISTORY_GAMES = 10
# EXPERIMENTAL: predictive value is unverified. This mixes defense with pace,
# schedule strength, overtime, and lineup changes; it is not defensive rating.
# Compare the same model with/without this input on identical chronological
# splits and rows before deciding whether to retain it.
OPPONENT_FEATURE = "opponent_pts_allowed_avg_10"
FEATURE_COLUMNS = (
    ["games_played", "rest_days", "is_home", OPPONENT_FEATURE]
    + [f"{stat}_season_avg" for stat in HISTORICAL_STATS]
    + [
        f"{stat}_avg_{window}"
        for stat in HISTORICAL_STATS
        for window in ROLLING_WINDOWS
    ]
)

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

def add_opponent_features(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate complete player logs into pregame opponent defense."""
    required = [
        "player_id", "game_id", "season", "game_date", "team_id",
        "matchup", "opponent", "pts",
    ]
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Missing opponent feature source columns: {missing}")
    if df[required].isna().any().any():
        raise ValueError("Missing values in opponent feature source data")
    if df.duplicated(["player_id", "game_id"]).any():
        raise ValueError("Duplicate player-game records")
    if (
        not pd.api.types.is_numeric_dtype(df["pts"])
        or df["pts"].isin([float("inf"), float("-inf")]).any()
        or (df["pts"] < 0).any()
    ):
        raise ValueError("Points must be finite nonnegative numbers")

    # Do not filter players by history before computing team totals.
    source = df.assign(team=df["matchup"].str.split().str[0])
    keys = ["season", "game_id", "team_id"]
    grouped = source.groupby(keys, sort=False)
    if grouped[["game_date", "team", "opponent"]].nunique().ne(1).any().any():
        raise ValueError("Inconsistent team-game date or matchup")
    teams = grouped.agg(
        game_date=("game_date", "first"),
        team=("team", "first"),
        opponent=("opponent", "first"),
        points=("pts", "sum"),
    ).reset_index()
    if teams.groupby(["season", "game_id"]).size().ne(2).any():
        raise ValueError("Each game must contain exactly two teams")
    if teams.duplicated(["season", "game_id", "team"]).any():
        raise ValueError("Team abbreviations must identify one team per game")

    # A team's points allowed are its opponent's scored points.
    opponents = teams[
        ["season", "game_id", "team", "opponent", "game_date", "points"]
    ].rename(columns={
        "team": "opponent", "opponent": "opponent_of_opponent",
        "game_date": "opponent_game_date", "points": "points_allowed",
    })
    teams = teams.merge(
        opponents, on=["season", "game_id", "opponent"],
        how="left", validate="one_to_one",
    )
    if (
        teams["team"].ne(teams["opponent_of_opponent"]).any()
        or teams["game_date"].ne(teams["opponent_game_date"]).any()
        or teams["points_allowed"].isna().any()
    ):
        raise ValueError("Game opponents must have reciprocal matchups and dates")

    teams = teams.sort_values(["team_id", "season", "game_date", "game_id"])
    # With dates rather than tipoff times, same-day ordering is ambiguous.
    if teams.duplicated(["team_id", "season", "game_date"]).any():
        raise ValueError("A team cannot have multiple games on the same date")
    history = teams.groupby(["team_id", "season"], sort=False)
    teams["opponent_games_played"] = history.cumcount()
    teams[OPPONENT_FEATURE] = history["points_allowed"].transform(
        lambda s: s.shift(1).rolling(HISTORY_GAMES, min_periods=HISTORY_GAMES).mean()
    )

    # Join the upcoming opponent's history, not the player's own team's history.
    summaries = teams[
        ["season", "game_id", "team", "opponent_games_played", OPPONENT_FEATURE]
    ].rename(columns={"team": "opponent"})
    result = df.merge(
        summaries, on=["season", "game_id", "opponent"],
        how="left", validate="many_to_one", sort=False,
    )
    if len(result) != len(df) or result["opponent_games_played"].isna().any():
        raise ValueError("Opponent join must preserve every player-game")
    result.index = df.index
    return result


def training_ready_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Require complete player and opponent histories without future imputation."""
    return df[
        (df["games_played"] >= HISTORY_GAMES)
        & (df["opponent_games_played"] >= HISTORY_GAMES)
    ]

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construct pregame features using historical games only.

    Each output row corresponds to one player-game.
    """

    df = df.copy()
    df["game_date"] = pd.to_datetime(df["game_date"], format="mixed", errors="raise")
    df = df.sort_values(
        ["player_id", "season", "game_date", "game_id"]
    ).reset_index(drop=True)

    # Add matchup information
    df = add_matchup_features(df)
    df = add_opponent_features(df)

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

    expected = FEATURE_COLUMNS

    missing = set(expected + ["opponent", "opponent_games_played"]) - set(df.columns)
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

    if (
        df["opponent_games_played"].isna().any()
        or (df["opponent_games_played"] < 0).any()
    ):
        raise ValueError("Invalid opponent history counts")

    # Warm-up is evaluated separately for player and opponent history.
    ready = training_ready_rows(df)

    if ready.empty:
        raise ValueError("No players have sufficient history")

    if ready[expected].isna().any().any():
        raise ValueError(
            "Missing values in training-ready features"
        )
    if (
        ready[OPPONENT_FEATURE].isin([float("inf"), float("-inf")]).any()
        or (ready[OPPONENT_FEATURE] < 0).any()
    ):
        raise ValueError("Opponent points allowed must be finite and nonnegative")

    # Every target must also be available.
    if ready[TARGET_STATS].isna().any().any():
        raise ValueError("Missing prediction targets")

def save_features(df: pd.DataFrame):
    """Save the model-ready dataset as CSV."""

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    validate_features(df)
    df = training_ready_rows(df).copy()

    # Explicitly identify which columns are model inputs.
    feature_columns = FEATURE_COLUMNS
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
