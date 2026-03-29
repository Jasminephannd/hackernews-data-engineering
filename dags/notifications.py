"""
Microsoft Teams failure alerts via Incoming Webhook.

Set Airflow Variable ``teams_webhook_secret`` to the full webhook URL from Teams
(Workflows / Incoming Webhook). If unset or empty, notifications are skipped.
"""
import logging
from typing import Any

import requests
from airflow.sdk import Variable

logger = logging.getLogger(__name__)

TEAMS_VARIABLE_KEY = "teams_webhook_secret"


def notify_teams(context: dict[str, Any]) -> None:
    """
    Post a MessageCard to Teams when a task fails.

    Intended for ``default_args['on_failure_callback']`` so each failed task fires once.
    """
    try:
        webhook = (Variable.get(TEAMS_VARIABLE_KEY, default="") or "").strip()
    except Exception:
        logger.exception("Could not read Airflow Variable %s", TEAMS_VARIABLE_KEY)
        return

    if not webhook:
        logger.warning(
            "Skipping Teams notification: set Airflow Variable %r to your webhook URL",
            TEAMS_VARIABLE_KEY,
        )
        return

    ti = context.get("task_instance") or context.get("ti")
    dag = context.get("dag")
    dag_id = dag.dag_id if dag is not None else (ti.dag_id if ti is not None else "unknown")
    task_key = context.get("task_instance_key_str") or (
        f"{dag_id}__{ti.task_id}__{getattr(ti, 'run_id', '')}" if ti is not None else "unknown"
    )

    log_url = ""
    if ti is not None and hasattr(ti, "log_url"):
        log_url = ti.log_url

    logical_date = context.get("ds") or context.get("logical_date")
    if logical_date is not None and not isinstance(logical_date, str):
        logical_date = str(logical_date)

    exc = context.get("exception")
    err_text = str(exc) if exc is not None else ""

    notification: dict[str, Any] = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "title": "Airflow task failed",
        "summary": f"Task {task_key} failed",
        "themeColor": "D83B01",
        "sections": [
            {
                "activityTitle": f"Task `{getattr(ti, 'task_id', '?')}` failed",
                "activitySubtitle": f"DAG: {dag_id}",
                "facts": [
                    {"name": "Logical date", "value": str(logical_date or "—")},
                    {"name": "Run ID", "value": str(getattr(ti, "run_id", "") or "—")},
                    *(
                        [{"name": "Error", "value": err_text[:2000]}]
                        if err_text
                        else []
                    ),
                ],
            }
        ],
    }

    if log_url:
        notification["potentialAction"] = [
            {
                "@type": "OpenUri",
                "name": "View logs",
                "targets": [{"os": "default", "uri": log_url}],
            }
        ]

    headers = {"Content-Type": "application/json; charset=utf-8"}
    try:
        logger.info("Sending Teams notification for failed task %s", task_key)
        r = requests.post(webhook, json=notification, headers=headers, timeout=30)
        r.raise_for_status()
    except requests.RequestException:
        logger.exception("Teams webhook request failed")
    except Exception:
        logger.exception("Unexpected error sending Teams notification")
