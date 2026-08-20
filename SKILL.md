---
name: b2b-facebook-ads-manager
description: 管理 Meta/Facebook 广告账户的全流程技能：生成中文 Markdown 表现报告（近 7/30 天、同环比、表单线索/消息对话成效分离、花费上限余额预警）；研究目标受众、兴趣、隐藏兴趣并估算国家/地区覆盖；诊断并安全执行广告操作（新建默认 PAUSED、任何写操作须明确确认）；为制造商、机械设备供应商、外贸 B2B 企业研究产品并生成英文线索广告文案、中文审查翻译、5 组测试版本、产品海报、9:16/1:1/1.91:1 版位素材和高意向即时表单。用户提供 Meta 访问口令、广告账户、Ads Manager 链接或对象 ID，或要求 FB 广告报告、受众研究、诊断、优化、创建/复制广告、写 B2B 广告文案时使用。
---

# B2B Facebook Ads Manager（Meta 广告报告、受众研究、安全操作与 B2B 广告构建）

Meta/Facebook 广告账户的单一入口，覆盖四种工作模式：

- **报告模式**：生成中文 Markdown 账户表现报告（只读）。见 [references/reporting.md](references/reporting.md)。
- **管理模式**：诊断、优化建议，并在用户明确确认后执行写操作。见 [references/management.md](references/management.md)。
- **受众研究模式**：查找目标受众、兴趣、隐藏兴趣，估算国家/地区覆盖。见 [references/audience.md](references/audience.md)。
- **B2B 广告构建模式**：从产品资料到英文文案、中文审查翻译、素材、线索表单和 Ads Manager 落地。见 [references/b2b-ad-builder.md](references/b2b-ad-builder.md)。

## 引导式开场（首次使用 / 意图不明时）

用户第一次使用本技能，或请求模糊（如“帮我看看广告”“用这个技能”“你看着办”）时，先走引导，不直接开跑：

1. 用一两句话说明本技能能做什么，然后只问一个问题让用户选择方向：
   - 账户表现报告（只读）
   - 受众 / 兴趣 / 覆盖研究（只读）
   - 诊断与优化建议（改动需确认）
   - B2B 广告构建（文案 / 素材 / 表单 / 建广告）
2. 按选择进入对应模式；每个模式按 [references/onboarding.md](references/onboarding.md) 的提问顺序收集信息，一次只问一组必要问题，不抛长问卷。
3. 先检查前置条件（token 是否已设置、账户是否已知）；token 只报告“已设置 / 未设置”，粘贴后仅当前进程临时使用。
4. 每完成一步用一句话同步“已确认：…；还需要：…”，结束时区分“已完成结果”和“需用户确认后执行的动作”。

用户请求已明确（如“出近 30 天报告”）时，直接进入对应模式，不重复走开场问题。

## 安全规则（四种模式通用）

- 绝不打印、重复、存储或在报告、日志、代码文件、回复中包含访问口令 `FB_ACCESS_TOKEN`。优先从环境变量读取；用户粘贴的口令只作临时环境变量，用后立即移除。
- 需要代理时用 `FB_PROXY`，常用 `http://127.0.0.1:10808` 或 `socks5h://127.0.0.1:10808`。
- 所有新建广告默认 `PAUSED`。任何写操作（开关 campaign/ad set/ad、改预算或出价、删除/归档、修改在用广告、创建 A/B 副本、发布/启用暂停副本）都必须先取得用户对具体动作的明确确认。
- 每次确认的写操作后，重新读取对象并报告：对象 ID、名称、`configured_status`、`effective_status`。
- `effective_status=PENDING_REVIEW` 表示审核中；`IN_PROCESS` 表示 Meta 正在处理素材或创意。不要把二者误报为正常投放。

## 依赖安装

```bash
pip install -r requirements.txt
```

requirements.txt 位于技能目录下；从其他工作目录运行时，请使用技能文件夹的完整路径。

## 报告快速运行

报告模式优先使用内置脚本：

`scripts/generate_fb_markdown_reports.py`

```powershell
$env:FB_ACCESS_TOKEN='<token from user or environment>'
$env:FB_PROXY='http://127.0.0.1:10808'
python scripts/generate_fb_markdown_reports.py --account-id <ACCOUNT_ID> --out-dir fb_output
Remove-Item Env:\FB_ACCESS_TOKEN -ErrorAction SilentlyContinue
Remove-Item Env:\FB_PROXY -ErrorAction SilentlyContinue
```

脚本位于技能目录 `scripts/` 下；若从其他工作目录运行，请把 `scripts/` 换成技能文件夹的完整路径。

默认 Python 缺依赖时，使用 `codex_app.load_workspace_dependencies` 提供的 Codex 内置 Python。

## 最终回复

最终回复简洁、默认中文。报告给 Markdown 文件链接；写操作给出已确认动作和复核状态；建议区分“分析结论”与“需用户确认后执行”的部分。
