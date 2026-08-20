import argparse
import csv
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


API_VERSION = "v25.0"
GRAPH = f"https://graph.facebook.com/{API_VERSION}"
LEVELS = ["campaign", "adset", "ad"]
LEVEL_LABELS = {"campaign": "广告系列", "adset": "广告组", "ad": "广告"}
REPORT_FONT = "FBReportCN"


def require_token():
    token = os.environ.get("FB_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("FB_ACCESS_TOKEN is not set. 请先在环境变量中配置 Meta 访问令牌。")
    return token


def normalize_account_id(account_id):
    value = str(account_id).strip()
    return value[4:] if value.startswith("act_") else value


def graph_get(path, params=None):
    payload = dict(params or {})
    payload["access_token"] = require_token()
    url = f"{GRAPH}/{path.lstrip('/')}?{urllib.parse.urlencode(payload)}"
    return url_get(url)


def url_get(url):
    proxy = os.environ.get("FB_PROXY")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy})) if proxy else None
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        if opener:
            with opener.open(request, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"error": {"message": body[:500]}}
        raise RuntimeError(json.dumps(payload, ensure_ascii=False, indent=2)) from None


def paged_get(path, params=None):
    payload = graph_get(path, params)
    while True:
        for row in payload.get("data", []):
            yield row
        next_url = payload.get("paging", {}).get("next")
        if not next_url:
            break
        payload = url_get(next_url)


def account_today(account):
    tz_name = account.get("timezone_name") or "Asia/Shanghai"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("Asia/Shanghai")
    return datetime.now(tz).date()


def date_windows(today):
    end = today - timedelta(days=1)
    return {
        "last_30_days": {"label": "过去30天", "since": end - timedelta(days=29), "until": end},
        "last_7_days": {"label": "过去7天", "since": end - timedelta(days=6), "until": end},
    }


def comparison_windows(today):
    end = today - timedelta(days=1)
    current_7_since = end - timedelta(days=6)
    current_30_since = end - timedelta(days=29)
    return {
        "last_7_days": {
            "label": "过去7天 vs 上个7天",
            "current_since": current_7_since,
            "current_until": end,
            "previous_since": current_7_since - timedelta(days=7),
            "previous_until": current_7_since - timedelta(days=1),
        },
        "last_30_days": {
            "label": "过去30天 vs 上个30天",
            "current_since": current_30_since,
            "current_until": end,
            "previous_since": current_30_since - timedelta(days=30),
            "previous_until": current_30_since - timedelta(days=1),
        },
    }


def action_map(actions):
    result = {}
    for item in actions or []:
        key = item.get("action_type", "")
        try:
            value = float(item.get("value", 0) or 0)
        except (TypeError, ValueError):
            value = 0.0
        result[key] = result.get(key, 0.0) + value
    return result


def first_action_value(actions, keys):
    values = action_map(actions)
    for key in keys:
        if values.get(key):
            return values[key], key
    return 0.0, "none"


def pick_result(row):
    values = action_map(row.get("actions"))
    purchase, purchase_basis = first_action_value(
        row.get("actions"),
        [
            "purchase",
            "omni_purchase",
            "offsite_conversion.fb_pixel_purchase",
            "onsite_conversion.purchase",
        ],
    )
    lead, lead_basis = first_action_value(
        row.get("actions"),
        [
            "lead",
            "onsite_conversion.lead_grouped",
            "offsite_complete_registration_add_meta_leads",
            "offsite_search_add_meta_leads",
            "omni_lead",
            "offsite_conversion.fb_pixel_lead",
            "onsite_conversion.lead",
        ],
    )
    message, message_basis = first_action_value(
        row.get("actions"),
        [
            "onsite_conversion.messaging_conversation_started_7d",
            "onsite_conversion.messaging_conversation_started",
            "messaging_conversation_started_7d",
            "messaging_conversation_started",
            "onsite_conversion.total_messaging_connection",
            "onsite_conversion.messaging_first_reply",
            "onsite_conversion.messaging_user_subscribed",
        ],
    )
    checkout, checkout_basis = first_action_value(
        row.get("actions"),
        [
            "initiate_checkout",
            "omni_initiated_checkout",
            "offsite_conversion.fb_pixel_initiate_checkout",
        ],
    )
    generic, generic_basis = first_action_value(row.get("conversions"), ["conversion", "offsite_conversion"])
    objective = str(row.get("objective") or "").upper()
    names = " ".join(
        str(row.get(key) or "") for key in ["campaign_name", "adset_name", "ad_name"]
    ).lower()
    objective_is_lead = "LEAD" in objective
    objective_is_message = "MESSAGE" in objective or "MESSAGING" in objective
    objective_is_engagement = "ENGAGEMENT" in objective
    name_is_message = "消息" in names or "互动" in names or "message" in names or "messenger" in names
    name_is_lead = "表单" in names or "lead" in names

    if objective_is_lead or (name_is_lead and not objective_is_message and not objective_is_engagement):
        return lead, "表单线索", lead_basis
    if objective_is_message or objective_is_engagement or name_is_message:
        return message, "发起消息对话", message_basis

    if purchase:
        return purchase, "购买", purchase_basis
    if message:
        return message, "发起消息对话", message_basis
    if lead:
        return lead, "表单线索", lead_basis
    if generic:
        return generic, "转化", generic_basis
    if checkout:
        return checkout, "发起结账", checkout_basis
    return 0.0, "无成效", "none"


