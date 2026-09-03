import duckdb
import time
from steam_games import fetch_app_list, fetch_game, transform_game

DATABASE_PATH = "data/steam_analytics.duckdb"


def load_game(con, game_data):
    exists = con.execute(
        "SELECT 1 FROM games WHERE appid = ?",
        [game_data["appid"]],
    ).fetchone()

    if exists:
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
    )

    return True

def main():
    apps = fetch_app_list(max_results=300)

    con = duckdb.connect(DATABASE_PATH)

    inserted_count = 0
    skipped_count = 0
    failed_count = 0

    consecutive_403 = 0

    for app in apps:
        appid = app["appid"]
        name = app["name"]

        print(f"Loading {appid} - {name}...")

        try:
            raw_game = fetch_game(appid)
            time.sleep(0.5)
            game_data = transform_game(raw_game)
            inserted = load_game(con, game_data)

            # Une requête réussie remet le compteur à zéro
            consecutive_403 = 0

            if inserted:
                print(f"Game {appid} inserted.")
                inserted_count += 1
            else:
                print(f"Game {appid} already exists. Skipped.")
                skipped_count += 1

        except RuntimeError as error:
            if "403" in str(error):
                consecutive_403 += 1
                failed_count += 1

                print(
                    f"Game {appid} failed: {error} "
                    f"({consecutive_403}/10 consecutive 403)"
                )

                if consecutive_403 >= 10:
                    print("10 consecutive 403 errors. Stopping ingestion.")
                    break

            else:
                print(f"Game {appid} failed: {error}")
                failed_count += 1

        except Exception as error:
            print(f"Game {appid} failed: {error}")
            failed_count += 1

    con.close()

    print()
    print("Loading summary:")
    print(f"Inserted: {inserted_count}")
    print(f"Skipped:  {skipped_count}")
    print(f"Failed:   {failed_count}")


if __name__ == "__main__":
    main()