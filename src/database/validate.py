
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "nba.db"

with sqlite3.connect(DB_PATH) as conn:
    # How many records do we have per season?
    print("Records per season:")

    query = """
        SELECT season,
               COUNT(*) AS games,
               COUNT(DISTINCT player_id) AS players
        FROM player_game_stats
        GROUP BY season
        ORDER BY season
    """

    for season, games, players in conn.execute(query):
        print(f"{season}: {games} records, {players} players")

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

    duplicates = conn.execute(duplicate_query).fetchone()[0]
    print(f"\nDuplicate records: {duplicates}")

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

    invalid = conn.execute(invalid_query).fetchone()[0]
    print(f"Invalid stat records: {invalid}")

    assert duplicates == 0
    assert invalid == 0

    print("\nBasic validation passed!")
