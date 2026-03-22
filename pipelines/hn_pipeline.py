import pandas as pd

from etls.hn_etl import extract_stories, load_data_to_csv, transform_data
from utils.constants import OUTPUT_PATH


def hackernews_pipeline(
    file_name: str,
    search_query: str,
    time_filter: str = "day",
    limit: int | None = 100,
) -> str:
    rows = extract_stories(
        search_query=search_query,
        time_filter=time_filter,
        limit=limit or 100,
    )
    post_df = pd.DataFrame(rows)
    post_df = transform_data(post_df)
    file_path = f"{OUTPUT_PATH}/{file_name}.csv"
    load_data_to_csv(post_df, file_path)
    return file_path
