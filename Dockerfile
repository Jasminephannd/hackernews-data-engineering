FROM apache/airflow:3.1.8-python3.12

COPY requirements.txt /opt/airflow/

USER root
RUN apt-get update && apt-get install -y gcc python3-dev

USER airflow

RUN pip install --no-cache-dir -r /opt/airflow/requirements.txt