def normalize_row(row, window_key, level):
    spend = float(row.get("spend") or 0)
    clicks = int(float(row.get("clicks") or 0))
    impressions = int(float(row.get("impressions") or 0))
    reach = int(float(row.get("reach") or 0))
    result_count, result_type, basis = pick_result(row)
    return {
        "window": window_key,
        "level": level,
        "campaign_id": row.get("campaign_id", ""),
        "campaign_name": row.get("campaign_name", ""),
        "adset_id": row.get("adset_id", ""),
        "adset_name": row.get("adset_name", ""),
        "ad_id": row.get("ad_id", ""),
        "ad_name": row.get("ad_name", ""),
        "objective": row.get("objective", ""),
        "spend": round(spend, 2),
        "clicks": clicks,
        "impressions": impressions,
        "reach": reach,
        "ctr": round(clicks / impressions * 100, 2) if impressions else 0,
        "cpc": round(spend / clicks, 2) if clicks else "",
        "result_count": round(result_count, 4),
        "result_type": result_type,
        "result_basis": basis,
        "cost_per_result": round(spend / result_count, 2) if result_count else "",
    }


def collect_active_campaigns(account_id):
    rows = list(
        paged_get(
            f"act_{account_id}/campaigns",
            {
                "fields": "id,name,effective_status,configured_status",
                "limit": 500,
            },
        )
    )
    active = [
        row
        for row in rows
        if str(row.get("effective_status") or "").upper() == "ACTIVE"
    ]
    return {row["id"]: row for row in active if row.get("id")}


def collect_level(account_id, window_key, since, until, level, active_campaign_ids=None):
    fields = ",".join(
        [
            "campaign_id",
            "campaign_name",
            "adset_id",
            "adset_name",
            "ad_id",
            "ad_name",
            "spend",
            "clicks",
            "impressions",
            "reach",
            "objective",
            "actions",
            "conversions",
        ]
    )
    params = {
        "level": level,
        "fields": fields,
        "time_range": json.dumps({"since": since.isoformat(), "until": until.isoformat()}),
        "limit": 500,
        "use_unified_attribution_setting": "true",
    }
    rows = [normalize_row(row, window_key, level) for row in paged_get(f"act_{account_id}/insights", params)]
    if active_campaign_ids is not None:
        rows = [row for row in rows if row.get("campaign_id") in active_campaign_ids]
    rows.sort(key=lambda r: (r["spend"], r["result_count"]), reverse=True)
    return rows


def totals(rows):
    spend = sum(float(row["spend"]) for row in rows)
    clicks = sum(int(row["clicks"]) for row in rows)
    impressions = sum(int(row["impressions"]) for row in rows)
    reach = sum(int(row["reach"]) for row in rows)
    result_count = sum(float(row["result_count"]) for row in rows)
    mix = {}
    breakdown = {}
    for row in rows:
        label = row.get("result_type") or "无成效"
        mix[label] = mix.get(label, 0.0) + float(row["result_count"])
        bucket = breakdown.setdefault(
            label,
            {"spend": 0.0, "clicks": 0, "impressions": 0, "reach": 0, "result_count": 0.0},
        )
        bucket["spend"] += float(row["spend"])
        bucket["clicks"] += int(row["clicks"])
        bucket["impressions"] += int(row["impressions"])
        bucket["reach"] += int(row["reach"])
        bucket["result_count"] += float(row["result_count"])
    mix = {key: round(value, 4) for key, value in mix.items() if value}
    breakdown = {
        key: {
            "spend": round(value["spend"], 2),
            "clicks": value["clicks"],
            "impressions": value["impressions"],
            "reach": value["reach"],
            "result_count": round(value["result_count"], 4),
            "ctr": round(value["clicks"] / value["impressions"] * 100, 2) if value["impressions"] else 0,
            "cpc": round(value["spend"] / value["clicks"], 2) if value["clicks"] else "",
            "cost_per_result": round(value["spend"] / value["result_count"], 2) if value["result_count"] else "",
        }
        for key, value in breakdown.items()
        if value["spend"] or value["result_count"]
    }
    return {
        "spend": round(spend, 2),
        "clicks": clicks,
        "impressions": impressions,
        "reach": reach,
        "result_count": round(result_count, 4),
        "result_mix": mix,
        "result_breakdown": breakdown,
        "ctr": round(clicks / impressions * 100, 2) if impressions else 0,
        "cpc": round(spend / clicks, 2) if clicks else "",
        "cost_per_result": round(spend / result_count, 2) if result_count else "",
    }


