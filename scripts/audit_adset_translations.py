"""Read Meta's creative translation fields for every ad in an ad set."""

import argparse
import json
import os
import sys
from urllib.parse import urlsplit

import requests


FEATURES = ("text_translation", "image_text_translation", "translate_voiceover")
FIELDS = "id,name,configured_status,effective_status,creative{id,degrees_of_freedom_spec}"


def audit(session, url):
    params = {"fields": FIELDS, "limit": 100}
    seen = set()
    while True:
        response = session.get(url, params=params, timeout=(8, 25))
        payload = response.json()
        if response.status_code >= 400 or "error" in payload:
            error = payload.get("error", {})
            raise RuntimeError(
                f"Meta HTTP {response.status_code}, code {error.get('code')}, "
                f"subcode {error.get('error_subcode')}"
            )
        for ad in payload["data"]:
            creative = ad.pop("creative", None) or {}
            freedom = creative.get("degrees_of_freedom_spec") or {}
            features = freedom.get("creative_features_spec") or {}
            yield {
                **ad,
                "creative_id": creative.get("id"),
                "translation": {name: features.get(name) for name in FEATURES},
            }
        paging = payload.get("paging", {})
        if not paging.get("next"):
            return
        after = paging.get("cursors", {}).get("after")
        if not after or after in seen:
            raise RuntimeError("Meta pagination did not return a new cursor")
        seen.add(after)
        params["after"] = after


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adset-id", required=True)
    args = parser.parse_args()
    if not args.adset_id.isascii() or not args.adset_id.isdigit():
        parser.error("--adset-id must contain only ASCII digits")
    token = os.environ.get("FB_ACCESS_TOKEN")
    if not token:
        parser.error("FB_ACCESS_TOKEN is not set")
    version = os.environ.get("FB_API_VERSION", "v25.0")
    if not version.startswith("v") or not all(
        part.isascii() and part.isdigit() for part in version[1:].split(".")
    ):
        parser.error("invalid FB_API_VERSION")
    url = f"https://graph.facebook.com/{version}/{args.adset_id}/ads"
    with requests.Session() as session:
        session.headers["Authorization"] = f"Bearer {token}"
        proxy = os.environ.get("FB_PROXY")
        if proxy:
            session.proxies.update(http=proxy, https=proxy)
        try:
            ads = list(audit(session, url))
        except (requests.RequestException, ValueError, KeyError) as exc:
            parser.exit(1, f"GET {urlsplit(url).path} failed: {type(exc).__name__}\n")
        except RuntimeError as exc:
            parser.exit(1, f"{exc}\n")
    print(json.dumps({"adset_id": args.adset_id, "ads": ads}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    sys.exit(main())
