# 受众研究模式（Audience Research）

使用 `scripts/audience_*.py` 系列脚本查找目标受众、兴趣或“隐藏兴趣”，做 B2B/B2C 受众研究，并估算特定国家/地区的覆盖。此工作流只读（targetingsearch / reachestimate）；之后要建广告，仍遵循本技能 [management.md](management.md) 的 PAUSED 和确认规则。

## 前置条件

1. 确认 `FB_ACCESS_TOKEN` 已设置（获取方式见 [environment.md](environment.md)）。受众研究端点 `targetingsearch`、`reachestimate` 需要 `ads_management`。
2. 校验令牌并列出可访问账户：

```bash
python -c "import json,sys; sys.path.insert(0,'scripts'); from common import graph_get; [print(a['id'], a.get('name','')) for a in graph_get('me/adaccounts', {'limit':100}).get('data',[])]"
```

多个账户时请用户选择。

## 询问顺序

- 目标国家/地区（可多选，映射为 ISO 代码）。
- 产品或行业（自由文本，例如“包材定制/包装袋”）。
- B2B、B2C 或两者都要。

## 关键词

内置行业库 + 自定义补充：

```bash
python scripts/audience_keywords.py --industry "包装袋/包材" --mode b2b
python scripts/audience_keywords.py --industry "日化" --mode b2c --extra "custom term"
```

未知行业：请用户给出 3-10 个代表关键词（品类词、品牌、使用场景短语）。

## 搜索

两条轨道都用 `scripts/audience_search.py`，默认不过滤规模（`--min-size 0 --max-size 0`），全部输出由用户决定。

B2C / 兴趣轨道：

```bash
python scripts/audience_search.py --account <ACCOUNT_ID> --keywords "packaging,food industry,cosmetics" --class adinterests --out-suffix b2c
```

B2B / 身份轨道（职位、行为、行业）：

```bash
python scripts/audience_search.py --account <ACCOUNT_ID> --keywords "purchasing manager,founder,small business owners" --class adworkjobtitles --type work_positions --out-suffix b2b_titles
python scripts/audience_search.py --account <ACCOUNT_ID> --keywords "small business owners,business page admins" --class adtargetingcategories --keep-all --out-suffix b2b_people
```

脚本会跨关键词去重、标注来源关键词，并把 CSV/JSON 输出到 `fb_output/`。

## 选择

把排序结果给用户，请其挑选受众 ID（写入 CSV，列：`id,name,type`）。默认只展示清单让用户决定；用户要求时才自动推荐。

## 估算覆盖

```bash
python scripts/audience_reach.py --account <ACCOUNT_ID> --file fb_output/audience_picks.csv --countries ID,PH,VN,TH,MY,SG,MM,KH,LA,BN,TL --out sea_reach
```

## 交付

```bash
python scripts/audience_report.py --reach-file fb_output/sea_reach.csv --countries "ID,PH,VN,TH,MY,SG,MM,KH,LA,BN,TL" --out audience_report
```

输出 Markdown 摘要和可直接粘贴的 `targeting_spec` JSON 示例。

## 经验要点

- Meta 里的“Southeast Asia”是兴趣，不是地理位置；按 ISO 国家代码列表做地域定向。
- `work_positions`（职位定向）在新兴市场很薄（东南亚常约 1000 以下）；B2B 优先用行为（Small business owners、Business page admins）和宽泛兴趣。
- `audience_size` 来自 targetingsearch，是无地理维度的全球估计；国家/地区覆盖以 reachestimate 为准。
- 不要把 `targetingsearch` 的全球规模当成国家覆盖，也不要混淆不同数据口径。