def collect_summary(account_id, window_key, since, until, active_campaign_ids=None):
    rows = collect_level(account_id, window_key, since, until, "campaign", active_campaign_ids=active_campaign_ids)
    return totals(rows)


def pct_change(current, previous, better_lower=False):
    if previous in ("", None) or current in ("", None) or float(previous) == 0:
        return None
    change = (float(current) - float(previous)) / float(previous)
    improved = change < 0 if better_lower else change > 0
    return {"change": round(change * 100, 2), "improved": improved}


def build_comparisons(account_id, today, active_campaign_ids=None):
    comparisons = {}
    for key, window in comparison_windows(today).items():
        previous = collect_summary(account_id, f"previous_{key}", window["previous_since"], window["previous_until"], active_campaign_ids=active_campaign_ids)
        current = collect_summary(account_id, f"compare_{key}", window["current_since"], window["current_until"], active_campaign_ids=active_campaign_ids)
        serialized_window = {
            "label": window["label"],
            "current_since": window["current_since"].isoformat(),
            "current_until": window["current_until"].isoformat(),
            "previous_since": window["previous_since"].isoformat(),
            "previous_until": window["previous_until"].isoformat(),
        }
        if previous["spend"] == 0 and previous["impressions"] == 0:
            comparisons[key] = {
                **serialized_window,
                "skipped": True,
                "reason": "上个周期没有足够数据，跳过对比。",
            }
            continue
        comparisons[key] = {
            **serialized_window,
            "skipped": False,
            "current": current,
            "previous": previous,
            "changes": {
                "spend": pct_change(current["spend"], previous["spend"]),
                "result_count": pct_change(current["result_count"], previous["result_count"]),
                "cost_per_result": pct_change(current["cost_per_result"], previous["cost_per_result"], better_lower=True),
                "ctr": pct_change(current["ctr"], previous["ctr"]),
                "cpc": pct_change(current["cpc"], previous["cpc"], better_lower=True),
            },
        }
    return comparisons


def collect_account(account_id):
    account = graph_get(
        f"act_{account_id}",
        {"fields": "id,name,account_id,currency,timezone_name,account_status,balance,amount_spent,spend_cap"},
    )
    today = account_today(account)
    windows = date_windows(today)
    active_campaigns = collect_active_campaigns(account_id)
    active_campaign_ids = set(active_campaigns)
    report = {
        "account": account,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "campaign_filter": {
            "effective_status": "ACTIVE",
            "campaigns": list(active_campaigns.values()),
        },
        "windows": {},
        "comparisons": {},
    }
    flat_rows = []
    for window_key, window in windows.items():
        levels = {}
        for level in LEVELS:
            rows = collect_level(account_id, window_key, window["since"], window["until"], level, active_campaign_ids=active_campaign_ids)
            levels[level] = rows
            flat_rows.extend([{**row, "since": window["since"].isoformat(), "until": window["until"].isoformat()} for row in rows])
        report["windows"][window_key] = {
            "label": window["label"],
            "since": window["since"].isoformat(),
            "until": window["until"].isoformat(),
            "levels": levels,
            "summary": totals(levels["campaign"]),
        }
    report["comparisons"] = build_comparisons(account_id, today, active_campaign_ids=active_campaign_ids)
    return report, flat_rows


def fmt_money(value, currency):
    if value == "" or value is None:
        return "-"
    return f"{currency} {float(value):,.2f}"


def fmt_money_value(value):
    if value == "" or value is None:
        return "-"
    return f"{float(value):,.2f}"


