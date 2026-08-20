---
name: facebook-ads-manager
description: Analyze and manage Meta/Facebook Ads accounts using the official facebook_business SDK and Meta Marketing API. Use when the user provides or references a Facebook/Meta access token, ad account ID, campaign/ad set/ad ID, lead form ID, or asks Codex to generate Facebook ads reports, diagnose campaign performance, create A/B test ads, optimize ad copy, activate or pause ads, retrieve lead ads data, find target audiences / interests / hidden interests, do B2B or B2C audience research, estimate audience reach by country or region, or manage multiple Meta ad accounts.
---

# Facebook Ads Manager

Use this skill for Meta/Facebook Ads reporting and controlled account operations after the user has already obtained an access token.

Prefer the official `facebook_business` Python SDK. Fall back to direct Graph API requests only when the SDK does not expose a needed edge cleanly.

## Safety Rules

- Never print, quote, or store access tokens.
- Read secrets from environment variables or runtime input:
  - `FB_ACCESS_TOKEN`
  - `META_APP_ID` optional
  - `META_APP_SECRET` optional
  - `FB_PROXY` optional, for example `socks5h://127.0.0.1:10808`
- Create new ads as `PAUSED` by default.
- Require explicit user approval before activating, pausing, deleting, changing budgets, or changing live targeting.
- After any write, read the object back and report ID, name, configured status, and effective status.
- If an operation fails due to app mode, permissions, review, token expiry, or policy review, explain the exact Meta error and stop before retrying write operations.

## Setup

Install dependencies in the workspace:

```bash
pip install facebook_business requests
```

Set token before running scripts:

```bash
set FB_ACCESS_TOKEN=...
set FB_PROXY=socks5h://127.0.0.1:10808
```

Use account IDs without `act_` in user-facing commands. Scripts normalize both forms.

## Standard Report Workflow

Use `scripts/report.py` when asked to analyze an account, generate a weekly report, compare recent performance, or diagnose issues.

1. Read account metadata.
2. Pull insights for:
   - last 30 days
   - last 7 days
   - last full week
3. Break down by:
   - campaign
   - ad set
   - ad
4. Include:
   - spend
   - clicks
   - impressions
   - CTR
   - CPC
   - conversions
   - cost per conversion
5. Identify:
   - high spend with zero conversions
   - CPA spikes
   - weak CTR
   - one-object spend concentration
   - missing A/B tests
6. Produce a short execution plan with concrete next actions.

Example:

```bash
python scripts/report.py --account-id 3149616161865068 --out-dir fb_output
```

## Audience Research Workflow

Use the `scripts/audience_*.py` scripts when the user asks to find target audiences, interests, or "hidden interests", do B2B/B2C audience research, or estimate how many people an audience covers in specific countries/regions.

Follow the steps in order. This workflow is read-only (targetingsearch / reachestimate); any ad creation afterward follows the existing create-as-PAUSED rules.

1. Token and account. Verify `FB_ACCESS_TOKEN` is set (see `references/environment.md` for how to obtain one if missing). Validate it and list accessible accounts with:

   ```bash
   python -c "import json,sys; sys.path.insert(0,'scripts'); from common import graph_get; [print(a['id'], a.get('name','')) for a in graph_get('me/adaccounts', {'limit':100}).get('data',[])]"
   ```

   Ask the user which account to use if several are returned.

2. Ask the user, in this order:
   - target country / region (multi-select; map to ISO codes)
   - product / industry (free text, e.g. "包材定制/包装袋")
   - B2B, B2C, or both

3. Build the keyword list. Use the built-in library for known industries, then let the user add custom keywords:

   ```bash
   python scripts/audience_keywords.py --industry "包装袋/包材" --mode b2b
   python scripts/audience_keywords.py --industry "日化" --mode b2c --extra "custom term"
   ```

   Unknown industries: ask the user for 3-10 representative keywords (category terms, brands, use-case phrases).

