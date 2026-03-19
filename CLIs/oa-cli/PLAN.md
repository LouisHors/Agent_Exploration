# OA Enhancement Plan

## 1. 告警通知 (Alerting)

### 功能
- 在 `oa collect` 后自动检查指标阈值
- 异常时发送 Slack 通知
- 支持静默期（避免重复告警）

### 实现
- 新增 `oa/alerting.py` 模块
- 修改 `oa collect` 命令，收集后执行检查
- 配置项添加到 `config.yaml`

### 配置示例
```yaml
alerts:
  enabled: true
  channel: slack
  targets:
    - user:U4143EF46  # 你的 Slack ID
  rules:
    - goal: cron_reliability
      metric: success_rate
      threshold: 80
      operator: lt
      message: "🚨 Cron 成功率低于 80%"
    - goal: team_health
      metric: memory_discipline
      threshold: 50
      operator: lt
      message: "⚠️ Memory Discipline 低于 50%"
  cooldown_minutes: 60  # 同一问题 60 分钟内不重复告警
```

## 2. Agent Skill 包

### 功能
- 作为 OpenClaw skill 安装
- Agent 可以查询系统健康度
- Agent 可以根据指标做决策

### 实现
- 新增 `skills/oa/` 目录
- `SKILL.md` 描述功能
- `tools/` 提供具体工具
  - `check_health` - 检查当前健康状态
  - `get_metric` - 获取具体指标值
  - `list_goals` - 列出所有目标

### Agent 使用示例
```
/skill oa

然后 Agent 可以:
- "检查系统健康状态"
- "过去 7 天 Cron 成功率如何"
- "哪个 Agent 最活跃"
```

## 开发顺序

1. 先实现告警通知（基础功能）
2. 再实现 Agent Skill 包（依赖告警的数据）

## 文件变更

```
oa-cli/
├── src/oa/
│   ├── alerting.py          # 新增
│   └── cli.py               # 修改：collect 后调用 alerting
├── skills/
│   └── oa/
│       ├── SKILL.md         # 新增
│       └── tools/
│           └── check.py     # 新增
└── templates/
    └── config.yaml          # 修改：添加 alerts 配置
```
