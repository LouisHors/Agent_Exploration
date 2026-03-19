"""OA Skill tools for OpenClaw agents."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


def _get_db_path() -> Path:
    """Find OA database path."""
    # Check environment variable
    if env_path := Path.home() / "clawd/agents/jarvis/oa-project/data/monitor.db":
        if env_path.exists():
            return env_path

    # Default locations
    defaults = [
        Path.home() / "clawd/agents/jarvis/oa-project/data/monitor.db",
        Path.home() / "oa-project/data/monitor.db",
        Path.cwd() / "data/monitor.db",
    ]

    for path in defaults:
        if path.exists():
            return path

    raise FileNotFoundError("OA database not found. Run `oa init` first.")


def check_health() -> str:
    """Check current system health status.

    Returns a summary of all goals and their health status.
    """
    try:
        db_path = _get_db_path()
        db = sqlite3.connect(str(db_path))

        today = datetime.now().strftime("%Y-%m-%d")

        # Get latest metrics for each goal
        rows = db.execute("""
            SELECT g.goal, g.metric, g.value, g.unit, cfg.healthy, cfg.warning
            FROM goal_metrics g
            JOIN (
                SELECT goal, metric, MAX(date) as max_date
                FROM goal_metrics
                GROUP BY goal, metric
            ) latest ON g.goal = latest.goal AND g.metric = latest.metric AND g.date = latest.max_date
            LEFT JOIN (
                SELECT 'cron_reliability' as goal, 'success_rate' as metric, 95 as healthy, 80 as warning
                UNION ALL
                SELECT 'team_health', 'active_agent_count', 3, 2
                UNION ALL
                SELECT 'team_health', 'memory_discipline', 80, 50
            ) cfg ON g.goal = cfg.goal AND g.metric = cfg.metric
        """).fetchall()

        if not rows:
            return "No data available. Run `oa collect` first."

        results = []
        for goal, metric, value, unit, healthy, warning in rows:
            healthy = healthy or 0
            warning = warning or 0

            if value >= healthy:
                status = "🟢 healthy"
            elif value >= warning:
                status = "🟡 warning"
            else:
                status = "🔴 critical"

            sep = " " if unit and not unit.startswith("%") else ""
            results.append(f"  {status} {goal}/{metric}: {value}{sep}{unit}")

        db.close()

        return "System Health:\n" + "\n".join(results)

    except Exception as e:
        return f"Error checking health: {e}"


def get_metric(goal: str, metric: str, days: int = 1) -> str:
    """Get a specific metric value and trend.

    Args:
        goal: Goal ID (e.g., 'cron_reliability')
        metric: Metric name (e.g., 'success_rate')
        days: Number of days of history to include
    """
    try:
        db_path = _get_db_path()
        db = sqlite3.connect(str(db_path))

        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        rows = db.execute(
            """SELECT date, value, unit FROM goal_metrics
               WHERE goal = ? AND metric = ? AND date >= ?
               ORDER BY date DESC""",
            (goal, metric, since)
        ).fetchall()

        if not rows:
            return f"No data for {goal}/{metric} in the last {days} days."

        # Format results
        lines = [f"📊 {goal}/{metric} (last {days} days):\n"]

        for date, value, unit in rows:
            sep = " " if unit and not unit.startswith("%") else ""
            lines.append(f"  {date}: {value}{sep}{unit}")

        # Calculate trend
        if len(rows) >= 2:
            latest = rows[0][1]
            previous = rows[1][1]
            if latest > previous:
                trend = "📈 improving"
            elif latest < previous:
                trend = "📉 declining"
            else:
                trend = "➡️ stable"
            lines.append(f"\nTrend: {trend}")

        db.close()
        return "\n".join(lines)

    except Exception as e:
        return f"Error getting metric: {e}"


def list_goals() -> str:
    """List all configured goals and their metrics."""
    try:
        db_path = _get_db_path()
        db = sqlite3.connect(str(db_path))

        rows = db.execute(
            """SELECT DISTINCT goal, metric, unit FROM goal_metrics
               ORDER BY goal, metric"""
        ).fetchall()

        if not rows:
            return "No goals configured. Run `oa collect` first."

        current_goal = None
        lines = ["📋 Configured Goals:\n"]

        for goal, metric, unit in rows:
            if goal != current_goal:
                lines.append(f"\n{goal}:")
                current_goal = goal
            lines.append(f"  • {metric} ({unit})")

        db.close()
        return "\n".join(lines)

    except Exception as e:
        return f"Error listing goals: {e}"


if __name__ == "__main__":
    # Test the tools
    print(check_health())
    print()
    print(get_metric("cron_reliability", "success_rate", days=7))
    print()
    print(list_goals())
