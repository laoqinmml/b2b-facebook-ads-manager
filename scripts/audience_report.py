"""把 audience_reach 的结果生成 Markdown 报告 + targeting_spec 示例。

用法：
    python audience_report.py --reach-file fb_output/sea_reach.csv \
        --countries "ID,PH,VN,TH,MY,SG,MM,KH,LA,BN,TL" \
        --out audience_report
"""

import argparse
import csv
import json
from datetime import date
from pathlib import Path

from common import TYPE_FIELDS

OUT_DIR = Path("fb_output")


def main():
    parser = argparse.ArgumentParser(description="生成受众调研报告")
    parser.add_argument("--reach-file", required=True, help="audience_reach 输出的 CSV")
    parser.add_argument("--countries", required=True, help="国家 ISO 列表，用于生成 targeting_spec")
    parser.add_argument("--out", default="audience_report", help="输出文件名（不含扩展名）")
    args = parser.parse_args()

    countries = [c.strip().upper() for c in args.countries.split(",") if c.strip()]
    rows = []
    with open(args.reach_file, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    rows.sort(key=lambda x: int(x.get("sea_lower") or 0), reverse=True)

    lines = []
    lines.append("# Facebook 受众调研报告")
    lines.append("")
    lines.append(f"- 生成日期: {date.today().isoformat()}")
    lines.append(f"- 目标国家: {', '.join(countries)}")
    lines.append(f"- 受众数量: {len(rows)}")
    lines.append("")
    lines.append("> 覆盖人数为 Meta 估算值；受众规模只反映 Facebook 人群，不代表全部市场。")
    lines.append("")
    lines.append("## 覆盖人数（降序）")
    lines.append("")
    lines.append("| # | 受众 | 类型 | 覆盖人数 |")
    lines.append("|---|------|------|---------|")
    for i, r in enumerate(rows, 1):
        lo = int(r.get("sea_lower") or 0)
        hi = int(r.get("sea_upper") or 0)
        lines.append(f"| {i} | {r['name']} | {r['type']} | {lo:,} ~ {hi:,} |")
    lines.append("")
    lines.append("## targeting_spec 示例")
    lines.append("")
    lines.append("每个受众可单独放入一个广告组，或组合使用（同一 spec 内多个条件为 AND，多个广告组为 OR）。")
    lines.append("")
    for i, r in enumerate(rows, 1):
        field = TYPE_FIELDS.get(r.get("type", ""))
        if not field:
            continue
        spec = {
            "geo_locations": {"countries": countries},
            field: [{"id": r["id"]}],
        }
        lines.append(f"### {i}. {r['name']}（{r['type']}）")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(spec, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")
    lines.append("## 投放建议")
    lines.append("")
    lines.append("- 东南亚等新兴市场：职业定向（work_positions）覆盖极薄，优先行为和兴趣。")
    lines.append("- 覆盖人数是全球估算叠加国家后的结果，未叠加年龄/性别；实际投放以广告组估算为准。")
    lines.append("- 新建广告组默认 PAUSED，确认后再激活。")
    lines.append("")

    out_md = OUT_DIR / f"{args.out}.md"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"已保存: {out_md}")


if __name__ == "__main__":
    main()
