# 管理模式（Management）

诊断、撰写优化建议，并在用户明确确认后执行写操作。

除非用户明确确认该具体写操作，不修改广告、预算、campaign 状态或账户设置。

## API 方式

广告创建、复制、状态变更或更深层的对象管理，优先使用官方 Meta Business SDK：

```bash
pip install -r requirements.txt
```

若 SDK 安装或导入不可用，谨慎使用直接 Graph API 调用。保持写调用隔离、已确认，并随后重读状态。

本技能附带 Graph API 辅助脚本：`scripts/copy_ad_ab_test.py`（复制广告做 A/B 文案测试）、`scripts/set_ad_status.py`（ACTIVE/PAUSED 状态变更）、`scripts/report.py`（轻量报告）。使用前先读取脚本参数，并同样遵守本节的确认与复核规则。`copy_ad_ab_test.py` 的 A/B 文案必须由用户通过 `--bodies-json`、`--titles-json` 提供，脚本不内置默认文案。

## 写操作

需要明确确认的写操作包括：

- 打开/关闭 campaign、ad set 或 ad
- 修改预算或出价设置
- 删除或归档对象
- 修改在用广告
- 创建 A/B 测试副本
- 发布或启用暂停的副本

每次确认的写操作后，重新读取对象并报告：

- 对象 ID
- 对象名称
- `configured_status`
- `effective_status`

`effective_status` 为 `PENDING_REVIEW` 时说明在审核中；`IN_PROCESS` 表示 Meta 正在处理素材或创意。

## A/B 测试副本规则

复制广告做 A/B 测试时：

1. 读取源广告、creative、campaign、ad set、表单、CTA、落地链接和相关设置。
2. 保留原 campaign、ad set、媒体、表单、CTA、落地链接和投放设置。
3. 除非用户要求更多，只优化文案字段（primary text、headline、description）。
4. 新广告创建为 `PAUSED`。
5. 报告源广告 ID、新广告 ID、新 creative ID、`configured_status`、`effective_status`。
6. 仅在用户明确说 `打开`、`开启`、`发布`、`启用` 等词时才激活。
7. 激活后重读状态并报告。

B2B/工厂/批发/制造类文案角度和完整建广告流程，见 [b2b-ad-builder.md](b2b-ad-builder.md)。
