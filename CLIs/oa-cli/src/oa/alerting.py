"""Alerting module for OA — sends notifications when metrics breach thresholds."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from oa.core.config import ProjectConfig


@dataclass
class AlertRule:
    """A single alert rule configuration."""
    goal: str
    metric: str
    threshold: float
    operator: str  # 'lt', 'gt', 'eq', 'lte', 'gte'
    message: str


@dataclass
class AlertConfig:
    """Alert configuration from config.yaml."""
    enabled: bool
    channel: str
    targets: list[str]
    rules: list[AlertRule]
    cooldown_minutes: int = 60


class AlertManager:
    """Manages metric alerting with cooldown and deduplication."""

    def __init__(self, config: AlertConfig, db_path: Path):
        self.config = config
        self.db_path = db_path
        self._init_alert_log()

    def _init_alert_log(self) -> None:
        """Create alert log table if not exists."""
        db = sqlite3.connect(str(self.db_path))
        db.execute("""
            CREATE TABLE IF NOT EXISTS alert_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_key TEXT NOT NULL,
                goal TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL,
                threshold REAL,
                message TEXT,
                sent_at TEXT DEFAULT (datetime('now'))
            )
        """)
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_alert_log_rule_date 
            ON alert_log(rule_key, sent_at)
        """)
        db.commit()
        db.close()

    def check_and_alert(self, date: str) -> list[dict]:
        """Check all rules and send alerts for breached thresholds."""
        if not self.config.enabled:
            return []

        alerts_triggered = []
        db = sqlite3.connect(str(self.db_path))

        for rule in self.config.rules:
            # Get current metric value
            row = db.execute(
                """SELECT value FROM goal_metrics 
                   WHERE date = ? AND goal = ? AND metric = ?""",
                (date, rule.goal, rule.metric)
            ).fetchone()

            if not row:
                continue

            value = row[0]
            rule_key = f"{rule.goal}:{rule.metric}"

            # Check if threshold breached
            if not self._is_breached(value, rule.threshold, rule.operator):
                continue

            # Check cooldown
            if self._is_in_cooldown(db, rule_key):
                continue

            # Send alert
            alert = self._send_alert(rule, value, date)
            if alert:
                alerts_triggered.append(alert)
                self._log_alert(db, rule_key, rule, value)

        db.close()
        return alerts_triggered

    def _is_breached(self, value: float, threshold: float, operator: str) -> bool:
        """Check if value breaches threshold based on operator."""
        ops = {
            'lt': lambda v, t: v < t,
            'gt': lambda v, t: v > t,
            'eq': lambda v, t: v == t,
            'lte': lambda v, t: v <= t,
            'gte': lambda v, t: v >= t,
        }
        return ops.get(operator, lambda v, t: False)(value, threshold)

    def _is_in_cooldown(self, db: sqlite3.Connection, rule_key: str) -> bool:
        """Check if this rule was alerted recently."""
        cooldown = timedelta(minutes=self.config.cooldown_minutes)
        since = (datetime.now() - cooldown).isoformat()

        row = db.execute(
            """SELECT 1 FROM alert_log 
               WHERE rule_key = ? AND sent_at > ?
               LIMIT 1""",
            (rule_key, since)
        ).fetchone()

        return row is not None

    def _send_alert(self, rule: AlertRule, value: float, date: str) -> dict | None:
        """Send alert via configured channel."""
        message = self._format_message(rule, value, date)

        if self.config.channel == 'slack':
            return self._send_slack(message, rule)
        elif self.config.channel == 'console':
            print(f"[ALERT] {message}")
            return {'channel': 'console', 'message': message}

        return None

    def _format_message(self, rule: AlertRule, value: float, date: str) -> str:
        """Format alert message."""
        op_symbols = {'lt': '<', 'gt': '>', 'eq': '=', 'lte': '≤', 'gte': '≥'}
        op = op_symbols.get(rule.operator, rule.operator)

        return (
            f"{rule.message}\n"
            f"📊 Goal: {rule.goal}\n"
            f"📈 Metric: {rule.metric}\n"
            f"🔢 Value: {value} {op} {rule.threshold}\n"
            f"📅 Date: {date}"
        )

    def _send_slack(self, message: str, rule: AlertRule) -> dict | None:
        """Send alert to Slack via OpenClaw message tool."""
        try:
            # Import here to avoid circular dependency
            from oa.core.slack_notifier import SlackNotifier

            notifier = SlackNotifier()
            for target in self.config.targets:
                notifier.send(target, message)

            return {
                'channel': 'slack',
                'targets': self.config.targets,
                'message': message,
            }
        except Exception as e:
            print(f"Failed to send Slack alert: {e}")
            return None

    def _log_alert(self, db: sqlite3.Connection, rule_key: str,
                   rule: AlertRule, value: float) -> None:
        """Log alert to database."""
        db.execute(
            """INSERT INTO alert_log (rule_key, goal, metric, value, threshold, message)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (rule_key, rule.goal, rule.metric, value, rule.threshold, rule.message)
        )
        db.commit()


def load_alert_config(config_dict: dict) -> AlertConfig:
    """Load alert config from config.yaml dict."""
    alerts = config_dict.get('alerts', {})

    rules = []
    for rule_dict in alerts.get('rules', []):
        rules.append(AlertRule(
            goal=rule_dict['goal'],
            metric=rule_dict['metric'],
            threshold=rule_dict['threshold'],
            operator=rule_dict.get('operator', 'lt'),
            message=rule_dict['message'],
        ))

    return AlertConfig(
        enabled=alerts.get('enabled', False),
        channel=alerts.get('channel', 'console'),
        targets=alerts.get('targets', []),
        rules=rules,
        cooldown_minutes=alerts.get('cooldown_minutes', 60),
    )
