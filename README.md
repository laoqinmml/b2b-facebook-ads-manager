# B2B Facebook Ads Manager（Codex Skill）

Meta / Facebook 广告账户全流程管理的 Codex 技能，面向外贸 B2B（制造商、机械设备供应商、批发商、工厂），基于官方 `facebook_business` SDK 与 Meta Marketing API。默认中文沟通；首次使用或意图不明时走引导式对话，一次只问一组必要问题。

## 能力总览

四种工作模式，从账户诊断到广告落地全覆盖：

**1. 账户表现报告（只读）**

- 中文 Markdown 报告（附 JSON / CSV），按 campaign / ad set / ad 拆分
- 默认窗口：近 7 天、近 30 天、7 天同环比、30 天同环比；使用广告账户时区、截至昨天
- 只统计投放中（`effective_status=ACTIVE`）的 campaign
- 表单线索与消息对话成效分离统计，不合并不同成效类型
- 花费上限剩余余额预警（`spend_cap - amount_spent`，低于 USD 200 标红）
- 自动发现：高花费无成效、单次成效费用过高、CTR 偏弱、花费集中、缺少 A/B 测试、环比变化

**2. 诊断与安全操作**

- 只读诊断 + 优化建议；所有写操作先列出具体动作，等待用户明确确认
- 新建广告默认 `PAUSED`；支持开关、改预算出价、删除归档、A/B 复制、发布暂停副本
- 每次写操作后回读对象并报告 ID、名称、`configured_status`、`effective_status`
- 正确区分 `PENDING_REVIEW`（审核中）、`IN_PROCESS`（素材处理中）与正常投放

**3. 受众 / 兴趣研究**

- 兴趣、职位、行为、行业分类批量搜索（含“隐藏兴趣”），跨关键词去重
- `reachestimate` 按国家 / 地区估算真实覆盖
- 输出 CSV / JSON、Markdown 调研报告和可直接粘贴的 `targeting_spec` 示例
- 内置行业关键词词库（包装、食品、日化、服装、电子等），支持自定义补充

**4. B2B 线索广告构建**

- 从产品事实建立简报，输出 5 组相互独立且有事实支撑的测试角度
- 英文 Primary Text / Headline / Description 各 5 组，附逐条中文审查翻译
- 9:16 / 1:1 / 1.91:1 三套版位素材（保留实拍设备结构，不虚构部件）
- 高意向即时表单（4-5 个采购筛选问题，含隐私政策提示）
- Ads Manager 落地：复制兼容设置、新建 PAUSED、写后逐项复核
- 严格区分用户事实、产品页声明与推断；不编造价格、MOQ、认证、交期、产能、客户数量或评价

## 目录结构

```text
b2b-facebook-ads-manager/
|-- SKILL.md                 技能入口：模式路由、引导开场、安全规则
|-- agents/openai.yaml       界面元数据与默认提示
|-- references/              各模式详细规范
|   |-- onboarding.md        引导式开场与各模式提问顺序
|   |-- reporting.md         报告口径：窗口、指标、成效类型、余额预警
|   |-- management.md        写操作确认与复核规则
|   |-- audience.md          受众研究流程与经验要点
|   |-- b2b-ad-builder.md    广告文案、素材、表单与落地规范
|   `-- environment.md       环境变量与权限说明
|-- scripts/                 Python 辅助脚本
|   |-- generate_fb_markdown_reports.py  主报告脚本（中文 Markdown/JSON/CSV）
|   |-- report.py            轻量报告（JSON/CSV，账户时区、仅 ACTIVE）
|   |-- audience_keywords.py 行业关键词词库展开
|   |-- audience_search.py   targetingsearch 批量搜索、去重、落盘
|   |-- audience_reach.py    reachestimate 国家/地区覆盖估算
|   |-- audience_report.py   受众调研 Markdown + targeting_spec
|   |-- copy_ad_ab_test.py   复制广告做 A/B 文案测试（默认 PAUSED）
|   |-- set_ad_status.py     启用/暂停状态变更
|   `-- common.py            公共请求层：token 安全、重试退避、分页游标
|-- requirements.txt         依赖
|-- README.md
`-- LICENSE
```

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

所需权限：报告用 `ads_read`；创建 / 更新广告用 `ads_management`；线索广告用 `leads_retrieval`；主页素材用 `pages_show_list`、`pages_manage_ads`；商务资产发现用 `business_management`。长期自动化建议使用 Business Manager System User token。

## 快速开始

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
- 绝不打印、引用或保存 access token；token 只通过环境变量或运行时输入读取，用后即删。
- 写操作完成后必须回读对象，报告 ID、名称、`configured_status` 与 `effective_status`；`PENDING_REVIEW` / `IN_PROCESS` 不是正常投放状态。
- API 请求自动重试限流与瞬时错误；写操作只重试明确限流，避免重复创建；异常信息不包含带 token 的完整 URL。

## 维护

仓库默认提交身份：老秦外贸运营手记 <qinshijia111@gmail.com>。修改后：

```bash
git add .
git commit -m "改了什么"
git push
```

## License

MIT