4. Search audiences in two tracks with `scripts/audience_search.py`. Do not filter by size by default (`--min-size 0 --max-size 0`); output everything and let the user decide.

   - B2C / interests track:

     ```bash
     python scripts/audience_search.py --account 1495761958760356 --keywords "packaging,food industry,cosmetics" --class adinterests --out-suffix b2c
     ```

   - B2B / identity track (job titles, behaviors, industries):

     ```bash
     python scripts/audience_search.py --account 1495761958760356 --keywords "purchasing manager,founder,small business owners" --class adworkjobtitles --type work_positions --out-suffix b2b_titles
     python scripts/audience_search.py --account 1495761958760356 --keywords "small business owners,business page admins" --class adtargetingcategories --keep-all --out-suffix b2b_people
     ```

   The script dedupes across keywords, tags each row with its source keyword, and saves CSV/JSON to `fb_output/`.

5. Present the sorted list to the user and ask them to pick audience IDs (write picks to a CSV with columns `id,name,type`). Auto-recommend only if the user asks for it; default is "show the list and let the user decide".

6. Estimate real reach in the selected countries with `scripts/audience_reach.py`:

   ```bash
   python scripts/audience_reach.py --account 1495761958760356 --file fb_output/audience_picks.csv --countries ID,PH,VN,TH,MY,SG,MM,KH,LA,BN,TL --out sea_reach
   ```

7. Deliver the report with `scripts/audience_report.py` (Markdown summary + ready-to-paste `targeting_spec` JSON examples):

   ```bash
   python scripts/audience_report.py --reach-file fb_output/sea_reach.csv --countries "ID,PH,VN,TH,MY,SG,MM,KH,LA,BN,TL" --out audience_report
   ```

Experience notes:

- "Southeast Asia" exists in Meta as an *interest*, not a geo location. Target countries by ISO code list.
- Job-title targeting (`work_positions`) is very thin in emerging markets (SEA often returns ~1,000 or below). For B2B in those markets, prefer behaviors (Small business owners, Business page admins) and broad interests.
- `audience_size` from targetingsearch is a global estimate without geo; use `reachestimate` (step 6) for country-level reach.
- `targetingsearch` and `reachestimate` require `ads_management` on the token.

## A/B Test Ad Workflow

Use `scripts/copy_ad_ab_test.py` when the user asks to duplicate an existing ad and test new copy.

1. Read the source ad and creative.
2. Preserve campaign, ad set, creative media, CTA, lead form, placements, and links.
3. Replace text assets only:
   - body / primary text
   - title / headline
   - description
4. Create a new creative.
5. Create a new ad as `PAUSED`.
6. Read back and report:
   - source ad ID
   - new creative ID
   - new ad ID
   - configured status
   - effective status
7. Activate only after the user explicitly asks.

Example:

```bash
python scripts/copy_ad_ab_test.py --source-ad-id 120232398906870392 --account-id 3149616161865068 --out fb_output/created_ab_test_ad.json
```

## Status Changes

Use `scripts/set_ad_status.py` for explicit requests such as "turn this ad on" or "pause this ad".

Allowed statuses:

- `ACTIVE`
- `PAUSED`

Example:

```bash
python scripts/set_ad_status.py --ad-id 120250996069480392 --status ACTIVE
```

## Copywriting Defaults

For B2B manufacturing or wholesale accounts, optimize copy toward:

- factory-direct pricing
- dealers, wholesalers, contractors, distributors
- custom sizes
- OEM/ODM or private label if true
- fabric/options count if known
- quote/sample/lead-time intent

Avoid unsupported claims such as guaranteed lowest price, impossible delivery promises, or claims not present in the user's business context.

## Output Style

Keep reports concise and operational:

- Summary table first.
- Findings by severity.
- Action steps last.
- Mention exact dates.
- Mention when conversion basis is `lead`, `purchase`, or another event.
