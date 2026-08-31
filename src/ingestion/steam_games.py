import requests
from datetime import datetime


APP_ID = 620
STEAM_APP_DETAILS_URL = "https://store.steampowered.com/api/appdetails"


def fetch_game(appid):
    """Fetch raw game data from the Steam Store API."""
    response = requests.get(
        STEAM_APP_DETAILS_URL,
        params={"appids": appid},
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    return data[str(appid)]["data"]


def transform_game(game):
    """Transform Steam API data into our games table format."""

    genres = [
        genre["description"]
        for genre in game.get("genres", [])
    ]

    categories = [
        category["description"]
        for category in game.get("categories", [])
    ]

    release_date = game.get("release_date", {}).get("date")

    if release_date:
        for date_format in ("%d %b, %Y", "%b %d, %Y"):
            try:
                release_date = datetime.strptime(
                    release_date,
                    date_format
                ).date()
                break
            except ValueError:
                continue
        else:
            release_date = None

    return {
        "appid": game["steam_appid"],
        "name": game["name"],
        "type": game.get("type"),
        "release_date": release_date,
        "is_free": game.get("is_free"),
        "required_age": game.get("required_age"),
        "developers": game.get("developers", []),
        "publishers": game.get("publishers", []),
        "genres": genres,
        "categories": categories,
    }


def main():
    raw_game = fetch_game(APP_ID)
    game_data = transform_game(raw_game)

    print(game_data)


if __name__ == "__main__":
    main()