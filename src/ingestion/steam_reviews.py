from datetime import datetime

import steam_api
from steam_api import DEFAULT_REQUEST_DELAY

# The Steam Store review endpoint is public and does not require an API key
# (unlike IStoreService/GetAppList used in steam_games.py).
APP_ID = 620
STEAM_APP_REVIEWS_URL = "https://store.steampowered.com/appreviews"

DEFAULT_LANGUAGE = "all"
NUM_PER_PAGE = 100


def fetch_reviews_page(appid, cursor="*", language=DEFAULT_LANGUAGE,
                       delay=DEFAULT_REQUEST_DELAY):
    """Fetch a single page of reviews from the Steam Store API."""

    response = steam_api.get(
        f"{STEAM_APP_REVIEWS_URL}/{appid}",
        params={
            "json": 1,
            "filter": "recent",
            "language": language,
            "review_type": "all",
            "purchase_type": "all",
            "num_per_page": NUM_PER_PAGE,
            "cursor": cursor,
        },
        delay=delay,
    )

    data = response.json()

    if data.get("success") != 1:
        raise steam_api.SteamAPIError(
            f"Steam review query failed for app {appid}"
        )

    return data


def fetch_reviews(appid, max_reviews=1000, language=DEFAULT_LANGUAGE,
                  delay=DEFAULT_REQUEST_DELAY):
    """Fetch reviews for a game, following the API cursor pagination."""

    reviews = []
    cursor = "*"
    seen_cursors = set()

    while len(reviews) < max_reviews:
        data = fetch_reviews_page(
            appid, cursor=cursor, language=language, delay=delay
        )

        page = data.get("reviews", [])

        if not page:
            break

        reviews.extend(page)

        cursor = data.get("cursor")

        # A missing or repeated cursor means there is no more data to page through.
        if not cursor or cursor in seen_cursors:
            break

        seen_cursors.add(cursor)

    return reviews[:max_reviews]


def _to_datetime(epoch):
    """Convert a Unix timestamp (seconds) to a naive datetime, or None."""

    if not epoch:
        return None

    return datetime.fromtimestamp(epoch)


def transform_review(review, appid):
    author = review.get("author", {})

    weighted_vote_score = review.get("weighted_vote_score")

    try:
        weighted_vote_score = float(weighted_vote_score)
    except (TypeError, ValueError):
        weighted_vote_score = None

    return {
        "recommendationid": int(review["recommendationid"]),
        "appid": appid,

        "language": review.get("language"),
        "review_text": review.get("review"),

        "voted_up": review.get("voted_up"),

        "author_steamid": author.get("steamid"),
        "author_num_games_owned": author.get("num_games_owned"),
        "author_num_reviews": author.get("num_reviews"),
        "author_playtime_forever": author.get("playtime_forever"),
        "author_playtime_last_two_weeks": author.get("playtime_last_two_weeks"),
        "author_playtime_at_review": author.get("playtime_at_review"),
        "author_last_played": _to_datetime(author.get("last_played")),

        "timestamp_created": _to_datetime(review.get("timestamp_created")),
        "timestamp_updated": _to_datetime(review.get("timestamp_updated")),

        "votes_up": review.get("votes_up"),
        "votes_funny": review.get("votes_funny"),
        "weighted_vote_score": weighted_vote_score,
        "comment_count": review.get("comment_count"),

        "steam_purchase": review.get("steam_purchase"),
        "received_for_free": review.get("received_for_free"),
        "written_during_early_access": review.get("written_during_early_access"),

        "data_fetched_at": datetime.now(),
    }


def main():
    reviews = fetch_reviews(APP_ID, max_reviews=20)

    print(f"Number of reviews: {len(reviews)}")

    for review in reviews:
        data = transform_review(review, APP_ID)
        print(
            data["recommendationid"],
            data["voted_up"],
            data["author_playtime_at_review"],
        )


if __name__ == "__main__":
    main()
