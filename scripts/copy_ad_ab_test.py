"""复制广告做 A/B 文案测试。

用法示例：
    python copy_ad_ab_test.py --source-ad-id <AD_ID> --account-id <ACCOUNT_ID> \
        --bodies-json fb_output/bodies.json --titles-json fb_output/titles.json

A/B 文案必须由用户通过 --bodies-json / --titles-json 提供，脚本不内置默认文案。
"""

import argparse
import copy
import json

from common import graph_get, graph_post, normalize_account_id, write_json


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


def load_list(path):
    if not path:
        raise RuntimeError("缺少文案 JSON 文件：--bodies-json / --titles-json 为必填")
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
    parser = argparse.ArgumentParser(description="复制广告做 A/B 文案测试（文案必须由用户提供）")
    parser.add_argument("--source-ad-id", required=True)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--name-suffix", default="AB Copy Test")
    parser.add_argument("--bodies-json", required=True, help="primary text 列表 JSON 文件（必填）")
    parser.add_argument("--titles-json", required=True, help="headline 列表 JSON 文件（必填）")
    parser.add_argument("--description", help="description 文本；缺省时保留原 description")
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

    bodies = load_list(args.bodies_json)
    titles = load_list(args.titles_json)
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
