#!/usr/bin/env python3
"""
TikTok (multiple accounts) -> Facebook Page auto-poster
Free stack: yt-dlp (listing + downloading) + Facebook Graph API (uploading)

Env vars required (set as GitHub Actions secrets):
  TIKTOK_USERNAMES      comma-separated list, e.g. "nikita,friend2,friend3"
  FB_PAGE_ID            numeric Facebook Page ID
  FB_PAGE_ACCESS_TOKEN  long-lived Page access token

State: one file per account, state/last_video_id_<username>.txt
(committed back by the workflow)
"""

import json
import os
import subprocess
import sys
import tempfile
import time

import requests

TIKTOK_USERNAMES = [
    u.strip() for u in os.environ["TIKTOK_USERNAMES"].split(",") if u.strip()
]
FB_PAGE_ID = os.environ["FB_PAGE_ID"]
FB_PAGE_TOKEN = os.environ["FB_PAGE_ACCESS_TOKEN"]
GRAPH_VERSION = "v19.0"
UPLOAD_DELAY_SECONDS = 30  # gap between uploads so they don't all land at once


def state_file_for(username):
    return f"state/last_video_id_{username}.txt"


def get_video_list(username):
    url = f"https://www.tiktok.com/@{username}"
    cmd = ["yt-dlp", "--flat-playlist", "-J", url]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    entries = data.get("entries", [])
    videos = [
        {
            "id": e["id"],
            "url": f"https://www.tiktok.com/@{username}/video/{e['id']}",
            "title": e.get("title") or "",
        }
        for e in entries
    ]
    return videos  # newest-first


def load_last_id(username):
    path = state_file_for(username)
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip() or None
    return None


def save_last_id(username, video_id):
    path = state_file_for(username)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(video_id)


def download_video(video_url, out_dir):
    out_path = os.path.join(out_dir, "video.mp4")
    cmd = ["yt-dlp", "-f", "mp4", "-o", out_path, video_url]
    subprocess.run(cmd, check=True)
    return out_path


def upload_to_facebook(video_path, caption):
    url = f"https://graph-video.facebook.com/{GRAPH_VERSION}/{FB_PAGE_ID}/videos"
    params = {"access_token": FB_PAGE_TOKEN}
    with open(video_path, "rb") as f:
        resp = requests.post(
            url,
            params=params,
            data={"description": caption},
            files={"source": f},
            timeout=600,
        )
    if resp.status_code != 200:
        print("FACEBOOK ERROR DETAILS:", resp.text)
    resp.raise_for_status()
    print("Facebook response:", resp.json())


def process_account(username):
    print(f"\n=== Checking @{username} ===")
    try:
        videos = get_video_list(username)
    except subprocess.CalledProcessError as e:
        print(f"Could not fetch videos for @{username}: {e}", file=sys.stderr)
        return

    if not videos:
        print(f"No videos found for @{username} (private or blocked?). Skipping.")
        return

    last_id = load_last_id(username)

    if last_id is None:
        save_last_id(username, videos[0]["id"])
        print(f"First run for @{username}. Baseline set to {videos[0]['id']}.")
        return

    new_videos = []
    for v in videos:
        if v["id"] == last_id:
            break
        new_videos.append(v)
    new_videos.reverse()  # oldest new video first

    if not new_videos:
        print(f"No new videos for @{username}.")
        return

    for v in new_videos:
        print(f"New video from @{username}: {v['id']} - {v['title']}")
        with tempfile.TemporaryDirectory() as tmp:
            try:
                path = download_video(v["url"], tmp)
                upload_to_facebook(path, f"{v['title']} (via @{username})")
                save_last_id(username, v["id"])
                time.sleep(UPLOAD_DELAY_SECONDS)
            except Exception as e:
                print(f"Failed on {v['id']} (@{username}): {e}", file=sys.stderr)
                # stop this account's loop so the same video is retried next run
                break


def main():
    for username in TIKTOK_USERNAMES:
        process_account(username)


if __name__ == "__main__":
    main()
