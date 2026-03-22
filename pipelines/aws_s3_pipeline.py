from etls.aws_etl import upload_file_to_s3
from utils.constants import AWS_BUCKET_NAME


def upload_s3_pipeline(ti):
    if not AWS_BUCKET_NAME:
        raise RuntimeError("Set aws_bucket_name under [aws] in config/config.conf")

    file_path = ti.xcom_pull(task_ids="hn_extraction", key="return_value")
    if not file_path:
        raise ValueError("hn_extraction did not return a file path.")

    key = f"raw/{file_path.rsplit('/', 1)[-1]}"
    upload_file_to_s3(file_path, AWS_BUCKET_NAME, key)
