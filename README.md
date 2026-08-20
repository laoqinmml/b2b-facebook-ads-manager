# B2B Facebook Ads Manager（Codex Skill）

Meta / Facebook 广告账户全流程管理的 Codex 技能，面向外贸 B2B（制造商、机械设备供应商、批发商），基于官方 `facebook_business` SDK 与 Meta Marketing API，默认中文沟通。

首次使用或意图不明时，技能会以引导式对话确认方向，一次只问一组必要问题，不抛长问卷。

## 能力

- 账户表现报告（只读）：近 7 / 30 天、同环比、表单线索与消息对话成效分离、花费上限余额预警，输出中文 Markdown（附 JSON / CSV）
- 广告诊断与优化建议；任何写操作（开关、改预算、删除、A/B 复制、发布暂停副本）都需用户明确确认，新建默认 `PAUSED`，执行后回读复核
- B2B / B2C 受众与兴趣研究（含“隐藏兴趣”），按国家 / 地区估算覆盖（reachestimate），输出可直接粘贴的 `targeting_spec`
- B2B 线索广告构建：从产品事实生成英文文案（5 组 Primary Text / Headline / Description + 中文审查翻译）、9:16 / 1:1 / 1.91:1 版位素材、高意向即时表单，以及 Ads Manager 落地

## 安装

在 Codex 中直接安装：

```text
$skill-installer install https://github.com/laoqinmml/b2b-facebook-ads-manager
```

或手动安装：克隆仓库，把 `b2b-facebook-ads-manager` 文件夹复制到 `~/.codex/skills/`（个人全局）或项目的 `.agents/skills/`（仓库级），然后重启 Codex。

## 依赖与环境变量

```bash
pip install -r requirements.txt
```

| 变量 | 必填 | 说明 |
|---|---|---|
| `FB_ACCESS_TOKEN` | 是 | Meta access token（所需权限见下） |
| `META_APP_ID` | 否 | Meta App ID |
| `META_APP_SECRET` | 否 | Meta App Secret |
| `FB_PROXY` | 否 | HTTP/SOCKS 代理，例如 `socks5h://127.0.0.1:10808` |
| `FB_API_VERSION` | 否 | Graph API 版本，默认 `v25.0` |

所需权限：报告用 `ads_read`；创建 / 更新广告用 `ads_management`；线索广告用 `leads_retrieval`；主页素材用 `pages_show_list`、`pages_manage_ads`；商务资产发现用 `business_management`。

## 基本用法

报告（主脚本，生成中文 Markdown / JSON / CSV）：

```bash
python scripts/generate_fb_markdown_reports.py --account-id <ACCOUNT_ID> --out-dir fb_output
```

轻量报告（JSON / CSV）：

```bash
python scripts/report.py --account-id <ACCOUNT_ID> --out-dir fb_output
```

受众研究（只读）：

```bash
python scripts/audience_keywords.py --industry "包装袋/包材" --mode b2b
python scripts/audience_search.py --account <ACCOUNT_ID> --keywords "packaging,food industry" --class adinterests --out-suffix b2c
python scripts/audience_reach.py --account <ACCOUNT_ID> --file fb_output/audience_picks.csv --countries ID,PH,VN,TH,MY --out sea_reach
python scripts/audience_report.py --reach-file fb_output/sea_reach.csv --countries "ID,PH,VN,TH,MY" --out audience_report
```

复制广告创建 A/B 测试（文案必须由用户提供，脚本不内置默认文案）：

```bash
python scripts/copy_ad_ab_test.py --source-ad-id <AD_ID> --account-id <ACCOUNT_ID> --bodies-json fb_output/bodies.json --titles-json fb_output/titles.json
```

显式启用 / 暂停广告（需用户明确确认）：

```bash
python scripts/set_ad_status.py --ad-id <AD_ID> --status PAUSED
```

## 安全约定

- 新创建的广告默认 `PAUSED`；启用、暂停、删除、改预算、改投放等操作必须先获得用户明确批准。
- 绝不打印、引用或保存 access token；token 只通过环境变量或运行时输入读取。
- 写操作完成后必须回读对象，报告 ID、名称、`configured_status` 与 `effective_status`；`PENDING_REVIEW` / `IN_PROCESS` 不是正常投放状态。
- API 请求自动重试限流与瞬时错误；写操作只重试明确限流，避免重复创建。

## License

MIT
