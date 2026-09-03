import duckdb

DATABASE_PATH = "data/steam_analytics.duckdb"


def main():
    con = duckdb.connect(DATABASE_PATH)

    result = con.execute("""
        SELECT
            COUNT(*) AS total_games,
            MIN(release_date) AS earliest_release,
            MAX(release_date) AS latest_release,

            COUNT(*) FILTER (
                WHERE is_free = TRUE
            ) AS free_games,

            COUNT(*) FILTER (
                WHERE is_free = FALSE
            ) AS paid_games,

            COUNT(*) FILTER (
                WHERE metacritic_score IS NOT NULL
            ) AS games_with_metacritic,

            COUNT(*) FILTER (
                WHERE recommendations_total IS NOT NULL
            ) AS games_with_recommendations

        FROM games;
    """).fetchone()

    print("Data quality summary")
    print("--------------------")
    print(f"Total games:              {result[0]}")
    print(f"Earliest release:         {result[1]}")
    print(f"Latest release:           {result[2]}")
    print(f"Free games:               {result[3]}")
    print(f"Paid games:               {result[4]}")
    print(f"With Metacritic score:    {result[5]}")
    print(f"With recommendations:     {result[6]}")

    print()
    print("Missing values")
    print("--------------")

    missing = con.execute("""
        SELECT
            COUNT(*) AS total_games,

            COUNT(*) - COUNT(name) AS missing_name,
            COUNT(*) - COUNT(release_date) AS missing_release_date,
            COUNT(*) - COUNT(is_free) AS missing_is_free,
            COUNT(*) - COUNT(required_age) AS missing_required_age,
            COUNT(*) - COUNT(developers) AS missing_developers,
            COUNT(*) - COUNT(publishers) AS missing_publishers,
            COUNT(*) - COUNT(genres) AS missing_genres,
            COUNT(*) - COUNT(categories) AS missing_categories,
            COUNT(*) - COUNT(tags) AS missing_tags,
            COUNT(*) - COUNT(price_final) AS missing_price,
            COUNT(*) - COUNT(metacritic_score) AS missing_metacritic,
            COUNT(*) - COUNT(recommendations_total) AS missing_recommendations

        FROM games;
    """).fetchone()

    columns = [
        "total_games",
        "missing_name",
        "missing_release_date",
        "missing_is_free",
        "missing_required_age",
        "missing_developers",
        "missing_publishers",
        "missing_genres",
        "missing_categories",
        "missing_tags",
        "missing_price",
        "missing_metacritic",
        "missing_recommendations",
    ]

    for column, value in zip(columns, missing):
        print(f"{column}: {value}")

    print()
    print("Consistency checks")
    print("------------------")

    checks = con.execute("""
        SELECT
            COUNT(*) FILTER (
                WHERE price_initial < 0
            ) AS negative_initial_prices,

            COUNT(*) FILTER (
                WHERE price_final < 0
            ) AS negative_final_prices,

            COUNT(*) FILTER (
                WHERE price_final > price_initial
            ) AS final_price_above_initial,

            COUNT(*) FILTER (
                WHERE metacritic_score < 0
                   OR metacritic_score > 100
            ) AS invalid_metacritic,

            COUNT(*) FILTER (
                WHERE recommendations_total < 0
            ) AS negative_recommendations,

            COUNT(*) FILTER (
                WHERE release_date > CURRENT_DATE
            ) AS future_release_dates,

            COUNT(*) FILTER (
                WHERE array_length(genres) = 0
            ) AS games_without_genres

        FROM games;
    """).fetchone()

    print(f"Negative initial prices:    {checks[0]}")
    print(f"Negative final prices:      {checks[1]}")
    print(f"Final > initial price:      {checks[2]}")
    print(f"Invalid Metacritic scores:  {checks[3]}")
    print(f"Negative recommendations:   {checks[4]}")
    print(f"Future release dates:       {checks[5]}")
    print(f"Games without genres:       {checks[6]}")

    con.close()


if __name__ == "__main__":
    main()