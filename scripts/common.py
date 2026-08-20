import json
import os
from datetime import date, timedelta
from pathlib import Path

import requests
from facebook_business.api import FacebookAdsApi


API_VERSION = "v25.0"
GRAPH = f"https://graph.facebook.com/{API_VERSION}"


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


def graph_get(path, params=None):
    token = require_token()
    payload = dict(params or {})
    payload["access_token"] = token
    response = requests.get(
        f"{GRAPH}/{path.lstrip('/')}",
        params=payload,
        proxies=proxy_config(),
        timeout=90,
    )
    body = response.json()
    if response.status_code >= 400:
        raise RuntimeError(json.dumps(body, ensure_ascii=False, indent=2))
    return body


def graph_post(path, data=None):
    token = require_token()
    payload = dict(data or {})
    payload["access_token"] = token
    response = requests.post(
        f"{GRAPH}/{path.lstrip('/')}",
        data=payload,
        proxies=proxy_config(),
        timeout=90,
    )
    body = response.json()
    if response.status_code >= 400:
        raise RuntimeError(json.dumps(body, ensure_ascii=False, indent=2))
    return body


def paged_get(path, params=None):
    payload = graph_get(path, params)
    while True:
        for row in payload.get("data", []):
            yield row
        next_url = payload.get("paging", {}).get("next")
        if not next_url:
            break
        response = requests.get(next_url, proxies=proxy_config(), timeout=90)
        body = response.json()
        if response.status_code >= 400:
            raise RuntimeError(json.dumps(body, ensure_ascii=False, indent=2))
        payload = body


def date_windows(today=None):
    today = today or date.today()
    start_of_this_week = today - timedelta(days=today.weekday())
    last_week_end = start_of_this_week - timedelta(days=1)
    last_week_start = last_week_end - timedelta(days=6)
    return {
        "last_30_days": (today - timedelta(days=29), today),
        "last_7_days": (today - timedelta(days=6), today),
        "last_full_week": (last_week_start, last_week_end),
    }


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
