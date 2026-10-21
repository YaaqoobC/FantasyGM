from pathlib import Path
import argparse
import sqlite3

from nba_api.stats.endpoints import playergamelogs
from pandas import DataFrame


# Project Locations:
ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "nba.db"

# Constants:
REGULAR_SEASON_STR = "Regular Season"
REQUIRED_COLUMNS = [
    "PLAYER_ID", "PLAYER_NAME", "TEAM_ID",
    "GAME_ID", "GAME_DATE", "MATCHUP", "MIN",
    "PTS", "REB", "AST", "STL", "BLK",
    "TOV", "FGM", "FGA", "FG3M", "FTM", "FTA",
]

def get_season_stats(season: str):
    print(f"[YC-LOG] Getting NBA season stats for '{season}'")

    response = playergamelogs.PlayerGameLogs(
        season_nullable=season,
        season_type_nullable=REGULAR_SEASON_STR,
        timeout=60,
    )
    df : DataFrame = response.get_data_frames()[0]

    # Pre-process result:
    missingCols = set(REQUIRED_COLUMNS) - set(df.columns)
    if missingCols:
        raise ValueError(f"Missing API columns: {missingCols}")

    if df.empty:
        raise ValueError(f"No game logs returned for {season}")

    df = df.drop_duplicates(
        subset=["PLAYER_ID", "GAME_ID"]
    ).copy()

    df["SEASON"] = season

    return df

def save_raw_data(df: DataFrame, season: str):
    """
    Save a specific seasons stats into the Raw Data directory
    """
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    path = RAW_DATA_DIR / f"player_games_{season}.csv"
    df.to_csv(path, index=False)

    print(f"[YC-LOG] Saved {len(df)} rows to {path}")

def save_database(df: DataFrame):
    """
    Save a specific dataframe into the database
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS player_game_stats (
                player_id INTEGER NOT NULL,
                game_id TEXT NOT NULL,
                season TEXT NOT NULL,
                game_date TEXT NOT NULL,
                player_name TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                matchup TEXT NOT NULL,
                min REAL,
                pts REAL,
                reb REAL,
                ast REAL,
                stl REAL,
                blk REAL,
                tov REAL,
                fgm REAL,
                fga REAL,
                fg3m REAL,
                ftm REAL,
                fta REAL,
                PRIMARY KEY (player_id, game_id)
            )
        """)

        columns = [
            "PLAYER_ID", "GAME_ID", "SEASON",
            "GAME_DATE", "PLAYER_NAME", "TEAM_ID",
            "MATCHUP", "MIN", "PTS", "REB",
            "AST", "STL", "BLK", "TOV",
            "FGM", "FGA", "FG3M", "FTM", "FTA",
        ]

        rows = list(
            df[columns].itertuples(index=False, name=None)
        )

        placeholders = ",".join("?" for _ in columns)

        conn.executemany(
            f"""
            INSERT OR REPLACE INTO player_game_stats
            VALUES ({placeholders})
            """,
            rows,
        )

        print(f"[YC-LOG] Stored {len(rows)} records in database")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--season",
        default="2024-25",
        help="NBA season, e.g. 2024-25"
    )

    args = parser.parse_args()

    stats = get_season_stats(args.season)
    save_raw_data(stats, args.season)
    save_database(stats)

    print("[YC-LOG] Collection complete!")
