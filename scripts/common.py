import json
import os
import random
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
from facebook_business.api import FacebookAdsApi


API_VERSION = os.environ.get("FB_API_VERSION", "v25.0")
GRAPH = f"https://graph.facebook.com/{API_VERSION}"

# access_token 位于查询串中，任何异常信息都不得包含完整 URL，只输出方法 + 路径。
RETRYABLE_CODES = {4, 17, 500, 503, 504}
MAX_ATTEMPTS = 4

# 受众类型 -> targeting_spec 字段映射（audience_reach / audience_report 共用）
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


def require_token():
    token = os.environ.get("FB_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("FB_ACCESS_TOKEN is not set")
    return token


def normalize_account_id(account_id):
    value = str(account_id).strip()
    return value if value.startswith("act_") else f"act_{value}"


def proxy_config():
    proxy = os.environ.get("FB_PROXY")
    return {"http": proxy, "https": proxy} if proxy else None


def init_api():
    token = require_token()
    FacebookAdsApi.init(
        app_id=os.environ.get("META_APP_ID"),
        app_secret=os.environ.get("META_APP_SECRET"),
        access_token=token,
        api_version=API_VERSION,
    )


def _safe_url(url):
    """异常信息只保留路径，不打印带 access_token 的查询串。"""
    return urlparse(url).path


def _error_code(body):
    if isinstance(body, dict):
        return body.get("error", {}).get("code")
    return None


def _retry_delay(attempt, response=None):
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(float(retry_after), 60)
            except (TypeError, ValueError):
                pass
    return min(2 ** attempt + random.uniform(0, 1), 30)


def _request(method, url, *, retry_policy="safe", **kwargs):
    """统一请求入口。

    safe（GET）：网络错误、限流（4/17）与 5xx 都重试。
    conservative（POST）：只重试明确的限流错误，避免超时后重复写入。
    """
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = requests.request(method, url, timeout=90, **kwargs)
            try:
                body = response.json()
            except ValueError:
                body = {}
            if response.status_code < 400:
                return response, body
            code = _error_code(body)
            if retry_policy == "safe":
                retryable = code in RETRYABLE_CODES or response.status_code in {500, 503, 504}
            else:
                retryable = code in {4, 17}
            if retryable and attempt < MAX_ATTEMPTS - 1:
                time.sleep(_retry_delay(attempt, response))
                continue
            raise RuntimeError(json.dumps(body, ensure_ascii=False, indent=2))
        except requests.exceptions.RequestException as exc:
            # 超时/连接类异常信息可能包含完整 URL（含 token），只报类型与路径。
            if retry_policy == "safe" and attempt < MAX_ATTEMPTS - 1:
                time.sleep(_retry_delay(attempt))
                continue
            raise RuntimeError(f"{method} {_safe_url(url)} failed: {type(exc).__name__}") from None
    raise RuntimeError(f"{method} {_safe_url(url)} failed")


def graph_get(path, params=None):
    token = require_token()
    payload = dict(params or {})
    payload["access_token"] = token
    url = f"{GRAPH}/{path.lstrip('/')}"
    _, body = _request("GET", url, params=payload, retry_policy="safe")
    return body


def graph_post(path, data=None):
    token = require_token()
    payload = dict(data or {})
    payload["access_token"] = token
    url = f"{GRAPH}/{path.lstrip('/')}"
    _, body = _request("POST", url, data=payload, retry_policy="conservative")
    return body


def paged_get(path, params=None):
    payload = graph_get(path, params)
    while True:
        for row in payload.get("data", []):
            yield row
        next_url = payload.get("paging", {}).get("next")
        if not next_url:
            break
        query = parse_qs(urlparse(next_url).query)
        after = (query.get("after") or [None])[0]
        if after:
            # 用 after 游标重请求同一路径，避免把带 token 的 next_url 直接当 URL 使用。
            next_params = dict(params or {})
            next_params["after"] = after
            payload = graph_get(path, next_params)
        else:
            _, body = _request("GET", next_url, retry_policy="safe")
            payload = body


def date_windows(end=None):
    """以广告账户时区的“昨天”为窗口结束日；不包含当前未结束的当天。"""
    end = end or (date.today() - timedelta(days=1))
    start_of_this_week = end - timedelta(days=end.weekday())
    last_week_end = start_of_this_week - timedelta(days=1)
    last_week_start = last_week_end - timedelta(days=6)
    return {
        "last_30_days": (end - timedelta(days=29), end),
        "last_7_days": (end - timedelta(days=6), end),
        "last_full_week": (last_week_start, last_week_end),
    }


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
