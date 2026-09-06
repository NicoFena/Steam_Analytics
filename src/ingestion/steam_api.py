"""Shared HTTP helper for Steam calls: client-side pacing + retries with backoff.

Both ingestion pipelines (games, reviews) go through `get()` so that a single
place controls how hard we hit the API. This matters when harvesting a large
slice of the Steam catalogue.
"""

import time

import requests

# Steam roughly tolerates ~1 request / 1.5s on the store endpoints before it
# starts answering 429 / 403. This is the minimum gap kept between two requests.
DEFAULT_REQUEST_DELAY = 1.5

# How many times a failing request is retried before we give up on it.
DEFAULT_MAX_RETRIES = 5

# Status codes worth retrying after a pause (rate limiting / transient errors).
# 403 is included because the store API also uses it as a soft throttle signal.
RETRY_STATUS = {403, 429, 500, 502, 503, 504}

_last_request_at = 0.0


class SteamAPIError(RuntimeError):
    """Raised when a Steam request keeps failing after every retry."""


def _throttle(delay):
    global _last_request_at

    wait = delay - (time.monotonic() - _last_request_at)
    if wait > 0:
        time.sleep(wait)

    _last_request_at = time.monotonic()


def _backoff(attempt, response=None):
    if response is not None:
        retry_after = response.headers.get("Retry-After", "")
        if retry_after.isdigit():
            time.sleep(int(retry_after))
            return

    # 2s, 4s, 8s, 16s, 32s ... capped at 60s.
    time.sleep(min(2 ** (attempt + 1), 60))


def get(url, params=None, *, delay=DEFAULT_REQUEST_DELAY,
        max_retries=DEFAULT_MAX_RETRIES, timeout=30):
    """GET a Steam URL, pacing requests and retrying transient failures.

    Raises SteamAPIError once all retries are exhausted so the caller can count
    the failure and move on to the next app.
    """

    for attempt in range(max_retries + 1):
        _throttle(delay)

        try:
            response = requests.get(url, params=params, timeout=timeout)
        except requests.RequestException as error:
            if attempt == max_retries:
                raise SteamAPIError(f"{url}: {error}") from error
            _backoff(attempt)
            continue

        if response.status_code == 200:
            return response

        if response.status_code in RETRY_STATUS:
            if attempt == max_retries:
                raise SteamAPIError(
                    f"{url}: HTTP {response.status_code} after {max_retries} retries"
                )
            print(
                f"HTTP {response.status_code} for {url} "
                f"(attempt {attempt + 1}/{max_retries}). Backing off..."
            )
            _backoff(attempt, response)
            continue

        # Any other 4xx: not worth retrying.
        raise SteamAPIError(f"{url}: HTTP {response.status_code}")

    raise SteamAPIError(f"{url}: exhausted retries")
