import duckdb


DATABASE_PATH = "data/steam_analytics.duckdb"


def main():
    con = duckdb.connect(DATABASE_PATH)

    result = con.execute("""
        SELECT
            genre,
            COUNT(*) AS game_count
        FROM games,
             UNNEST(genres) AS t(genre)
        GROUP BY genre
        ORDER BY game_count DESC;
    """).fetchall()

    print("Games by genre")
    print("--------------")

    for genre, count in result:
        print(f"{genre:<25} {count}")

    con.close()


if __name__ == "__main__":
    main()