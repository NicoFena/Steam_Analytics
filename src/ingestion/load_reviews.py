import argparse

import duckdb

from steam_api import DEFAULT_REQUEST_DELAY, SteamAPIError
from steam_reviews import DEFAULT_LANGUAGE, fetch_reviews, transform_review

DEFAULT_DATABASE_PATH = "data/steam_analytics.duckdb"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Ingest Steam reviews into the DuckDB database."
    )
    parser.add_argument(
        "--max-games", type=int, default=None,
        help="Limit how many games to fetch reviews for (default: all games).",
    )
    parser.add_argument(
        "--max-reviews", type=int, default=1000,
        help="Max reviews to fetch per game (default: 1000).",
    )
    parser.add_argument(
        "--language", default=DEFAULT_LANGUAGE,
        help='Review language filter (default: "all").',
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
    parser.add_argument(
        "--refresh", action="store_true",
        help="Also fetch games that already have reviews in the database.",
    )
    return parser.parse_args()


def load_review(con, review_data):
    """Insert a review, skipping it if the recommendationid is already present."""

    result = con.execute(
        """
        INSERT INTO reviews (
            recommendationid,
            appid,
            language,
            review_text,
            voted_up,
            author_steamid,
            author_num_games_owned,
            author_num_reviews,
            author_playtime_forever,
            author_playtime_last_two_weeks,
            author_playtime_at_review,
            author_last_played,
            timestamp_created,
            timestamp_updated,
            votes_up,
            votes_funny,
            weighted_vote_score,
            comment_count,
            steam_purchase,
            received_for_free,
            written_during_early_access,
            data_fetched_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (recommendationid) DO NOTHING
        RETURNING recommendationid
        """,
        [
            review_data["recommendationid"],
            review_data["appid"],
            review_data["language"],
            review_data["review_text"],
            review_data["voted_up"],
            review_data["author_steamid"],
            review_data["author_num_games_owned"],
            review_data["author_num_reviews"],
            review_data["author_playtime_forever"],
            review_data["author_playtime_last_two_weeks"],
            review_data["author_playtime_at_review"],
            review_data["author_last_played"],
            review_data["timestamp_created"],
            review_data["timestamp_updated"],
            review_data["votes_up"],
            review_data["votes_funny"],
            review_data["weighted_vote_score"],
            review_data["comment_count"],
            review_data["steam_purchase"],
            review_data["received_for_free"],
            review_data["written_during_early_access"],
            review_data["data_fetched_at"],
        ],
    ).fetchone()

    return result is not None


def main():
    args = parse_args()

    con = duckdb.connect(args.db)

    games = con.execute(
        "SELECT appid, name FROM games ORDER BY appid"
    ).fetchall()

    # Skip games that already have reviews, unless --refresh is passed.
    done_appids = set()
    if not args.refresh:
        done_appids = {
            row[0]
            for row in con.execute(
                "SELECT DISTINCT appid FROM reviews"
            ).fetchall()
        }

    if args.max_games is not None:
        games = games[: args.max_games]

    inserted_count = 0
    skipped_reviews = 0
    skipped_games = 0
    failed_count = 0
    consecutive_failures = 0

    for appid, name in games:
        if appid in done_appids:
            skipped_games += 1
            continue

        print(f"Loading reviews for {appid} - {name}...")

        try:
            reviews = fetch_reviews(
                appid,
                max_reviews=args.max_reviews,
                language=args.language,
                delay=args.request_delay,
            )
        except SteamAPIError as error:
            failed_count += 1
            consecutive_failures += 1
            print(
                f"App {appid} failed: {error} "
                f"({consecutive_failures}/{args.max_consecutive_failures} in a row)"
            )
            if consecutive_failures >= args.max_consecutive_failures:
                print("Too many consecutive failures. Stopping ingestion.")
                break
            continue

        # The request went through: the API is responding, reset the breaker.
        consecutive_failures = 0

        game_inserted = 0
        game_skipped = 0

        for review in reviews:
            review_data = transform_review(review, appid)

            if load_review(con, review_data):
                game_inserted += 1
            else:
                game_skipped += 1

        inserted_count += game_inserted
        skipped_reviews += game_skipped

        print(
            f"App {appid}: {game_inserted} inserted, "
            f"{game_skipped} already present."
        )

    con.close()

    print()
    print("Loading summary:")
    print(f"Reviews inserted: {inserted_count}")
    print(f"Reviews skipped:  {skipped_reviews}")
    print(f"Games skipped:    {skipped_games}")
    print(f"Failed:           {failed_count}")


if __name__ == "__main__":
    main()
