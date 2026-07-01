# TikTok → Facebook Page Auto-Poster (100% Free)

Watches a TikTok account for new videos and automatically posts them to your
Facebook Page, using only free tools:

- **yt-dlp** — lists and downloads TikTok videos (no API key)
- **GitHub Actions** — free scheduler that runs the check every 30 min
- **Facebook Graph API** — free video upload endpoint

---

## Step 1 — Create a GitHub repo

1. Go to github.com → New repository → make it **public** (public repos get
   unlimited free Actions minutes; private repos get 2,000 free min/month,
   which is still plenty at a 30-min interval).
2. Upload all the files in this folder, preserving the structure:
   ```
   .github/workflows/watch_tiktok.yml
   scripts/check_and_post.py
   requirements.txt
   ```

## Step 2 — Get a Facebook Page Access Token (free)

1. Go to https://developers.facebook.com/ → log in → **My Apps** → **Create App**
   → choose type **"Other" / "Business"** → name it anything.
2. In the app dashboard, add the **Facebook Login** or just use
   **Graph API Explorer** (top nav under Tools): https://developers.facebook.com/tools/explorer/
3. In Graph API Explorer:
   - Select your app.
   - Click "Get Token" → "Get Page Access Token".
   - Grant permissions: `pages_manage_posts`, `pages_read_engagement`,
     `pages_show_list`.
   - Select your Facebook Page.
4. This gives you a **short-lived** token. Exchange it for a **long-lived**
   one (lasts ~60 days, renewable) using this URL in your browser
   (replace the placeholders):
   ```
   https://graph.facebook.com/v19.0/oauth/access_token?
     grant_type=fb_exchange_token&
     client_id=YOUR_APP_ID&
     client_secret=YOUR_APP_SECRET&
     fb_exchange_token=YOUR_SHORT_LIVED_TOKEN
   ```
5. Note your **Page ID** (found under your Page's "About" section or via
   `https://graph.facebook.com/me/accounts?access_token=YOUR_TOKEN`).

> Since you're only posting to your own Page (not the public), this works
> in the app's **Development Mode** — no App Review needed. Just make sure
> your Facebook account is listed as an Admin/Developer on the app.

## Step 3 — Add secrets to GitHub

In your repo: **Settings → Secrets and variables → Actions → New repository secret**

Add three secrets:
| Name | Value |
|---|---|
| `TIKTOK_USERNAME` | the TikTok handle, no `@` |
| `FB_PAGE_ID` | your numeric Page ID |
| `FB_PAGE_ACCESS_TOKEN` | the long-lived token from Step 2 |

## Step 4 — Run it

- Go to the **Actions** tab in your repo → select "TikTok to Facebook" →
  **Run workflow** to test it manually first.
- The first run only records the current newest video as a baseline (so you
  don't get a flood of old videos posted at once) — check the run logs to
  confirm it worked.
- After that, it checks every 30 minutes automatically and posts anything
  new.

## Notes & limits

- **Token expiry**: Page tokens from this method last ~60 days. Re-run Step
  2 periodically, or look into Meta's "System User" tokens (also free) for
  a token that doesn't expire, once you're comfortable with the setup.
- **TikTok scraping is unofficial**: yt-dlp works by parsing TikTok's site,
  which can break if TikTok changes its layout. If the workflow starts
  failing, check for a `yt-dlp` update (`pip install -U yt-dlp`).
- **Rights**: only auto-repost videos you own or have permission to share.
- **Cost**: $0 — GitHub Actions free tier and Meta's Graph API are both
  free for this volume of usage.
