import argparse

import duckdb

from steam_api import DEFAULT_REQUEST_DELAY, SteamAPIError
from steam_games import fetch_app_list, fetch_game, get_api_key, transform_game

DEFAULT_DATABASE_PATH = "data/steam_analytics.duckdb"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Ingest Steam games into the DuckDB database."
    )
    parser.add_argument(
        "--max-games", type=int, default=300,
        help="How many games to pull from the app list (default: 300).",
    )
    parser.add_argument(
        "--start-appid", type=int, default=0,
        help="Resume paging the app list after this appid (default: 0).",
    )
    parser.add_argument(
        "--db", default=DEFAULT_DATABASE_PATH,
        help="Path to the DuckDB database file.",
    )
    parser.add_argument(
        "--request-delay", type=float, default=DEFAULT_REQUEST_DELAY,
        help="Minimum seconds between two Steam API requests.",
    )
    parser.add_argument(
        "--max-consecutive-failures", type=int, default=10,
        help="Stop ingestion after this many failures in a row.",
    )
    return parser.parse_args()


def load_game(con, game_data):
    """Insert a game, skipping it if the appid is already present."""

    result = con.execute(
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
            categories,
            tags,
            price_initial,
            price_final,
            price_discount_percent,
            currency,
            metacritic_score,
            metacritic_url,
            recommendations_total,
            header_image_url,
            website_url,
            data_fetched_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (appid) DO NOTHING
        RETURNING appid
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
            game_data["tags"],
            game_data["price_initial"],
            game_data["price_final"],
            game_data["price_discount_percent"],
            game_data["currency"],
            game_data["metacritic_score"],
            game_data["metacritic_url"],
            game_data["recommendations_total"],
            game_data["header_image_url"],
            game_data["website_url"],
            game_data["data_fetched_at"],
        ],
    ).fetchone()

    return result is not None


def main():
    args = parse_args()
    api_key = get_api_key()

    con = duckdb.connect(args.db)

    # Load the appids we already have once, so we never spend an API call on a
    # game that is already in the database (cheap resume for large harvests).
    existing_appids = {
        row[0] for row in con.execute("SELECT appid FROM games").fetchall()
    }

    apps = fetch_app_list(
        api_key,
        max_results=args.max_games,
        start_appid=args.start_appid,
        delay=args.request_delay,
    )

    inserted_count = 0
    skipped_count = 0
    failed_count = 0
    consecutive_failures = 0

    for app in apps:
        appid = app["appid"]
        name = app["name"]

        if appid in existing_appids:
            skipped_count += 1
            continue

        print(f"Loading {appid} - {name}...")

        try:
            raw_game = fetch_game(appid, delay=args.request_delay)
        except SteamAPIError as error:
            failed_count += 1
            consecutive_failures += 1
            print(
                f"Game {appid} failed: {error} "
                f"({consecutive_failures}/{args.max_consecutive_failures} in a row)"
            )
            if consecutive_failures >= args.max_consecutive_failures:
                print("Too many consecutive failures. Stopping ingestion.")
                break
            continue

        # The request went through: the API is responding, reset the breaker.
        consecutive_failures = 0

        try:
            game_data = transform_game(raw_game)
        except ValueError as error:
            skipped_count += 1
            print(f"Game {appid} skipped: {error}")
            continue

        if load_game(con, game_data):
            existing_appids.add(appid)
            inserted_count += 1
            print(f"Game {appid} inserted.")
        else:
            skipped_count += 1
            print(f"Game {appid} already exists. Skipped.")

    con.close()

    print()
    print("Loading summary:")
    print(f"Inserted: {inserted_count}")
    print(f"Skipped:  {skipped_count}")
    print(f"Failed:   {failed_count}")


if __name__ == "__main__":
    main()
