"""批量搜索 Meta 受众（兴趣/职业/行为/行业分类），全量输出、去重、落盘。

用法示例：
    python audience_search.py --account 1495761958760356 \
        --keywords "packaging,food industry,cosmetics" \
        --class adinterests --out-suffix b2c

    python audience_search.py --account 1495761958760356 \
        --keywords "purchasing manager,founder,small business owners" \
        --class adworkjobtitles --type work_positions --out-suffix b2b

    python audience_search.py --account 1495761958760356 \
        --keywords "small business owners,business page admins" \
        --class adtargetingcategories --keep-all --out-suffix b2b_people
"""

import argparse
import csv
import json
import time
from pathlib import Path

from common import graph_get, normalize_account_id, write_json

OUT_DIR = Path("fb_output")


def search_keyword(account, keyword, target_class, limit, locale, suggest):
    if suggest:
        params = {
            "type": "adinterestsuggestion",
            "interest_list": json.dumps([keyword]),
            "limit": limit,
            "locale": locale,
        }
        return graph_get("search", params).get("data", [])
    params = {
        "q": keyword,
        "class": target_class,
        "limit": limit,
        "locale": locale,
    }
    return graph_get(f"{account}/targetingsearch", params).get("data", [])


def row_size(r):
    if r.get("audience_size"):
        return r["audience_size"]
    return r.get("audience_size_lower_bound") or 0


def main():
    parser = argparse.ArgumentParser(description="批量搜索 Meta 受众")
    parser.add_argument("--account", required=True, help="广告账户 ID")
    parser.add_argument("--keywords", required=True, help="逗号分隔的关键词列表")
    parser.add_argument("--class", dest="target_class", default="adinterests",
                        help="targetingsearch class: adinterests/adworkjobtitles/adbehaviors/adtargetingcategories")
    parser.add_argument("--type", dest="keep_types", default=None,
                        help="只保留指定类型（逗号分隔），默认只保留 interests")
    parser.add_argument("--keep-all", action="store_true", help="保留所有返回类型")
    parser.add_argument("--min-size", type=int, default=0, help="最小受众规模过滤，0 表示不过滤")
    parser.add_argument("--max-size", type=int, default=0, help="最大受众规模过滤，0 表示不过滤")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--locale", default="en_US")
    parser.add_argument("--out-suffix", default="audiences", help="输出文件名后缀")
    parser.add_argument("--print-rows", type=int, default=50, help="终端打印多少条")
    parser.add_argument("--suggest", action="store_true",
                        help="用 adinterestsuggestion 代替 targetingsearch（某词搜不到时备用）")
    args = parser.parse_args()

    account = normalize_account_id(args.account)
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    keep_types = None
    if args.keep_all:
        keep_types = None
    elif args.keep_types:
        keep_types = set(t.strip() for t in args.keep_types.split(",") if t.strip())
    else:
        keep_types = {"interests"}

    seen = {}
    per_keyword = {}
    for kw in keywords:
        try:
            rows = search_keyword(account, kw, args.target_class, args.limit, args.locale, args.suggest)
        except RuntimeError as exc:
            print(f"[{kw}] 失败: {exc}")
            continue
        rows = [r for r in rows if keep_types is None or r.get("type") in keep_types]
        per_keyword[kw] = len(rows)
        for r in rows:
            rid = r["id"]
            if rid not in seen:
                r["search_keyword"] = kw
                seen[rid] = r
        time.sleep(0.3)

    all_rows = list(seen.values())
    filtered = [
        r
        for r in all_rows
        if (args.min_size == 0 or row_size(r) >= args.min_size)
        and (args.max_size == 0 or row_size(r) <= args.max_size)
    ]
    filtered.sort(key=row_size)

    print("各关键词返回条数:")
    for kw, n in per_keyword.items():
        print(f"  {kw:<28} {n}")
    print(f"\n去重后共 {len(all_rows)} 条，过滤后 {len(filtered)} 条（按规模升序）:\n")
    for r in filtered[: args.print_rows]:
        lo = row_size(r)
        hi = r.get("audience_size_upper_bound") or ""
        path = " / ".join(r.get("path") or [])
        print(f"{lo:>12,}-{hi:>12,}  {r['id']}  {r['name']}  [{path}]  <{r['search_keyword']}>")

    out_csv = OUT_DIR / f"audience_{args.out_suffix}.csv"
    out_json = OUT_DIR / f"audience_{args.out_suffix}.json"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "search_keyword",
                "type",
                "name",
                "id",
                "audience_size_lower_bound",
                "audience_size_upper_bound",
                "path",
                "description",
            ],
        )
        writer.writeheader()
        for r in filtered:
            writer.writerow(
                {
                    "search_keyword": r.get("search_keyword", ""),
                    "type": r.get("type", ""),
                    "name": r.get("name", ""),
                    "id": r.get("id", ""),
                    "audience_size_lower_bound": r.get("audience_size_lower_bound", ""),
                    "audience_size_upper_bound": r.get("audience_size_upper_bound", ""),
                    "path": " / ".join(r.get("path") or []),
                    "description": r.get("description", ""),
                }
            )
    write_json(out_json, filtered)
    print(f"\n已保存: {out_csv}\n已保存: {out_json}")


if __name__ == "__main__":
    main()
