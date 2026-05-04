"""
Fetches all playlists from the YouTube channel and saves to playlists.json.

Usage:
    python fetch_playlists.py
"""

import json
import subprocess
import sys
from pathlib import Path

CHANNEL_URL = "https://www.youtube.com/@sappabharathibhagavatarini/playlists"
OUTPUT_FILE = Path(__file__).parent / "playlists.json"


def fetch_playlists() -> list[dict]:
    print("Fetching playlists from YouTube channel...")

    result = subprocess.run(
        [
            "yt-dlp",
            "--flat-playlist",
            "--print", "%(title)s|||%(url)s",
            CHANNEL_URL,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("ERROR: yt-dlp failed.")
        print(result.stderr)
        sys.exit(1)

    playlists = []
    for line in result.stdout.strip().splitlines():
        if "|||" not in line:
            continue
        title, url = line.split("|||", 1)
        title = title.strip()
        url = url.strip()
        if not title or not url:
            continue
        playlists.append({
            "title": title,
            "link": url,
        })

    return playlists


def main():
    playlists = fetch_playlists()

    if not playlists:
        print("No playlists found.")
        sys.exit(1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(playlists, f, ensure_ascii=False, indent=2)

    print(f"Done! {len(playlists)} playlists saved to playlists.json")
    for i, p in enumerate(playlists, 1):
        print(f"  {i}. {p['title']}")
        print(f"     {p['link']}")


if __name__ == "__main__":
    main()
