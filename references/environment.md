# Environment Variables

Use these variables when running scripts.

| Variable | Required | Purpose |
|---|---:|---|
| `FB_ACCESS_TOKEN` | yes | Meta access token with required permissions |
| `META_APP_ID` | no | Meta app ID for SDK initialization |
| `META_APP_SECRET` | no | Meta app secret for SDK initialization |
| `FB_PROXY` | no | HTTP/SOCKS proxy, for example `socks5h://127.0.0.1:10808` |

Required permissions depend on task:

- Reporting: `ads_read`
- Create/update ads: `ads_management`
- Lead forms: `leads_retrieval`
- Page-backed ad creatives: `pages_show_list`, `pages_manage_ads`
- Business asset discovery: `business_management`

Long-term automation should use a Business Manager System User token where possible.

## Getting an Access Token

1. Go to https://developers.facebook.com/apps and create an App (Business type).
2. Open https://developers.facebook.com/tools/explorer and select the App.
3. Add permissions `ads_management` and `ads_read`.
4. Click *Generate Access Token*, log in if asked, then copy the token.
5. Set it as `FB_ACCESS_TOKEN` in the environment before running scripts.

Notes:

- Graph API Explorer tokens expire after about 2 hours. For longer sessions, extend the token in the Access Token Debugger, or use a Business Manager System User token for automation.
- Audience research endpoints (`targetingsearch`, `reachestimate`) require `ads_management`.
- Never write tokens to files or commit them to version control.
