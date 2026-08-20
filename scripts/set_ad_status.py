import argparse
import json

from facebook_business.adobjects.ad import Ad

from common import init_api, write_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ad-id", required=True)
    parser.add_argument("--status", required=True, choices=["ACTIVE", "PAUSED"])
    parser.add_argument("--out", default="fb_output/ad_status_update.json")
    args = parser.parse_args()

    init_api()
    ad = Ad(args.ad_id)
    update = ad.api_update(params={"status": args.status})
    verify = Ad(args.ad_id).api_get(
        fields=["id", "name", "status", "effective_status", "configured_status", "adset_id", "campaign_id"]
    ).export_all_data()
    result = {"update": update.export_all_data() if hasattr(update, "export_all_data") else update, "verify": verify}
    write_json(args.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
