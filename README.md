# Data pipeline: Hacker News, Airflow, Celery, PostgreSQL, and Amazon S3

This project implements an **extract → transform → load** path for **Hacker News** story data, orchestrated with **Apache Airflow 3** and **Celery**, with **PostgreSQL** and **Redis** for Airflow’s metadata and broker, and **Amazon S3** for raw CSV storage.

The original design was inspired by a **Reddit**-based pipeline (Reddit API client credentials are difficult to obtain for casual automation), so the **source was switched to Hacker News** via the **public Algolia HN Search API**, which does not require an API key for read-only search.

A natural **extension** of the same architecture—aligned with common data-engineering coursework—is to add **AWS Glue**, **Amazon Athena** *after* S3 for cataloging and SQL transforms. AWS analytics layers are **not implemented in this repository yet**; they are documented below as a **target architecture** you can build on top of the S3 landing zone this project already produces.

## Table of contents

- [Overview](#overview)
- [What this repo implements](#what-this-repo-implements)
- [Architecture diagram](#architecture-diagram)
- [Target architecture](#target-architecture)
- [Project layout](#project-layout)
- [Configuration](#configuration)
- [Running with Docker Compose](#running-with-docker-compose)
- [DAG behavior](#dag-behavior)
- [Security notes](#security-notes)

## Overview

The pipeline is intended to:

1. **Extract** recent Hacker News **stories** using the [Algolia HN API](https://hn.algolia.com/api) (`/api/v1/search`), filtered by a **time window** and optional **search query**.
2. **Transform** records into a **pandas** `DataFrame` (typed columns, UTC timestamps, HTML entities decoded in text fields).
3. **Load** a **CSV** file under `data/output/` inside the Airflow container (bind-mounted from the host).
4. **Upload** that CSV to **Amazon S3** (`raw/<filename>.csv`) using **boto3** and credentials from a **gitignored** `config/config.conf`.

**Apache Airflow** (with **CeleryExecutor**) schedules the work; **PostgreSQL** holds Airflow’s metadata and Celery result backend; **Redis** is the Celery broker.

## What this repo implements

| Layer | Technology | Role |
|--------|------------|------|
| Source | Hacker News (Algolia) | HTTP JSON search; no API key for the endpoints used here |
| Orchestration | Airflow 3.1.x, Celery | DAG `etl_hackernews_pipeline`: extract → upload to S3 |
| Metadata / results DB | PostgreSQL 12 | `airflow_hn` database for Airflow + Celery |
| Broker | Redis | Celery message broker |
| Local staging | CSV on disk | `./data/output/` (mounted at `/opt/airflow/data/output`) |
| Object storage | Amazon S3 | Raw CSV under `s3://<bucket>/raw/` |
| Runtime | Docker Compose | Custom image from `Dockerfile` (extends `apache/airflow:3.1.8-python3.12`) |

## Target architecture 

The following matches the **idea set** you started from (Reddit → replaced by HN here). These pieces are **roadmap**, not current code in this repo:

| Component | Intended role |
|-----------|----------------|
| **Amazon S3** | Raw zone for CSVs. |
| **AWS Glue** | Crawl S3, maintain a **Data Catalog**, Spark/Python **ETL jobs** to curated prefixes. |
| **Amazon Athena** | Run **SQL** over cataloged data in S3 (often Parquet/ORC after Glue jobs). |
| **Amazon Redshift** | **Copy** or **Spectrum**-style analytics warehouse for BI and heavy SQL. |

In this project: **S3 raw** → **Glue** (convert CSV to Parquet, transform created_utc → keep only date, drop story_text column) → **Athena** 

## Project layout

| Path | Purpose |
|------|---------|
| `dags/hn_dag.py` | DAG: HN extraction task → S3 upload task |
| `pipelines/hn_pipeline.py` | Orchestrates extract → transform → CSV path |
| `pipelines/aws_s3_pipeline.py` | Reads XCom path from extraction, uploads to S3 |
| `etls/hn_etl.py` | HTTP extract, normalize hits, transform, write CSV |
| `etls/aws_etl.py` | boto3 S3 client + `upload_file` |
| `utils/constants.py` | Loads `config/config.conf` paths and AWS settings |
| `config/config.conf` | **Gitignored** — database, paths, AWS keys, HN URL |
| `docker-compose.yml` | Postgres, Redis, Airflow init, API server, scheduler, worker, dag-processor |
| `airflow.env` | Non-secret Airflow configuration (`AIRFLOW__*` variables) |
| `Dockerfile` | Installs `requirements.txt` on the official Airflow image |

**CSV columns** (normalized story shape): `id`, `title`, `story_text`, `score`, `num_comments`, `author`, `created_utc`, `url`.

## Configuration

1. Copy or create **`config/config.conf`** (see `.gitignore`; do not commit secrets).
2. Fill **`[aws]`**: `aws_access_key_id`, `aws_secret_access_key`, optional `aws_session_token`, `aws_region`, `aws_bucket_name`.
3. Adjust **`[file_paths]`** if you change mount points; in Docker, `output_path` should remain **`/opt/airflow/data/output`** unless you change the compose volumes.
4. **`airflow.env`** holds Airflow core settings (executor, DB URL, broker, JWT secret, etc.) — keep secrets out of git if you extend it.

## Running with Docker Compose

High-level sequence:

1. Build the image (init service owns the `build:` stanza):  
   `docker compose build airflow-init`
2. Start Postgres and Redis, run **init** once (migrations + admin user):  
   `docker compose up -d postgres redis`  
   then  
   `docker compose run --rm airflow-init`  
   (or rely on compose dependencies if you use `docker compose up` as documented in the [Airflow Docker Compose guide](https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html).)
3. Start the rest: API server, scheduler, worker, dag-processor.  
   UI: **http://localhost:8080** (Airflow 3 uses **`airflow api-server`** behind the scenes).

Ensure **`./data`** and **`./logs`** are writable by UID **50000** (the image’s `airflow` user); the **init** container runs as root briefly to `chown` those paths (see `docker-compose.yml`).

## DAG behavior

- **DAG id:** `etl_hackernews_pipeline`
- **Task `hn_extraction`:** calls `hackernews_pipeline` with `search_query`, `time_filter` (e.g. `month` ≈ last 30 days), and `limit` (default 100). Writes `hn_YYYYMMDD.csv` and returns the full path via XCom.
- **Task `s3_upload`:** uploads that file to **`s3://<bucket>/raw/<same filename>`**.

Tune extraction in **`dags/hn_dag.py`** (`op_kwargs`) and time-window keys in **`etls/hn_etl.py`** (`_TIME_FILTER_SECONDS`).

## Security notes

- **Never commit** `config/config.conf` if it contains AWS keys; keep it **gitignored**.
- **Rotate** any access keys that were ever committed or pasted into tickets or chat.

## Python dependencies

Main packages are pinned in **`requirements.txt`** (e.g. Apache Airflow 3.1.x, pandas, requests, boto3). The stack is built for **Python 3.12** to match the official Airflow image tag.

---

