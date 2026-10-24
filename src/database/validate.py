
import sqlite3
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "nba.db"

LOGGER = logging.getLogger(__name__)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

LOGGER.info("Starting database validation: %s", DB_PATH)
with sqlite3.connect(DB_PATH) as conn:
    # How many records do we have per season?
    LOGGER.info("Counting records and players per season")

    query = """
        SELECT season,
               COUNT(*) AS games,
               COUNT(DISTINCT player_id) AS players
        FROM player_game_stats
        GROUP BY season
        ORDER BY season
    """

    for season, games, players in conn.execute(query):
        LOGGER.info("%s: %s records, %s players", season, f"{games:,}", players)

    # Check for duplicate player-game records
    duplicate_query = """
        SELECT COUNT(*)
        FROM (
            SELECT player_id, game_id
            FROM player_game_stats
            GROUP BY player_id, game_id
            HAVING COUNT(*) > 1
        )
    """

    LOGGER.info("Checking for duplicate player-game records")
    duplicates = conn.execute(duplicate_query).fetchone()[0]
    LOGGER.info("Duplicate records: %s", duplicates)

    # Check for impossible shooting statistics
    invalid_query = """
        SELECT COUNT(*)
        FROM player_game_stats
        WHERE fgm > fga
           OR ftm > fta
           OR pts < 0
           OR reb < 0
           OR ast < 0
    """

    LOGGER.info("Checking for impossible shooting and negative statistics")
    invalid = conn.execute(invalid_query).fetchone()[0]
    LOGGER.info("Invalid stat records: %s", invalid)

    assert duplicates == 0
    assert invalid == 0

    LOGGER.info("Basic database validation passed")
