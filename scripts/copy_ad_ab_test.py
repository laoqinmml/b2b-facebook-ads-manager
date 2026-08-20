import argparse
import copy
import json

from common import graph_get, graph_post, normalize_account_id, write_json


DEFAULT_BODIES = [
    "Source custom shades & blinds directly from us. Ask for factory pricing, custom sizes, samples, and lead times.",
    "Need reliable supply for projects or resale? Get custom window-covering options built for dealers, contractors, and wholesalers.",
    "Cut out the middleman. Request direct pricing on custom shades and blinds for your next project or wholesale order.",
]

DEFAULT_TITLES = [
    "Wholesale Shades, Factory Direct",
    "Custom Blinds for Dealers",
    "Get Factory Pricing",
]

DEFAULT_DESCRIPTION = "Request pricing, samples, and lead times for custom shades and blinds."


def strip_label_ids(value):
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key == "id" and "name" in value:
                continue
            out[key] = strip_label_ids(item)
        return out
    if isinstance(value, list):
        return [strip_label_ids(item) for item in value]
    return value


def load_list(path, fallback):
    if not path:
        return fallback
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return payload
    raise RuntimeError(f"{path} must contain a JSON list")


def replace_text_assets(asset_feed_spec, bodies, titles, description):
    spec = strip_label_ids(copy.deepcopy(asset_feed_spec))
    for index, body in enumerate(spec.get("bodies", [])):
        body["text"] = bodies[index % len(bodies)]
    for index, title in enumerate(spec.get("titles", [])):
        title["text"] = titles[index % len(titles)]
    if description:
        spec["descriptions"] = [{"text": description}]
    return spec


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-ad-id", required=True)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--name-suffix", default="AB Copy Test")
    parser.add_argument("--bodies-json")
    parser.add_argument("--titles-json")
    parser.add_argument("--description", default=DEFAULT_DESCRIPTION)
    parser.add_argument("--out", default="fb_output/created_ab_test_ad.json")
    args = parser.parse_args()

    source = graph_get(
        args.source_ad_id,
        {
            "fields": (
                "id,name,status,effective_status,adset_id,campaign_id,"
                "creative{id,name,object_story_spec,asset_feed_spec}"
            )
        },
    )
    creative = source["creative"]
    if "asset_feed_spec" not in creative:
        raise RuntimeError("Source creative does not contain asset_feed_spec. Manual adaptation is required.")

    bodies = load_list(args.bodies_json, DEFAULT_BODIES)
    titles = load_list(args.titles_json, DEFAULT_TITLES)
    new_spec = replace_text_assets(creative["asset_feed_spec"], bodies, titles, args.description)

    creative_name = f"{source['name']} - {args.name_suffix} Creative"
    new_creative = graph_post(
        f"{normalize_account_id(args.account_id)}/adcreatives",
        {
            "name": creative_name,
            "object_story_spec": json.dumps(creative["object_story_spec"], ensure_ascii=False),
            "asset_feed_spec": json.dumps(new_spec, ensure_ascii=False),
        },
    )

    new_ad_name = f"{source['name']} - {args.name_suffix}"
    new_ad = graph_post(
        f"{normalize_account_id(args.account_id)}/ads",
        {
            "name": new_ad_name,
            "adset_id": source["adset_id"],
            "creative": json.dumps({"creative_id": new_creative["id"]}),
            "status": "PAUSED",
        },
    )
    verify = graph_get(
        new_ad["id"],
        {"fields": "id,name,status,effective_status,configured_status,adset_id,campaign_id,creative{id,name}"},
    )
    result = {
        "source_ad_id": source["id"],
        "source_ad_name": source["name"],
        "new_creative_id": new_creative["id"],
        "new_ad_id": new_ad["id"],
        "new_ad_name": new_ad_name,
        "verify": verify,
        "status": "PAUSED",
    }
    write_json(args.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
