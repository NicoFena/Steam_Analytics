import os
from datetime import datetime

from dotenv import load_dotenv

import steam_api
from steam_api import DEFAULT_REQUEST_DELAY, SteamAPIError

APP_ID = 620
STEAM_APP_LIST_URL = "https://api.steampowered.com/IStoreService/GetAppList/v1/"
STEAM_APP_DETAILS_URL = "https://store.steampowered.com/api/appdetails"


def get_api_key():
    """Read STEAM_API_KEY from the environment (loaded lazily, not at import)."""

    load_dotenv()
    api_key = os.getenv("STEAM_API_KEY")

    if not api_key:
        raise RuntimeError("STEAM_API_KEY is missing from .env")

    return api_key


def fetch_app_list(api_key, max_results=10, start_appid=0, delay=DEFAULT_REQUEST_DELAY):
    """Fetch a list of Steam applications, following the API pagination.

    `start_appid` lets a run resume where a previous one stopped.
    """

    apps = []
    last_appid = start_appid

    while len(apps) < max_results:
        remaining = max_results - len(apps)

        response = steam_api.get(
            STEAM_APP_LIST_URL,
            params={
                "key": api_key,
                "include_games": True,
                "max_results": min(remaining, 50000),
                "last_appid": last_appid,
            },
            delay=delay,
        )

        payload = response.json()["response"]
        page = payload.get("apps", [])

        if not page:
            break

        apps.extend(page)
        last_appid = page[-1]["appid"]

        if not payload.get("have_more_results"):
            break

    return apps[:max_results]


def fetch_game(appid, delay=DEFAULT_REQUEST_DELAY):
    """Fetch raw game data from the Steam Store API.

    Raises SteamAPIError when the store has no usable data for the app
    (delisted, region-locked, non-game bundle, ...).
    """

    response = steam_api.get(
        STEAM_APP_DETAILS_URL,
        # Pin country + language so prices and genre names stay comparable
        # across the whole dataset regardless of where the request runs from.
        params={"appids": appid, "cc": "us", "l": "en"},
        delay=delay,
    )

    entry = response.json().get(str(appid), {})

    if not entry.get("success") or "data" not in entry:
        raise SteamAPIError(f"No store data for app {appid}")

    return entry["data"]


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


def main():
    api_key = get_api_key()
    apps = fetch_app_list(api_key, max_results=30)

    print(f"Number of apps: {len(apps)}")

    for app in apps:
        print(app["appid"], app["name"])


if __name__ == "__main__":
    main()
