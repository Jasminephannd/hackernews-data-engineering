import os
import sys
from datetime import datetime

from airflow.sdk import dag, get_current_context, task

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DAGS = os.path.dirname(os.path.abspath(__file__))
for _p in (_ROOT, _DAGS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from notifications import notify_teams
from pipelines.aws_s3_pipeline import upload_s3_from_path
from pipelines.hn_pipeline import hackernews_pipeline


@dag(
    dag_id="etl_hackernews_pipeline",
    start_date=datetime(2026, 3, 29),
    schedule="@daily",
    catchup=False,
    tags=["hackernews", "etl", "pipeline", "algolia"],
    default_args={
        "owner": "Jasmine Phan",
        "on_failure_callback": notify_teams,
    },
)
def etl_hackernews_pipeline():
    """TaskFlow DAG: @task turns plain functions into operators; return values become XCom."""

    @task(task_id="hn_extraction")
    def extract() -> str:
        """Runs HN ETL; return value is pushed to XCom for the next task."""
        ctx = get_current_context()
        ds = ctx["ds_nodash"]
        return hackernews_pipeline(
            file_name=f"hn_{ds}",
            search_query="data engineering",
            time_filter="month",
            limit=100,
        )

    @task(task_id="s3_upload")
    def upload(file_path: str) -> None:
        """Receives `file_path` from upstream via TaskFlow (XCom)."""
        upload_s3_from_path(file_path)

    upload(extract())


dag = etl_hackernews_pipeline()
