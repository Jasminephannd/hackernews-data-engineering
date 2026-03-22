# Data Pipeline: Hacker News, Airflow, Celery, PostgreSQL, S3 (AWS)

This project implements an **end-to-end data pipeline (ETL)** that ingests, processes, and stores **Hacker News** data using a modern data engineering stack.

The pipeline is orchestrated with **Apache Airflow + Celery**, uses **PostgreSQL and Redis** for task management, and stores data in **Amazon S3** as a raw data lake.

Originally inspired by a Reddit-based pipeline, this project was adapted to use **Hacker News (Algolia API)** due to recent restrictions on Reddit API access. This reflects a realistic engineering decision: **adapting data sources while preserving pipeline architecture**.

---

# Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Data Flow](#data-flow)
- [Configuration](#configuration)
- [Setup Instructions](#setup-instructions)
- [Key Learnings](#key-learnings)
- [Future Improvements](#future-improvements)

---

# Overview

The pipeline performs:

1. **Extract**  
   Fetch Hacker News posts via the public API (no authentication required)

2. **Transform**  
   Clean and normalize data (timestamps, types, schema consistency)

3. **Load**  
   - Store locally as CSV (staging layer)  
   - Upload to **Amazon S3 (raw layer)**  

4. **AWS Analytics Layer**  
   - AWS Glue → schema + ETL  
   - Athena → SQL querying  

---

# Architecture

<img width="1600" height="612" alt="image" src="https://github.com/user-attachments/assets/29fe5870-50df-4fc6-ba64-aef7a7cbf2de" />

| Tool | What it is | What it does |
|------|-----------|-------------|
| **Hacker News API (Algolia)** | Public REST API | Provides structured story data (title, author, score, comments) |
| **Apache Airflow** | Workflow orchestrator | Schedules and manages ETL pipeline |
| **Celery** | Distributed task queue | Enables parallel task execution |
| **PostgreSQL** | Metadata database | Stores Airflow state and execution metadata |
| **Docker Compose** | Container orchestration | Runs the entire system locally |
| **Amazon S3** | Data lake | Stores raw and transformed data |
| **AWS Glue** | Serverless ETL | Cleans and transforms data (e.g., date normalisation, column pruning) |
| **AWS Glue Data Catalog** | Metadata layer | Registers schemas for querying |
| **Amazon Athena** | Serverless SQL engine | Queries data directly from S3 |

---

# Project Structure

| Path | Description |
|------|------------|
| `dags/hn_dag.py` | Defines Airflow DAG (extract → upload) |
| `pipelines/hn_pipeline.py` | Core ETL orchestration |
| `pipelines/aws_s3_pipeline.py` | Handles S3 upload |
| `etls/hn_etl.py` | Extract + transform logic |
| `etls/aws_etl.py` | S3 interaction via boto3 |
| `utils/constants.py` | Configuration loader |
| `config/config.conf` | AWS credentials (gitignored) |
| `docker-compose.yml` | Infrastructure setup |
| `Dockerfile` | Custom Airflow image |

---

# Data Flow 

## 1. Extraction
- Airflow triggers the pipeline
- Calls Hacker News API:

https://hn.algolia.com/api/v1/search

## 2. Transformation
Using Pandas:
- Convert timestamps → UTC format
- Normalise fields (author, score, comments)
- Clean text fields

## 3. Local Staging
- Save as CSV:

/opt/airflow/data/output/hn_YYYYMMDD.csv

## 4. Load to S3
- Upload via boto3:

s3://<bucket>/raw/

## 5. AWS Processing
- Glue:
  - convert CSV → Parquet
  - keep `created_utc` as date only
  - drop unnecessary columns (e.g. `story_text`)
- Athena:
  - query using SQL

---

# Configuration

- AWS credentials stored in:

config/config.conf (gitignored)


- Airflow environment:

airflow.env


---

# Setup Instructions

1. **Clone the repository**
```bash
git clone https://github.com/Jasminephannd/hackernews-data-engineering.git
```
2. **Create a virtual environment**
```bash
python3 -m venv venv
```
3. **Activate the virtual environment**
```bash
source venv/bin/activate
```
5. **Install dependencies**
```bash
pip install -r requirements.txt
```
6. **Set up configuration file**
```bash
mv config/config.conf.example config/config.conf
```
7. **Start Docker containers**
```bash
docker-compose up -d
```
8. **Open Airflow Web UI**
```bash
http://localhost:8080
```
---


# Key Learnings

This project demonstrates:

- Designing an **end-to-end ETL pipeline**
- Orchestrating workflows using **Airflow + Celery**
- Managing distributed systems (**Redis + Postgres**)
- Building a **data lake on S3**
- Performing transformations using:
  - Pandas (local)
  - Spark (AWS Glue)
- Understanding **schema evolution and data quality**
- Adapting architecture when APIs change (Reddit → Hacker News)

---

# Future Improvements

- Convert CSV → **Parquet (columnar, efficient)**
- Add **partitioning by date**
- Implement **data quality checks in Glue**
- Add **dashboard (Athena + BI tool)**
- Deploy pipeline to **AWS (production-ready)**
