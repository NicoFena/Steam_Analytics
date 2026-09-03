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
    if game.get("type") != "game":
        raise ValueError(
            f"App {game.get('steam_appid')} is not a game"
        )

    genres = [
        genre["description"]
        for genre in game.get("genres", [])
    ]

    categories = [
        category["description"]
        for category in game.get("categories", [])
    ]

    tags = [
        tag["description"]
        for tag in game.get("tags", [])
    ]

    release_date = None
    release_date_raw = game.get("release_date", {}).get("date")

    if release_date_raw:
        try:
            release_date = datetime.strptime(
                release_date_raw,
                "%d %b, %Y"
            ).date()
        except ValueError:
            release_date = None

    price = game.get("price_overview", {})

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
        "tags": tags,

        "price_initial": price.get("initial"),
        "price_final": price.get("final"),
        "price_discount_percent": price.get("discount_percent"),
        "currency": price.get("currency"),

        "metacritic_score": game.get("metacritic", {}).get("score"),
        "metacritic_url": game.get("metacritic", {}).get("url"),

        "recommendations_total": game.get("recommendations", {}).get("total"),

        "header_image_url": game.get("header_image"),
        "website_url": game.get("website"),

        "data_fetched_at": datetime.now(),
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