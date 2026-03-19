# OA Skill — Operational Analytics for OpenClaw Agents

This skill allows agents to query system health and metrics from OA (Operational Analytics).

## Installation

```bash
# Copy skill to your agent's skills directory
cp -r skills/oa ~/.openclaw/skills/

# Or symlink for development
ln -s $(pwd)/skills/oa ~/.openclaw/skills/oa
```

## Usage

Once installed, agents can use these tools:

### check_health

Check current system health status.

```
/skill oa check_health
```

Returns:
```json
{
  "overall": "critical",
  "goals": [
    {"name": "Cron Reliability", "status": "healthy", "value": "100%"},
    {"name": "Team Health", "status": "critical", "value": "0%"}
  ]
}
```

### get_metric

Get a specific metric value.

```
/skill oa get_metric --goal cron_reliability --metric success_rate --days 7
```

Returns:
```json
{
  "goal": "cron_reliability",
  "metric": "success_rate",
  "current": 100.0,
  "trend": "stable",
  "history": [
    {"date": "2026-03-19", "value": 100.0},
    {"date": "2026-03-18", "value": 95.0}
  ]
}
```

### list_goals

List all configured goals and their metrics.

```
/skill oa list_goals
```

## Agent Instructions

Add this to your agent's instructions:

```markdown
## Operational Awareness

You have access to OA (Operational Analytics) to check system health:

- Use `oa check_health` before starting critical tasks
- If cron reliability < 80%, report issues before proceeding
- If memory discipline < 50%, remind agents to log their work
- Query trends with `oa get_metric --days N` for context

Always log your actions to memory for tracking.
```

## Configuration

The skill reads OA configuration from:
- `~/clawd/agents/jarvis/oa-project/config.yaml` (default)
- Or set `OA_CONFIG_PATH` environment variable

## Requirements

- OA CLI installed and initialized
- SQLite database with collected metrics
