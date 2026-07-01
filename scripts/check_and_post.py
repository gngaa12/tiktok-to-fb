#!/usr/bin/env python3
"""
TikTok -> Facebook Page auto-poster
Free stack: yt-dlp (listing + downloading) + Facebook Graph API (uploading)

Env vars required (set as GitHub Actions secrets):
  TIKTOK_USERNAME       e.g. "someuser"  (no @)
  FB_PAGE_ID            numeric Facebook Page ID
  FB_PAGE_ACCESS_TOKEN  long-lived Page access token

State file: state/last_video_id.txt (committed back by the workflow)
"""

import json
import os
import subprocess
import sys
import tempfile

import requests

TIKTOK_USERNAME = os.environ["TIKTOK_USERNAME"]
FB_PAGE_ID = os.environ["FB_PAGE_ID"]
FB_PAGE_TOKEN = os.environ["FB_PAGE_ACCESS_TOKEN"]
STATE_FILE = "state/last_video_id.txt"
GRAPH_VERSION = "v19.0"


def get_video_list():
    """Return list of dicts [{id, url, title}] newest-first for the TikTok user."""
    url = f"https://www.tiktok.com/@{TIKTOK_USERNAME}"
    cmd = ["yt-dlp", "--flat-playlist", "-J", url]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    entries = data.get("entries", [])
    videos = [
        {
            "id": e["id"],
            "url": f"https://www.tiktok.com/@{TIKTOK_USERNAME}/video/{e['id']}",
            "title": e.get("title") or "",
        }
        for e in entries
    ]
    return videos  # yt-dlp returns newest-first for TikTok user pages


def load_last_id():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return f.read().strip() or None
    return None


def save_last_id(video_id):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        f.write(video_id)


def download_video(video_url, out_dir):
    out_path = os.path.join(out_dir, "video.mp4")
    cmd = ["yt-dlp", "-f", "mp4", "-o", out_path, video_url]
    subprocess.run(cmd, check=True)
    return out_path


def upload_to_facebook(video_path, caption):
    url = f"https://graph-video.facebook.com/{GRAPH_VERSION}/{FB_PAGE_ID}/videos"
    with open(video_path, "rb") as f:
        resp = requests.post(
            url,
            data={"access_token": FB_PAGE_TOKEN, "description": caption},
            files={"source": f},
            timeout=600,
        )
    if resp.status_code != 200:
        print("FACEBOOK ERROR DETAILS:", resp.text)
    resp.raise_for_status()
    print("Facebook response:", resp.json())
def main():
    videos = get_video_list()
    if not videos:
        print("No videos found (account may be private or blocked). Exiting.")
        return

    last_id = load_last_id()

    if last_id is None:
        # First run: don't mass-post the whole backlog, just mark newest as seen.
        save_last_id(videos[0]["id"])
        print(f"First run. Marked {videos[0]['id']} as the baseline, no post made.")
        return

    # Collect videos newer than last_id, in chronological order (oldest new video first)
    new_videos = []
    for v in videos:
        if v["id"] == last_id:
            break
        new_videos.append(v)
    new_videos.reverse()

    if not new_videos:
        print("No new videos.")
        return

    for v in new_videos:
        print(f"New video found: {v['id']} - {v['title']}")
        with tempfile.TemporaryDirectory() as tmp:
            try:
                path = download_video(v["url"], tmp)
                upload_to_facebook(path, v["title"])
                save_last_id(v["id"])
            except Exception as e:
                print(f"Failed on {v['id']}: {e}", file=sys.stderr)
                # Stop here so we retry this video next run instead of skipping it
                break


if __name__ == "__main__":
    main()
