import os
from datetime import datetime
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("STEAM_API_KEY")

if not API_KEY:
    raise RuntimeError("STEAM_API_KEY is missing from .env")

APP_ID = 620
STEAM_APP_DETAILS_URL = "https://store.steampowered.com/api/appdetails"


def fetch_app_list(max_results=10):
    """Fetch a list of Steam applications."""

    url = "https://api.steampowered.com/IStoreService/GetAppList/v1/"

    apps = []
    last_appid = 0

    while len(apps) < max_results:
        remaining = max_results - len(apps)

        params = {
            "key": API_KEY,
            "include_games": True,
            "max_results": min(remaining, 50000),
            "last_appid": last_appid,
        }

        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        page = data["response"]["apps"]

        if not page:
            break

        apps.extend(page)

        last_appid = page[-1]["appid"]

        if len(page) < params["max_results"]:
            break

    return apps[:max_results]

def fetch_game(appid, max_retries=1):
    """Fetch raw game data from the Steam Store API."""

    for attempt in range(max_retries + 1):
        response = requests.get(
            STEAM_APP_DETAILS_URL,
            params={"appids": appid},
            timeout=30,
        )

        if response.status_code == 403:
            if attempt < max_retries:
                print(f"403 for app {appid}. Retrying in 2s...")
                time.sleep(2)
                continue

            raise RuntimeError(
                f"Steam returned 403 for app {appid}"
            )

        response.raise_for_status()

        data = response.json()

        return data[str(appid)]["data"]

    raise RuntimeError(f"Steam returned 403 for app {appid}")


def transform_game(game):
    """Transform Steam API data into our games table format."""

    if game.get("type") != "game":
        raise ValueError(f"App {game.get('steam_appid')} is not a game")

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


# def main():
#     apps = fetch_app_list(max_results=10)

#     for app in apps:
#         appid = app["appid"]

#         print(f"Fetching {appid} - {app['name']}...")

#         raw_game = fetch_game(appid)
#         game_data = transform_game(raw_game)

#         print(game_data)
#         print()

def main():
    apps = fetch_app_list(max_results=30)

    print(f"Number of apps: {len(apps)}")

    for app in apps:
        print(app["appid"], app["name"])
        
if __name__ == "__main__":
    main()