# Facebook Ads Manager (Codex Skill)

一个用于分析和管理 Meta / Facebook 广告账户的 Codex Skill，基于官方 `facebook_business` SDK 与 Meta Marketing API。

支持：

- 账户表现报告（近 7 天 / 30 天 / 上周，按 campaign / ad set / ad 拆分）
- 广告表现诊断与下一步优化建议
- B2B / B2C 受众与兴趣研究（含"隐藏兴趣"）
- 按国家 / 地区估算受众规模（reachestimate）
- 复制现有广告并替换文案，创建 A/B test 广告（默认 `PAUSED`）
- 显式请求下启用 / 暂停广告

## 安装

仓库发布后，在 Codex 中直接安装：

```text
$skill-installer install https://github.com/laoqinmml/b2b-facebook-ads-manager
```

或者手动安装：克隆仓库，把 `facebook-ads-manager` 文件夹复制到 `~/.codex/skills/`（个人全局）或项目的 `.agents/skills/`（仓库级），然后重启 Codex。

## 依赖与环境变量

```bash
pip install facebook_business requests
```

| 变量 | 必填 | 说明 |
|---|---|---|
| `FB_ACCESS_TOKEN` | 是 | Meta access token（所需权限见下） |
| `META_APP_ID` | 否 | Meta App ID |
| `META_APP_SECRET` | 否 | Meta App Secret |
| `FB_PROXY` | 否 | HTTP/SOCKS 代理，例如 `socks5h://127.0.0.1:10808` |

所需权限：报告用 `ads_read`；创建 / 更新广告用 `ads_management`；线索广告用 `leads_retrieval`；主页素材用 `pages_show_list`、`pages_manage_ads`；商务资产发现用 `business_management`。

## 基本用法

报告与诊断：

```bash
python scripts/report.py --account-id 3149616161865068 --out-dir fb_output
```

受众研究（只读）：

```bash
python scripts/audience_keywords.py --industry "包装袋/包材" --mode b2b
python scripts/audience_search.py --account 1495761958760356 --keywords "packaging,food industry" --class adinterests --out-suffix b2c
python scripts/audience_reach.py --account 1495761958760356 --file fb_output/audience_picks.csv --countries ID,PH,VN,TH,MY --out sea_reach
python scripts/audience_report.py --reach-file fb_output/sea_reach.csv --countries "ID,PH,VN,TH,MY" --out audience_report
```

复制广告创建 A/B test：

```bash
python scripts/copy_ad_ab_test.py --source-ad-id 120232398906870392 --account-id 3149616161865068 --out fb_output/created_ab_test_ad.json
```

显式启用 / 暂停广告：

```bash
python scripts/set_ad_status.py --ad-id 120250996069480392 --status ACTIVE
```

## 安全约定

- 新创建的广告默认 `PAUSED`；启用、暂停、删除、改预算、改投放等操作必须先获得用户明确批准。
- 绝不打印、引用或保存 access token；token 只通过环境变量或运行时输入读取。
- 写操作完成后必须回读对象，报告 ID、名称、配置状态与生效状态。

## License

MIT