def minor_currency_amount(raw):
    if raw in ("", None):
        return None
    try:
        return float(raw) / 100
    except (TypeError, ValueError):
        return None


def account_spend_limit_remaining(account):
    spent = minor_currency_amount(account.get("amount_spent"))
    if spent is None:
        spent = minor_currency_amount(account.get("balance"))
    spend_cap = minor_currency_amount(account.get("spend_cap"))
    if spend_cap is None or spent is None or spend_cap <= 0:
        return None
    return max(spend_cap - spent, 0)


def fmt_num(value):
    if value == "" or value is None:
        return "-"
    number = float(value)
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}"


def object_name(row, level):
    if level == "campaign":
        return row.get("campaign_name") or row.get("campaign_id") or "-"
    if level == "adset":
        return row.get("adset_name") or row.get("adset_id") or "-"
    return row.get("ad_name") or row.get("ad_id") or "-"


def is_low_ctr_ad(row):
    return (
        str(row.get("level")) == "ad"
        and int(float(row.get("impressions") or 0)) >= 1000
        and float(row.get("ctr") or 0) < 0.8
    )


def red(value):
    return f'<span style="color:red">{value}</span>'


def object_path_bullets(row):
    campaign = row.get("campaign_name") or row.get("campaign_id") or "-"
    adset = row.get("adset_name") or row.get("adset_id") or "-"
    ad = row.get("ad_name") or row.get("ad_id") or "-"
    if is_low_ctr_ad(row):
        ad = red(ad)
    return f"  - 广告系列：{campaign}\n  - 广告组：{adset}\n  - 广告：{ad}"


def objective_label(value):
    mapping = {
        "OUTCOME_LEADS": "leads",
        "OUTCOME_ENGAGEMENT": "engagement",
        "OUTCOME_TRAFFIC": "traffic",
        "OUTCOME_SALES": "sales",
        "OUTCOME_AWARENESS": "awareness",
        "MESSAGES": "messages",
        "LEAD_GENERATION": "leads",
    }
    return mapping.get(str(value or ""), str(value or ""))


def truncate(value, limit=42):
    text = str(value or "-")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def build_findings(report):
    window = report["windows"]["last_30_days"]
    campaign_rows = window["levels"]["campaign"]
    ad_rows = window["levels"]["ad"]
    summary = window["summary"]
    findings = []
    if not campaign_rows:
        return ["过去30天没有拉到广告花费数据，请确认账户、日期范围和权限。"]

    total_spend = summary["spend"]
    top_campaign = campaign_rows[0]
    if total_spend and top_campaign["spend"] / total_spend >= 0.7:
        findings.append(
            f"花费集中：最高花费广告系列占过去30天总花费 {top_campaign['spend'] / total_spend:.0%}，需要关注预算是否过度集中。"
        )

    breakdown = summary.get("result_breakdown") or {}
    zero_result = []
    for row in ad_rows:
        if row["spend"] <= 0 or float(row["result_count"]) != 0:
            continue
        avg_cost = (breakdown.get(row.get("result_type")) or {}).get("cost_per_result")
        if avg_cost not in ("", None) and float(avg_cost) > 0 and row["spend"] >= float(avg_cost):
            zero_result.append(row)
    if zero_result:
        top = zero_result[0]
        findings.append(
            f"高花费无成效：\n{object_path_bullets(top)}\n  - 数据：花费 {fmt_money(top['spend'], report['account'].get('currency', ''))}，成效为 0，已超过同成效类型平均单次费用，当前识别口径为 {top['result_type']}。"
        )

    resulted = [row for row in ad_rows if row["cost_per_result"] != ""]
    if resulted:
        avg_cpa = summary["cost_per_result"]
        expensive = [row for row in resulted if avg_cpa and row["cost_per_result"] >= float(avg_cpa) * 1.5]
        if expensive:
            top = expensive[0]
            findings.append(
                f"单次成效费用偏高：\n{object_path_bullets(top)}\n  - 数据：单次成效费用为 {fmt_money(top['cost_per_result'], report['account'].get('currency', ''))}，明显高于账户均值。"
            )

    weak_ctr = [row for row in ad_rows if row["impressions"] >= 1000 and row["ctr"] < 0.8]
    if weak_ctr:
        top = weak_ctr[0]
        findings.append(f"CTR 偏弱：\n{object_path_bullets(top)}\n  - 数据：展示超过 1,000 次但 CTR 低于 0.8%，建议检查素材和首句卖点。")

    if not findings:
        findings.append("未发现明显异常；建议继续观察 7 天趋势，并维持素材和文案测试节奏。")
    return findings[:5]


