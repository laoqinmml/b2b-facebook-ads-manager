"""估算选中受众在指定国家/地区的实际覆盖人数（reachestimate）。

用法：
    python audience_reach.py --account 1495761958760356 \
        --file fb_output/audience_picks.csv \
        --countries ID,PH,VN,TH,MY,SG,MM,KH,LA,BN,TL \
        --out sea_reach

输入 CSV 列: id,name,type（type 为 interests/behaviors/work_positions/industries 等）
"""

import argparse
import csv
import json
import time
from pathlib import Path

from common import graph_get, normalize_account_id, write_json

OUT_DIR = Path("fb_output")
SEA_COUNTRIES = ["ID", "PH", "VN", "TH", "MY", "SG", "MM", "KH", "LA", "BN", "TL"]

TYPE_FIELDS = {
    "interests": "interests",
    "behaviors": "behaviors",
    "work_positions": "work_positions",
    "industries": "industries",
    "life_events": "life_events",
    "demographics": "demographics",
    "education_majors": "education_majors",
    "work_employers": "work_employers",
}


def estimate_reach(account, audience_id, audience_type, countries):
    field = TYPE_FIELDS.get(audience_type)
    if not field:
        return None
    spec = {
        "geo_locations": {"countries": countries},
        field: [{"id": audience_id}],
    }
    body = graph_get(f"{account}/reachestimate", {"targeting_spec": json.dumps(spec)})
    return body.get("data", {})


def main():
    parser = argparse.ArgumentParser(description="估算受众在指定国家的覆盖人数")
    parser.add_argument("--account", required=True, help="广告账户 ID")
    parser.add_argument("--file", required=True, help="受众 CSV，列: id,name,type")
    parser.add_argument("--countries", default=",".join(SEA_COUNTRIES),
                        help="逗号分隔的国家 ISO 代码")
    parser.add_argument("--out", default="sea_reach", help="输出文件名（不含扩展名）")
    parser.add_argument("--sleep", type=float, default=0.3)
    args = parser.parse_args()

    account = normalize_account_id(args.account)
    countries = [c.strip().upper() for c in args.countries.split(",") if c.strip()]

    rows = []
    seen = set()
    with open(args.file, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rid = row["id"].strip()
            rtype = row["type"].strip()
            if rid in seen:
                continue
            seen.add(rid)
            rows.append({"id": rid, "name": row["name"].strip(), "type": rtype})

    print(f"共 {len(rows)} 个受众，国家: {', '.join(countries)}\n")
    results = []
    for i, r in enumerate(rows, 1):
        try:
            data = estimate_reach(account, r["id"], r["type"], countries)
        except RuntimeError as exc:
            print(f"[{i}/{len(rows)}] {r['name']} 失败: {exc}")
            continue
        if data is None:
            print(f"[{i}/{len(rows)}] {r['name']} 类型 {r['type']} 不受支持，跳过")
            continue
        lo = data.get("users_lower_bound") or data.get("users") or 0
        hi = data.get("users_upper_bound") or data.get("users") or 0
        results.append({**r, "sea_lower": lo, "sea_upper": hi})
        print(f"[{i}/{len(rows)}] {r['name']:<52} {lo:>12,} ~ {hi:>12,}")
        time.sleep(args.sleep)

    results.sort(key=lambda x: x["sea_lower"], reverse=True)
    out_csv = OUT_DIR / f"{args.out}.csv"
    out_json = OUT_DIR / f"{args.out}.json"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "id", "type", "sea_lower", "sea_upper"])
        writer.writeheader()
        writer.writerows(results)
    write_json(out_json, results)
    print(f"\n已保存: {out_csv}\n已保存: {out_json}")


if __name__ == "__main__":
    main()
