"""
Microsoft Teams alerts (DAG-level) via workflow / incoming webhook.

Uses Airflow Variable ``teams_webhook_secret``. Success: one message when the DAG run succeeds.
Failure: one message listing failed task(s) with links to the DAG run and to the first failed task’s logs.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import requests
from airflow.configuration import conf
from airflow.sdk import Variable
from airflow.utils.state import TaskInstanceState

logger = logging.getLogger(__name__)

TEAMS_WEBHOOK_VARIABLE = "teams_webhook_secret"


def _get_webhook() -> str:
    try:
        return (Variable.get(TEAMS_WEBHOOK_VARIABLE, default="") or "").strip()
    except Exception:
        logger.exception("Could not read Airflow Variable %s", TEAMS_WEBHOOK_VARIABLE)
        return ""


def _api_base() -> str:
    return conf.get("api", "base_url", fallback="http://localhost:8080/").rstrip("/")


def _dag_run_url(dag_id: str, run_id: str) -> str:
    return f"{_api_base()}/dags/{dag_id}/runs/{quote(run_id)}"


def _collect_failed_tasks(context: dict[str, Any]) -> tuple[list[str], str]:
    """
    Return (human-readable failed task lines, primary task log URL if any).
    """
    lines: list[str] = []
    log_url = ""
    dag_run = context.get("dag_run")
    if dag_run is not None:
        try:
            failed = dag_run.get_task_instances(state=[TaskInstanceState.FAILED])
            for ti in failed:
                lines.append(f"{ti.task_id} (try {ti.try_number})")
                if not log_url and hasattr(ti, "log_url"):
                    log_url = ti.log_url
        except Exception:
            logger.exception("Could not load failed task instances for Teams notification")
    if not lines:
        ti = context.get("task_instance") or context.get("ti")
        if ti is not None:
            tid = getattr(ti, "task_id", "?")
            lines.append(f"{tid} (from DAG callback context)")
            if hasattr(ti, "log_url"):
                log_url = ti.log_url
        else:
            lines.append("(open Airflow UI — failed task details not available in callback context)")
    return lines, log_url


def _dag_ids(context: dict[str, Any]) -> tuple[str, str, str]:
    dag = context.get("dag")
    dag_id = dag.dag_id if dag is not None else "unknown"
    dr = context.get("dag_run")
    run_id = str(getattr(dr, "run_id", None) or context.get("run_id") or "—")
    logical = getattr(dr, "logical_date", None) if dr is not None else None
    if logical is None:
        logical = context.get("logical_date") or context.get("ds")
    logical_s = str(logical) if logical is not None else "—"
    return dag_id, run_id, logical_s


def _post_message_card(notification: dict[str, Any]) -> None:
    webhook = _get_webhook()
    if not webhook:
        logger.warning(
            "Skipping Teams notification: set Airflow Variable %r to your webhook URL",
            TEAMS_WEBHOOK_VARIABLE,
        )
        return
    headers = {"Content-Type": "application/json; charset=utf-8"}
    try:
        r = requests.post(webhook, json=notification, headers=headers, timeout=30)
        r.raise_for_status()
    except requests.RequestException:
        logger.exception("Teams webhook request failed")
    except Exception:
        logger.exception("Unexpected error sending Teams notification")


def notify_teams_dag_success(context: dict[str, Any]) -> None:
    """``on_success_callback`` on the DAG — fires once per successful DAG run."""
    dag_id, run_id, logical_s = _dag_ids(context)
    run_url = _dag_run_url(dag_id, run_id) if run_id != "—" else ""

    notification: dict[str, Any] = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "title": "Airflow DAG succeeded",
        "summary": f"DAG {dag_id} completed successfully",
        "themeColor": "107C10",
        "sections": [
            {
                "activityTitle": f"DAG `{dag_id}` finished successfully",
                "facts": [
                    {"name": "Logical date", "value": logical_s},
                    {"name": "Run ID", "value": run_id},
                ],
            }
        ],
    }
    actions: list[dict[str, Any]] = []
    if run_url:
        actions.append(
            {
                "@type": "OpenUri",
                "name": "Open DAG run",
                "targets": [{"os": "default", "uri": run_url}],
            }
        )
    if actions:
        notification["potentialAction"] = actions

    logger.info("Sending Teams DAG success notification for %s run %s", dag_id, run_id)
    _post_message_card(notification)


def notify_teams_dag_failure(context: dict[str, Any]) -> None:
    """``on_failure_callback`` on the DAG — fires when the DAG run fails; highlights failed task(s)."""
    dag_id, run_id, logical_s = _dag_ids(context)
    reason = str(context.get("reason") or "—")
    failed_tasks, task_log_url = _collect_failed_tasks(context)
    run_url = _dag_run_url(dag_id, run_id) if run_id != "—" else ""

    failed_block = "\n".join(f"• {t}" for t in failed_tasks[:20])
    if len(failed_tasks) > 20:
        failed_block += f"\n… and {len(failed_tasks) - 20} more"

    notification: dict[str, Any] = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "title": "Airflow DAG failed",
        "summary": f"DAG {dag_id} failed — check failed task(s)",
        "themeColor": "D83B01",
        "sections": [
            {
                "activityTitle": f"DAG `{dag_id}` failed",
                "activitySubtitle": "See failed task(s) below",
                "facts": [
                    {"name": "Failed task(s)", "value": failed_block or "—"},
                    {"name": "Logical date", "value": logical_s},
                    {"name": "Run ID", "value": run_id},
                    {"name": "Callback reason", "value": reason},
                ],
            }
        ],
    }

    actions: list[dict[str, Any]] = []
    if run_url:
        actions.append(
            {
                "@type": "OpenUri",
                "name": "Open DAG run (grid)",
                "targets": [{"os": "default", "uri": run_url}],
            }
        )
    if task_log_url:
        actions.append(
            {
                "@type": "OpenUri",
                "name": "Logs — first failed task",
                "targets": [{"os": "default", "uri": task_log_url}],
            }
        )
    if actions:
        notification["potentialAction"] = actions

    logger.info("Sending Teams DAG failure notification for %s run %s", dag_id, run_id)
    _post_message_card(notification)