def build_actions(report):
    return [
        "先处理过去30天有花费但无成效的广告，降低浪费预算。",
        "对 CTR 偏低的广告补充 2-3 个新素材或首句文案，保持原广告不动，用暂停状态复制测试。",
        "分别看表单广告和消息互动广告的单次成效费用，不把线索和发起消息对话混为同一个业务结果。",
    ]


def format_result_mix(summary):
    mix = summary.get("result_mix") or {}
    if not mix:
        return "-"
    return " / ".join(f"{key} {fmt_num(value)}" for key, value in mix.items())


def single_result_type(summary):
    breakdown = summary.get("result_breakdown") or {}
    if len(breakdown) == 1:
        return next(iter(breakdown.values()))
    return None


def format_change(change, suffix=""):
    if not change:
        return "-"
    value = change["change"]
    direction = "改善" if change["improved"] else "变差"
    color = "green" if change["improved"] else "red"
    sign = "+" if value > 0 else ""
    return f'<span style="color:{color}">{sign}{value:.2f}%（{direction}）{suffix}</span>'


def metric_change(current_value, previous_value, better_lower=False):
    return format_change(pct_change(current_value, previous_value, better_lower=better_lower))


def comparison_lines(report):
    lines = []
    for key in ["last_7_days", "last_30_days"]:
        comp = (report.get("comparisons") or {}).get(key)
        if not comp:
            continue
        if comp.get("skipped"):
            lines.append(f"{comp['label']}：{comp.get('reason', '数据不足，跳过对比。')}")
            continue
        current = comp["current"]
        previous = comp["previous"]
        changes = comp["changes"]
        lines.append(
            f"{comp['label']}：成效 {fmt_num(previous['result_count'])} -> {fmt_num(current['result_count'])}，"
            f"单次成效费用 {fmt_money(previous['cost_per_result'], report['account'].get('currency', ''))} -> {fmt_money(current['cost_per_result'], report['account'].get('currency', ''))}"
            f"（{format_change(changes.get('cost_per_result'))}），CTR {previous['ctr']:.2f}% -> {current['ctr']:.2f}%（{format_change(changes.get('ctr'))}）。"
        )
    return lines


def result_type_comparison_rows(report, window_key):
    comp = (report.get("comparisons") or {}).get(window_key)
    if not comp or comp.get("skipped"):
        return []
    current_breakdown = comp["current"].get("result_breakdown") or {}
    previous_breakdown = comp["previous"].get("result_breakdown") or {}
    result_types = sorted(set(current_breakdown) | set(previous_breakdown))
    rows = []
    for result_type in result_types:
        current = current_breakdown.get(result_type, {})
        previous = previous_breakdown.get(result_type, {})
        rows.append(
            {
                "result_type": result_type,
                "previous": previous,
                "current": current,
                "result_change": metric_change(current.get("result_count"), previous.get("result_count")),
                "cost_change": metric_change(current.get("cost_per_result"), previous.get("cost_per_result"), better_lower=True),
            }
        )
    return rows


def make_styles():
    font_candidates = [
        Path("C:/Windows/Fonts/NotoSansSC-VF.ttf"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/Deng.ttf"),
    ]
    for font_path in font_candidates:
        if font_path.exists():
            pdfmetrics.registerFont(TTFont(REPORT_FONT, str(font_path)))
            break
    else:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        globals()["REPORT_FONT"] = "STSong-Light"
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("TitleCN", parent=base["Title"], fontName=REPORT_FONT, fontSize=20, leading=26, alignment=TA_CENTER, spaceAfter=8),
        "subtitle": ParagraphStyle("SubtitleCN", parent=base["Normal"], fontName=REPORT_FONT, fontSize=9, leading=13, alignment=TA_CENTER, textColor=colors.HexColor("#4b5563"), spaceAfter=10),
        "h2": ParagraphStyle("H2CN", parent=base["Heading2"], fontName=REPORT_FONT, fontSize=13, leading=18, spaceBefore=10, spaceAfter=6, textColor=colors.HexColor("#111827")),
        "body": ParagraphStyle("BodyCN", parent=base["BodyText"], fontName=REPORT_FONT, fontSize=9, leading=13),
        "small": ParagraphStyle("SmallCN", parent=base["BodyText"], fontName=REPORT_FONT, fontSize=7.3, leading=9.5),
        "right": ParagraphStyle("RightCN", parent=base["BodyText"], fontName=REPORT_FONT, fontSize=7.3, leading=9.5, alignment=TA_RIGHT),
        "left": ParagraphStyle("LeftCN", parent=base["BodyText"], fontName=REPORT_FONT, fontSize=7.3, leading=9.5, alignment=TA_LEFT),
    }


