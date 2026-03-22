import os
import sys
from datetime import datetime

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipelines.aws_s3_pipeline import upload_s3_pipeline
from pipelines.hn_pipeline import hackernews_pipeline

default_args = {
    "owner": "Jasmine Phan",
    "start_date": datetime(2026, 3, 22),
}

file_postfix = datetime.now().strftime("%Y%m%d")

dag = DAG(
    dag_id="etl_hackernews_pipeline",
    default_args=default_args,
    schedule="@daily",
    catchup=False,
    tags=["hackernews", "etl", "pipeline", "algolia"],
)

extract = PythonOperator(
    task_id="hn_extraction",
    python_callable=hackernews_pipeline,
    op_kwargs={
        "file_name": f"hn_{file_postfix}",
        "search_query": "data engineering",
        # Time window for Algolia numericFilters created_at_i (see etls/hn_etl.py _TIME_FILTER_SECONDS).
        # Options: "hour", "day" (~24h), "week", "month" (~30 days), "year".
        "time_filter": "month",
        "limit": 100,
    },
    dag=dag,
)

# Upload to AWS S3
upload_to_s3 = PythonOperator(
    task_id="s3_upload",
    python_callable=upload_s3_pipeline,
    dag=dag,
)

extract >> upload_to_s3