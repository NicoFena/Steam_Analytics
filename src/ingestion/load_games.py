import duckdb

from steam_games import fetch_app_list, fetch_game, transform_game

DATABASE_PATH = "data/steam_analytics.duckdb"


def load_game(game_data):
    """Insert one game into DuckDB if it does not already exist."""

    con = duckdb.connect(DATABASE_PATH)

    exists = con.execute(
        """
        SELECT 1
        FROM games
        WHERE appid = ?
        """,
        [game_data["appid"]],
    ).fetchone()

    if exists:
        con.close()
        return False

    con.execute(
        """
        INSERT INTO games (
            appid,
            name,
            type,
            release_date,
            is_free,
            required_age,
            developers,
            publishers,
            genres,
            categories
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            game_data["appid"],
            game_data["name"],
            game_data["type"],
            game_data["release_date"],
            game_data["is_free"],
            game_data["required_age"],
            game_data["developers"],
            game_data["publishers"],
            game_data["genres"],
            game_data["categories"],
        ],
    )

    con.close()
    return True

def main():
    apps = fetch_app_list(max_results=10)

    for app in apps:
        appid = app["appid"]

        print(f"Loading {appid} - {app['name']}...")

        raw_game = fetch_game(appid)
        game_data = transform_game(raw_game)

        inserted = load_game(game_data)

        if inserted:
            print(f"Game {appid} inserted.")
        else:
            print(f"Game {appid} already exists. Skipped.")


if __name__ == "__main__":
    main()