def table(data, widths, header_rows=1):
    t = Table(data, colWidths=widths, repeatRows=header_rows)
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), REPORT_FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 7.2),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def add_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(REPORT_FONT, 8)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawRightString(doc.pagesize[0] - 12 * mm, 8 * mm, f"第 {doc.page} 页")
    canvas.restoreState()


def write_pdf(path, report):
    styles = make_styles()
    currency = report["account"].get("currency", "")
    doc = SimpleDocTemplate(
        str(path),
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=14 * mm,
    )
    story = []
    account = report["account"]
    story.append(Paragraph(f"{account.get('name', 'Facebook 广告账户')} 广告效果报告", styles["title"]))
    story.append(
        Paragraph(
            f"账户 ID：{account.get('account_id')} | 币种：{currency} | 时区：{account.get('timezone_name')} | 生成时间：{report['generated_at']}",
            styles["subtitle"],
        )
    )

    story.append(Paragraph("总览", styles["h2"]))
    summary_data = [["时间范围", "日期", "花费", "点击", "成效", "单次成效费用", "展示", "覆盖", "CTR", "CPC", "成效组合"]]
    for window_key in ["last_7_days", "last_30_days"]:
        window = report["windows"][window_key]
        s = window["summary"]
        summary_data.append(
            [
                window["label"],
                f"{window['since']} 至 {window['until']}",
                fmt_money(s["spend"], currency),
                fmt_num(s["clicks"]),
                fmt_num(s["result_count"]),
                fmt_money(s["cost_per_result"], currency),
                fmt_num(s["impressions"]),
                fmt_num(s["reach"]),
                f"{s['ctr']:.2f}%",
                fmt_money(s["cpc"], currency),
                format_result_mix(s),
            ]
        )
    story.append(table(summary_data, [20 * mm, 40 * mm, 22 * mm, 16 * mm, 16 * mm, 25 * mm, 22 * mm, 22 * mm, 15 * mm, 20 * mm, 45 * mm]))

    story.append(Paragraph("按成效类型汇总", styles["h2"]))
    type_data = [["时间范围", "成效类型", "花费", "成效", "单次成效费用", "点击", "展示", "CTR", "CPC"]]
    for window_key in ["last_7_days", "last_30_days"]:
        window = report["windows"][window_key]
        breakdown = window["summary"].get("result_breakdown") or {}
        for result_type, item in breakdown.items():
            type_data.append(
                [
                    window["label"],
                    result_type,
                    fmt_money(item["spend"], currency),
                    fmt_num(item["result_count"]),
                    fmt_money(item["cost_per_result"], currency),
                    fmt_num(item["clicks"]),
                    fmt_num(item["impressions"]),
                    f"{item['ctr']:.2f}%",
                    fmt_money(item["cpc"], currency),
                ]
            )
    story.append(table(type_data, [24 * mm, 30 * mm, 25 * mm, 18 * mm, 26 * mm, 19 * mm, 26 * mm, 17 * mm, 22 * mm]))

    story.append(Paragraph("周期对比", styles["h2"]))
    for item in comparison_lines(report):
        story.append(Paragraph(f"• {item}", styles["body"]))

    story.append(Paragraph("主要发现", styles["h2"]))
    for item in build_findings(report):
        story.append(Paragraph(f"• {item}", styles["body"]))
    story.append(Paragraph("建议动作", styles["h2"]))
    for item in build_actions(report):
        story.append(Paragraph(f"• {item}", styles["body"]))

    for window_key in ["last_7_days", "last_30_days"]:
        window = report["windows"][window_key]
        story.append(PageBreak())
        story.append(Paragraph(f"{window['label']}分层数据（{window['since']} 至 {window['until']}）", styles["h2"]))
        for level in LEVELS:
            rows = window["levels"][level][:12]
            story.append(Paragraph(f"{LEVEL_LABELS[level]} Top {len(rows)}", styles["h2"]))
            data = [["名称", "花费", "点击", "成效", "成效类型", "单次成效费用", "展示", "覆盖", "CTR", "CPC", "原始口径"]]
            if not rows:
                data.append(["无数据", "-", "-", "-", "-", "-", "-", "-", "-", "-", "-"])
            for row in rows:
                data.append(
                    [
                        Paragraph(truncate(object_name(row, level), 54), styles["small"]),
                        fmt_money(row["spend"], currency),
                        fmt_num(row["clicks"]),
                        fmt_num(row["result_count"]),
                        row["result_type"],
                        fmt_money(row["cost_per_result"], currency),
                        fmt_num(row["impressions"]),
                        fmt_num(row["reach"]),
                        f"{row['ctr']:.2f}%",
                        fmt_money(row["cpc"], currency),
                        row["result_basis"],
                    ]
                )
            story.append(table(data, [58 * mm, 21 * mm, 15 * mm, 15 * mm, 22 * mm, 24 * mm, 21 * mm, 21 * mm, 14 * mm, 19 * mm, 34 * mm]))
            story.append(Spacer(1, 5 * mm))

    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)


