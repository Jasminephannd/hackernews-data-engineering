from etls.aws_etl import upload_file_to_s3
from utils.constants import AWS_BUCKET_NAME


def upload_s3_from_path(file_path: str) -> None:
    """Upload a local file to S3. Used by TaskFlow @task (path comes from upstream XCom)."""
    if not AWS_BUCKET_NAME:
        raise RuntimeError("Set aws_bucket_name under [aws] in config/config.conf")
    if not file_path:
        raise ValueError("file_path is empty.")
    key = f"raw/{file_path.rsplit('/', 1)[-1]}"
    upload_file_to_s3(file_path, AWS_BUCKET_NAME, key)
