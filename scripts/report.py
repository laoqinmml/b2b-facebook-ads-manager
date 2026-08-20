import argparse
import csv
import json
from pathlib import Path

from facebook_business.adobjects.adaccount import AdAccount

from common import date_windows, init_api, normalize_account_id, write_json


FIELDS = [
    "campaign_id",
    "campaign_name",
    "adset_id",
    "adset_name",
    "ad_id",
    "ad_name",
    "spend",
    "clicks",
    "impressions",
    "ctr",
    "cpc",
    "actions",
    "conversions",
]


def action_value(actions, wanted):
    total = 0.0
    for action in actions or []:
        action_type = action.get("action_type", "")
        if action_type in wanted or any(action_type.endswith(f".{w}") for w in wanted):
            try:
                total += float(action.get("value", 0))
            except (TypeError, ValueError):
                pass
    return total


def pick_conversions(row):
    purchase = action_value(row.get("actions", []), {
        "purchase",
        "omni_purchase",
        "offsite_conversion.fb_pixel_purchase",
        "onsite_conversion.purchase",
    })
    lead_exact = action_value(row.get("actions", []), {"lead"})
    lead_grouped = action_value(row.get("actions", []), {"onsite_conversion.lead_grouped"})
    lead_other = action_value(row.get("actions", []), {
        "omni_lead",
        "offsite_conversion.fb_pixel_lead",
        "onsite_conversion.lead",
    })
    lead = lead_exact or lead_grouped or lead_other
    checkout = action_value(row.get("actions", []), {
        "initiate_checkout",
        "omni_initiated_checkout",
        "offsite_conversion.fb_pixel_initiate_checkout",
    })
    if purchase:
        return purchase, "purchase"
    generic = action_value(row.get("conversions", []), {"conversion", "offsite_conversion"})
    if generic:
        return generic, "conversion"
    if lead:
        return lead, "lead"
    if checkout:
        return checkout, "initiate_checkout"
    return 0.0, "none"


def normalize(row, window, level):
    data = dict(row)
    spend = float(data.get("spend") or 0)
    clicks = int(float(data.get("clicks") or 0))
    impressions = int(float(data.get("impressions") or 0))
    conversions, basis = pick_conversions(data)
    return {
        "window": window,
        "level": level,
        "campaign_id": data.get("campaign_id", ""),
        "campaign_name": data.get("campaign_name", ""),
        "adset_id": data.get("adset_id", ""),
        "adset_name": data.get("adset_name", ""),
        "ad_id": data.get("ad_id", ""),
        "ad_name": data.get("ad_name", ""),
        "spend": round(spend, 2),
        "clicks": clicks,
        "impressions": impressions,
        "ctr": round(float(data.get("ctr") or 0), 4),
        "cpc": round(float(data.get("cpc") or 0), 4),
        "conversions": round(conversions, 4),
        "conversion_basis": basis,
        "cost_per_conversion": round(spend / conversions, 2) if conversions else "",
    }


def collect(account, window_name, since, until, level):
    rows = account.get_insights(
        fields=FIELDS,
        params={
            "level": level,
            "time_range": {"since": since.isoformat(), "until": until.isoformat()},
            "limit": 500,
            "use_unified_attribution_setting": True,
        },
    )
    output = [normalize(row.export_all_data(), window_name, level) for row in rows]
    output.sort(key=lambda r: (r["spend"], r["conversions"]), reverse=True)
    return output


def write_csv(path, rows):
    fields = [
        "window",
        "level",
        "campaign_id",
        "campaign_name",
        "adset_id",
        "adset_name",
        "ad_id",
        "ad_name",
        "spend",
        "clicks",
        "impressions",
        "ctr",
        "cpc",
        "conversions",
        "conversion_basis",
        "cost_per_conversion",
    ]
    with Path(path).open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def totals(rows):
    spend = sum(float(r["spend"]) for r in rows)
    clicks = sum(int(r["clicks"]) for r in rows)
    impressions = sum(int(r["impressions"]) for r in rows)
    conversions = sum(float(r["conversions"]) for r in rows)
    return {
        "spend": round(spend, 2),
        "clicks": clicks,
        "impressions": impressions,
        "conversions": round(conversions, 4),
        "ctr": round(clicks / impressions * 100, 2) if impressions else 0,
        "cpc": round(spend / clicks, 2) if clicks else "",
        "cost_per_conversion": round(spend / conversions, 2) if conversions else "",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--out-dir", default="fb_output")
    args = parser.parse_args()

    init_api()
    account = AdAccount(normalize_account_id(args.account_id))
    account_info = account.api_get(fields=["id", "name", "account_id", "currency", "timezone_name", "account_status"]).export_all_data()

    out = {"account": account_info, "windows": {}}
    flat_rows = []
    for window_name, (since, until) in date_windows().items():
        levels = {}
        for level in ["campaign", "adset", "ad"]:
            rows = collect(account, window_name, since, until, level)
            levels[level] = rows
            flat_rows.extend(rows)
        out["windows"][window_name] = {
            "since": since.isoformat(),
            "until": until.isoformat(),
            "levels": levels,
            "summary": totals(levels["campaign"]),
        }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "fb_report.json", out)
    write_csv(out_dir / "fb_report.csv", flat_rows)
    print(json.dumps({"ok": True, "out_dir": str(out_dir), "summary": out["windows"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