def write_csv(path, rows):
    fields = [
        "window",
        "since",
        "until",
        "level",
        "campaign_id",
        "campaign_name",
        "adset_id",
        "adset_name",
        "ad_id",
        "ad_name",
        "objective",
        "spend",
        "clicks",
        "impressions",
        "reach",
        "ctr",
        "cpc",
        "result_count",
        "result_type",
        "result_basis",
        "cost_per_result",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows([{key: row.get(key, "") for key in fields} for row in rows])


def md_table(headers, rows):
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(item).replace("\n", " ") for item in row) + " |")
    return "\n".join(lines)


def bold(value):
    return f"**{value}**"


def write_markdown(path, report):
    currency = report["account"].get("currency", "")
    account = report["account"]
    spend_limit_remaining = account_spend_limit_remaining(account)
    lines = [
        f"# {account.get('name', 'Facebook 广告账户')} 广告效果报告",
        "",
        f"- 账户 ID：{account.get('account_id')}",
        f"- 币种：{currency}",
        f"- 时区：{account.get('timezone_name')}",
        f"- 生成时间：{report['generated_at']}",
    ]
    if spend_limit_remaining is not None:
        balance_line = f"账户花费限额余额：{currency} {spend_limit_remaining:,.2f}"
        if spend_limit_remaining < 200:
            balance_line = f'<span style="color:red">低余额告警：{balance_line}，低于 {currency} 200.00</span>'
        lines.append(f"- {balance_line}")
    lines.extend(["", "## 总览（流量指标）", ""])

    overview_has_result = all(single_result_type(report["windows"][key]["summary"]) for key in ["last_7_days", "last_30_days"])
    overview_rows = []
    for window_key in ["last_7_days", "last_30_days"]:
        window = report["windows"][window_key]
        s = window["summary"]
        row = [
            window["label"],
            f"{window['since']} 至 {window['until']}",
            fmt_money_value(s["spend"]),
            fmt_num(s["clicks"]),
        ]
        if overview_has_result:
            result = single_result_type(s)
            row.extend([bold(fmt_num(result["result_count"])), bold(fmt_money_value(result["cost_per_result"]))])
        row.extend(
            [
                fmt_num(s["impressions"]),
                fmt_num(s["reach"]),
                f"{s['ctr']:.2f}%",
                fmt_money_value(s["cpc"]),
            ]
        )
        overview_rows.append(row)
    overview_headers = ["时间范围", "日期", f"花费（{currency}）", "点击"]
    if overview_has_result:
        overview_headers.extend(["成效", f"单次费用（{currency}）"])
    overview_headers.extend(["展示", "覆盖", "CTR", f"CPC（{currency}）"])
    lines.append(md_table(overview_headers, overview_rows))

    lines.extend(["", "## 按成效类型汇总", ""])
    type_rows = []
    for window_key in ["last_7_days", "last_30_days"]:
        window = report["windows"][window_key]
        for result_type, item in (window["summary"].get("result_breakdown") or {}).items():
            type_rows.append(
                [
                    window["label"],
                    result_type,
                    fmt_money_value(item["spend"]),
                    bold(fmt_num(item["result_count"])),
                    bold(fmt_money_value(item["cost_per_result"])),
                    fmt_num(item["clicks"]),
                    fmt_num(item["impressions"]),
                    f"{item['ctr']:.2f}%",
                    fmt_money_value(item["cpc"]),
                ]
            )
    lines.append(md_table(["时间范围", "成效类型", f"花费（{currency}）", "成效", f"单次费用（{currency}）", "点击", "展示", "CTR", f"CPC（{currency}）"], type_rows))

    lines.extend(["", "## 周期对比（按成效类型）", ""])
    for window_key in ["last_7_days", "last_30_days"]:
        comp = (report.get("comparisons") or {}).get(window_key)
        if not comp:
            continue
        lines.append(f"### {comp['label']}")
        lines.append("")
        if comp.get("skipped"):
            lines.extend([comp.get("reason", "上个周期数据不足，跳过对比。"), ""])
            continue
        compare_rows = []
        for row in result_type_comparison_rows(report, window_key):
            previous = row["previous"]
            current = row["current"]
            compare_rows.append(
                [
                    row["result_type"],
                    fmt_money_value(previous.get("spend")),
                    bold(fmt_num(previous.get("result_count"))),
                    bold(fmt_money_value(previous.get("cost_per_result"))),
                    fmt_money_value(current.get("spend")),
                    bold(fmt_num(current.get("result_count"))),
                    bold(fmt_money_value(current.get("cost_per_result"))),
                    row["result_change"],
                    row["cost_change"],
                ]
            )
        lines.append(
            md_table(
                ["成效类型", f"上期花费（{currency}）", "上期成效", f"上期单次（{currency}）", f"本期花费（{currency}）", "本期成效", f"本期单次（{currency}）", "成效变化", "费用变化"],
                compare_rows,
            )
        )
        lines.append("")

    lines.extend(["## 主要发现", ""])
    for item in build_findings(report):
        lines.append(f"- {item}")
    lines.extend(["", "## 建议动作", ""])
    for item in build_actions(report):
        lines.append(f"- {item}")

    for window_key in ["last_7_days", "last_30_days"]:
        window = report["windows"][window_key]
        lines.extend(["", f"## {window['label']}分层数据（{window['since']} 至 {window['until']}）", ""])
        for level in LEVELS:
            rows = window["levels"][level][:20]
            detail_rows = []
            for row in rows:
                name = object_name(row, level)
                if is_low_ctr_ad(row):
                    name = red(name)
                detail_rows.append(
                    [
                        LEVEL_LABELS[level],
                        name,
                        fmt_money_value(row["spend"]),
                        fmt_num(row["clicks"]),
                        bold(fmt_num(row["result_count"])),
                        row["result_type"],
                        bold(fmt_money_value(row["cost_per_result"])),
                        fmt_num(row["impressions"]),
                        fmt_num(row["reach"]),
                        f"{row['ctr']:.2f}%",
                        fmt_money_value(row["cpc"]),
                    ]
                )
            lines.append(f"### {LEVEL_LABELS[level]}")
            lines.append("")
            lines.append(
                md_table(
                    ["层级", "名称", f"花费（{currency}）", "点击", "成效", "成效类型", f"单次费用（{currency}）", "展示", "覆盖", "CTR", f"CPC（{currency}）"],
                    detail_rows,
                )
            )
            lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def safe_name(value):
    text = str(value or "account").strip()
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text)[:80]


