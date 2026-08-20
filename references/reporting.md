# 报告模式（Reporting）

生成中文 Markdown 表现报告。优先使用内置脚本：

`scripts/generate_fb_markdown_reports.py`

脚本在输出目录生成 Markdown、JSON、CSV。报告为只读：不修改广告、预算、campaign 状态或账户设置。

## 日期规则

使用广告账户时区，统计完整自然日，截至昨天。

默认窗口：

- 近 7 天
- 近 30 天
- 近 7 天 vs 前 7 天
- 近 30 天 vs 前 30 天

除非用户明确要求，不包含当前未结束的当天；除非用户明确要求，不额外加“完整上一自然周”板块。

用户可见报告中的日期必须显式写明，如 `2026-06-07 至 2026-07-06`。

## 仅统计正在投放的 Campaign

默认只报告当前正在运行的 campaign：

- 包含 `campaign.effective_status = ACTIVE`。
- 从总计、发现、对比和明细表中排除停止、暂停、归档、删除或非活跃的 campaign。

如果用户要求审查非活跃 campaign，单独成板块并清楚标注。

## 指标

- 花费：`spend`
- 点击：`clicks`（对应 Ads Manager“点击次数”）
- 展示：`impressions`
- 覆盖：`reach`
- CTR：`clicks / impressions`
- CPC：`spend / clicks`
- 统一归因：拉取 insights 时传 `use_unified_attribution_setting=true`

除非用户明确要求链接点击分析，不用 `link_click` 当总点击。

## 成效类型规则

绝不把不同成效类型合并进同一个“单次成效费用”。

表单线索 campaign（如 `OUTCOME_LEADS`）：

- 成效类型：`表单线索`
- 首选 action：`lead`
- 仅在 `lead` 缺失时的回退：`onsite_conversion.lead_grouped`、`offsite_complete_registration_add_meta_leads`、`offsite_search_add_meta_leads` 或相关 Meta leads action
- 不要把多个 lead 类 action 相加；它们往往只是同一 Meta 线索事件的不同形态。

互动/消息 campaign（如 `OUTCOME_ENGAGEMENT` 或消息类 campaign）：

- 成效类型：`发起消息对话`
- 使用消息对话发起 action。

单次成效费用：

- 优先使用 Meta 对所选 action 的 `cost_per_action_type`（当可用时）。
- 否则用 `spend / result_count`。

某时段只有一种成效类型时，总览可包含成效数和单次成效费用，两项都加粗。

某时段有多种成效类型时，总览只显示流量指标；成效数和单次成效费用只放进按成效类型拆分的汇总。

## 花费上限余额规则

始终在报告顶部附近显示账户花费上限剩余余额。

`账户花费上限剩余余额 = spend_cap - amount_spent`

不要把 Meta 的 `balance` 或 `amount_spent` 单独当可用余额；很多账户里该值代表已花费金额而非剩余预算。

剩余余额低于 `USD 200.00` 时，整行余额标红并标注为低余额警告；不低于时正常显示余额行。

## Markdown 格式

使用中文标题和标签。

报告顺序：

1. 账户元信息和花费上限剩余余额
2. 总览表
3. 按成效类型汇总
4. 对比板块
5. Campaign、Ad Set、Ad 明细表
6. 发现与建议

货币单位放在表头而非单元格：`花费（USD）`、`单次费用（USD）`、`CPC（USD）`。

表头保持简短，避免出现单字符窄列；用 `单次费用（USD）`，不用 `单次成效费用（USD）`。

所有 `成效` 和 `单次费用` 数据值加粗。

对比规则：

- 红色表示变差；绿色表示改善。
- 按成效类型分别对比。
- 前一时段某成效类型数据不足时用 `-` 或说明已跳过；不混用成效类型。

广告创意名称：当广告展示 ≥ 1000 且 CTR < 0.8% 时，标红。

除非用户明确要求，不单独加“口径说明”板块。

## 明细表

按 campaign、ad set、ad 拆分。

包含：花费、点击、展示、覆盖、CTR、CPC、成效数、成效类型、单次成效费用。

移除重复或噪声列，如 `目标` 和原始 metric/action 列。

## 发现

用缩进对象层级写具体发现：

```markdown
- 高花费无成效：
  - 广告系列：...
  - 广告组：...
  - 广告：...
  - 数据：花费 USD ..., 成效为 0，当前识别口径为 ...
```

重点标记：

- 高花费无成效
- 同成效类型内单次成效费用过高
- CTR 偏弱或 CPC 异常偏高
- 花费集中在某一 campaign/ad set/ad
- 缺少 A/B 测试
- 相对上一时段是改善还是变差

只有同时满足以下两点才标记“高花费无成效”：

- 该广告成效数为 0。
- 花费 ≥ 该成效类型的账户平均单次成效费用。

不要把低于平均单次成效费用的小测试误标为“高花费无成效”。

## 数据核对

若 API 数据与 Ads Manager 截图不一致，先排查再下结论：

- 日期范围不一致
- 误含当前未结束的当天
- `clicks` vs `link_click`
- 多个 lead action 字段被相加
- 缺少 `use_unified_attribution_setting=true`
- 层级不同：campaign、ad set 或 ad
- 后台筛选：仅活跃、选中对象、所有广告、已删除/归档对象
- 生成的中文文件编码问题

Markdown/JSON 用 UTF-8；若 CSV 需用 Excel 打开则用 UTF-8-SIG。

## 输出处理

提供 Markdown 路径。仅在有用时提 JSON/CSV。

用户之后要 PDF 时，仅在验证过 Markdown 内容后，从定稿的 Markdown 转换。
