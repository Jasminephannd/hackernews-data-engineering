import html
import sys
import time
from typing import Any

import pandas as pd
import requests

from utils.constants import HN_ALGOLIA_SEARCH_URL


def _hn_text_field(hit: dict[str, Any], key: str) -> str:
    """Algolia usually returns plain strings; highlight payloads may nest {'value': ...}."""
    raw = hit.get(key)
    if raw is None:
        return ""
    if isinstance(raw, str):
        return html.unescape(raw).strip()
    if isinstance(raw, dict) and "value" in raw:
        return html.unescape(str(raw["value"])).strip()
    return html.unescape(str(raw)).strip()

# Window length for Algolia numericFilters: created_at_i > (now - N seconds).
# Tuned here; chosen in the DAG via extract_stories(..., time_filter="month").
_TIME_FILTER_SECONDS = {
    "hour": 3600,
    "day": 86400,
    "week": 7 * 86400,
    "month": 30 * 86400,
    "year": 365 * 86400,
}


def _created_after_i(time_filter: str) -> int:
    window = _TIME_FILTER_SECONDS.get(time_filter, _TIME_FILTER_SECONDS["day"])
    return int(time.time()) - window


def _normalize_hit(hit: dict[str, Any]) -> dict[str, Any]:
    oid = hit.get("objectID", "")
    url = hit.get("url") or ""
    if not url and oid:
        url = f"https://news.ycombinator.com/item?id={oid}"
    return {
        "id": str(oid),
        "title": _hn_text_field(hit, "title"),
        "story_text": _hn_text_field(hit, "story_text"),
        "score": int(hit.get("points") or 0),
        "num_comments": int(hit.get("num_comments") or 0),
        "author": (hit.get("author") or "") or "",
        "created_utc": int(hit.get("created_at_i") or 0),
        "url": url,
    }


def extract_stories(
    search_query: str,
    time_filter: str = "day",
    limit: int = 100,
    timeout: int = 30,
) -> list[dict[str, Any]]:
    """Fetch HN stories from the public Algolia HN API (no API key)."""
    created_after = _created_after_i(time_filter)
    numeric_filters = f"created_at_i>{created_after}"
    stories: list[dict[str, Any]] = []
    page = 0

    while len(stories) < limit:
        per_page = min(100, limit - len(stories))
        params = {
            "query": search_query or "",
            "tags": "story",
            "numericFilters": numeric_filters,
            "hitsPerPage": per_page,
            "page": page,
        }
        try:
            r = requests.get(
                HN_ALGOLIA_SEARCH_URL,
                params=params,
                timeout=timeout,
                headers={"User-Agent": "HnDataEngineering-Airflow/1.0"},
            )
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            print(f"Error calling HN Algolia API: {e}")
            sys.exit(1)

        hits = data.get("hits") or []
        if not hits:
            break
        for h in hits:
            stories.append(_normalize_hit(h))
            if len(stories) >= limit:
                break
        page += 1
        nb_pages = int(data.get("nbPages") or 0)
        if page >= nb_pages:
            break

    print(f"Fetched {len(stories)} HN stories (query={search_query!r}, window={time_filter})")
    return stories[:limit]


def transform_data(post_df: pd.DataFrame) -> pd.DataFrame:
    if post_df.empty:
        return post_df
    post_df = post_df.copy()
    post_df["created_utc"] = pd.to_datetime(post_df["created_utc"], unit="s", utc=True)
    post_df["author"] = post_df["author"].astype(str)
    post_df["num_comments"] = post_df["num_comments"].astype(int)
    post_df["score"] = post_df["score"].astype(int)
    post_df["title"] = post_df["title"].astype(str)
    if "story_text" in post_df.columns:
        post_df["story_text"] = post_df["story_text"].astype(str)
    return post_df


def load_data_to_csv(data: pd.DataFrame, path: str) -> None:
    data.to_csv(path, index=False)
