import configparser
import os

parser = configparser.ConfigParser()
parser.read(os.path.join(os.path.dirname(__file__), "../config/config.conf"))

HN_ALGOLIA_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
if parser.has_section("hackernews"):
    HN_ALGOLIA_SEARCH_URL = parser.get(
        "hackernews", "algolia_search_url", fallback=HN_ALGOLIA_SEARCH_URL
    )

DATABASE_HOST = parser.get("database", "database_host")
DATABASE_PORT = parser.get("database", "database_port")
DATABASE_NAME = parser.get("database", "database_name")
DATABASE_USERNAME = parser.get("database", "database_username")
DATABASE_PASSWORD = parser.get("database", "database_password")

def _strip(val: str | None) -> str:
    return (val or "").strip()


# AWS — config/config.conf only ([aws] section; file is gitignored).
AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""
AWS_SESSION_TOKEN = ""
AWS_REGION = ""
AWS_BUCKET_NAME = ""
if parser.has_section("aws"):
    AWS_ACCESS_KEY_ID = _strip(parser.get("aws", "aws_access_key_id", fallback=""))
    AWS_SECRET_ACCESS_KEY = _strip(parser.get("aws", "aws_secret_access_key", fallback=""))
    AWS_SESSION_TOKEN = _strip(parser.get("aws", "aws_session_token", fallback=""))
    AWS_REGION = _strip(parser.get("aws", "aws_region", fallback=""))
    AWS_BUCKET_NAME = _strip(parser.get("aws", "aws_bucket_name", fallback=""))

INPUT_PATH = parser.get("file_paths", "input_path")
OUTPUT_PATH = parser.get("file_paths", "output_path")

HN_STORY_COLUMNS = (
    "id",
    "title",
    "story_text",
    "score",
    "num_comments",
    "author",
    "created_utc",
    "url",
)