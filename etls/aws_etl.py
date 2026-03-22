import os

import boto3

from utils.constants import (
    AWS_ACCESS_KEY_ID,
    AWS_BUCKET_NAME,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    AWS_SESSION_TOKEN,
)


def _s3_client():
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        raise RuntimeError(
            "Missing AWS keys: set aws_access_key_id and aws_secret_access_key under [aws] in config/config.conf"
        )
    kwargs: dict = {
        "service_name": "s3",
        "region_name": AWS_REGION or None,
        "aws_access_key_id": AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": AWS_SECRET_ACCESS_KEY,
    }
    if AWS_SESSION_TOKEN:
        kwargs["aws_session_token"] = AWS_SESSION_TOKEN
    return boto3.client(**kwargs)


def upload_file_to_s3(local_path: str, bucket: str, key: str) -> None:
    if not os.path.isfile(local_path):
        raise FileNotFoundError(local_path)
    _s3_client().upload_file(local_path, bucket, key)
