from pathlib import Path
import argparse
import logging
import sqlite3
import time

from nba_api.stats.endpoints import playergamelogs
from pandas import DataFrame

LOGGER = logging.getLogger(__name__)

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
    LOGGER.info("Requesting NBA season stats for %s (timeout: 60 seconds)", season)

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
    LOGGER.info("Received %s player-game records for %s", f"{len(df):,}", season)

    return df

def save_raw_data(df: DataFrame, season: str):
    """
    Save a specific seasons stats into the Raw Data directory
    """
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    path = RAW_DATA_DIR / f"player_games_{season}.csv"
    df.to_csv(path, index=False)

    LOGGER.info("Saved %s raw rows to %s", f"{len(df):,}", path)

def save_database(df: DataFrame):
    """
    Save a specific dataframe into the database
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Writing player-game records to %s", DB_PATH)
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

    LOGGER.info("Stored %s records in database", f"{len(rows):,}")

def import_seasons(start_year: int, end_year: int):
    for year in range(start_year, end_year +1):
        season_str = f"{year}-{str(year+1)[-2:]}" # convert to this format: 2024-25

        LOGGER.info("Importing season %s (%s/%s)", season_str, year - start_year + 1, end_year - start_year + 1)

        # Attempt each season up to three times
        for attempt in range(1, 4):
            try:
                df = get_season_stats(season_str)

                # Data integrity checks
                if df[["PLAYER_ID", "GAME_ID"]].isna().any().any():
                    raise ValueError("Missing player/game IDs")

                if df.duplicated(
                    subset=["PLAYER_ID", "GAME_ID"]
                ).any():
                    raise ValueError("Duplicate player-game records")

                save_raw_data(df, season_str)
                save_database(df)

                LOGGER.info("Successfully imported %s", season_str)
                break

            except Exception as exc:
                LOGGER.warning("Season %s attempt %s/3 failed: %s", season_str, attempt, exc)

                if attempt == 3:
                    raise RuntimeError(
                        f"Unable to import {season_str}"
                    ) from exc

                # Exponential backoff between retries
                LOGGER.info("Retrying %s in %s seconds", season_str, 2 ** attempt)
                time.sleep(2 ** attempt)

        # Avoid rapidly sending requests to NBA.com
        if year < end_year:
            LOGGER.info("Waiting 3 seconds before the next season request")
            time.sleep(3)

    LOGGER.info("All seasons imported successfully")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--start",
        type=int,
        default=2020
    )
    parser.add_argument(
        "--end",
        type=int,
        default=2025
    )

    args = parser.parse_args()

    if args.start > args.end:
        parser.error("--start cannot exceed --end")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    import_seasons(args.start, args.end)
