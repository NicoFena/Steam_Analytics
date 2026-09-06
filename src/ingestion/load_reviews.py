import duckdb
import time
from steam_reviews import fetch_reviews, transform_review

DATABASE_PATH = "data/steam_analytics.duckdb"

MAX_REVIEWS_PER_GAME = 1000


def load_review(con, review_data):
    exists = con.execute(
        "SELECT 1 FROM reviews WHERE recommendationid = ?",
        [review_data["recommendationid"]],
    ).fetchone()

    if exists:
        return False

    con.execute(
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
    )

    return True


def main():
    con = duckdb.connect(DATABASE_PATH)

    # Reviews are fetched for the games already ingested in the database.
    games = con.execute(
        "SELECT appid, name FROM games ORDER BY appid"
    ).fetchall()

    inserted_count = 0
    skipped_count = 0
    failed_count = 0

    consecutive_403 = 0

    for appid, name in games:
        print(f"Loading reviews for {appid} - {name}...")

        try:
            reviews = fetch_reviews(appid, max_reviews=MAX_REVIEWS_PER_GAME)
            time.sleep(0.5)

            # Une requête réussie remet le compteur à zéro
            consecutive_403 = 0

            game_inserted = 0
            game_skipped = 0

            for review in reviews:
                review_data = transform_review(review, appid)

                if load_review(con, review_data):
                    game_inserted += 1
                else:
                    game_skipped += 1

            inserted_count += game_inserted
            skipped_count += game_skipped

            print(
                f"App {appid}: {game_inserted} inserted, "
                f"{game_skipped} already present."
            )

        except RuntimeError as error:
            if "403" in str(error):
                consecutive_403 += 1
                failed_count += 1

                print(
                    f"App {appid} failed: {error} "
                    f"({consecutive_403}/10 consecutive 403)"
                )

                if consecutive_403 >= 10:
                    print("10 consecutive 403 errors. Stopping ingestion.")
                    break

            else:
                print(f"App {appid} failed: {error}")
                failed_count += 1

        except Exception as error:
            print(f"App {appid} failed: {error}")
            failed_count += 1

    con.close()

    print()
    print("Loading summary:")
    print(f"Inserted: {inserted_count}")
    print(f"Skipped:  {skipped_count}")
    print(f"Failed:   {failed_count}")


if __name__ == "__main__":
    main()