def main():
    parser = argparse.ArgumentParser(description="Generate Facebook Ads account Markdown reports.")
    parser.add_argument("--account-id", action="append", dest="account_ids", help="Ad account ID, can be used multiple times.")
    parser.add_argument("--accounts", help="Comma-separated ad account IDs.")
    parser.add_argument("--out-dir", default="fb_output")
    args = parser.parse_args()

    account_ids = []
    for value in args.account_ids or []:
        account_ids.extend([item.strip() for item in value.split(",") if item.strip()])
    if args.accounts:
        account_ids.extend([item.strip() for item in args.accounts.split(",") if item.strip()])
    if not account_ids:
        raise RuntimeError("请至少提供一个 --account-id。")

    run_date = datetime.now().strftime("%Y-%m-%d")
    outputs = []
    for raw_id in account_ids:
        account_id = normalize_account_id(raw_id)
        report, rows = collect_account(account_id)
        account_name = safe_name(report["account"].get("name"))
        target = Path(args.out_dir) / account_id / run_date
        target.mkdir(parents=True, exist_ok=True)
        json_path = target / f"{account_name}_{account_id}_report.json"
        csv_path = target / f"{account_name}_{account_id}_report.csv"
        md_path = target / f"{account_name}_{account_id}_report.md"
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        write_csv(csv_path, rows)
        write_markdown(md_path, report)
        outputs.append({"account_id": account_id, "markdown": str(md_path), "json": str(json_path), "csv": str(csv_path)})

    print(json.dumps({"ok": True, "outputs": outputs}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
