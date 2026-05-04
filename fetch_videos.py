"""
Run this once to fetch all videos from the YouTube channel
and save them to videos.json.

Usage:
    python fetch_videos.py
"""

import json
import subprocess
import sys
from pathlib import Path

CHANNEL_URL = "https://www.youtube.com/@sappabharathibhagavatarini"
OUTPUT_FILE = Path(__file__).parent / "videos.json"

DEVOTIONAL_TAGS = {
    "rama": ["rama", "ramayana", "sita", "ram"],
    "sita": ["sita", "janaki", "vaidehi"],
    "hanuman": ["hanuman", "anjaneya", "maruti", "vayuputra"],
    "krishna": ["krishna", "govinda", "madhava", "gopala", "radha", "gokula"],
    "shiva": ["shiva", "siva", "shankara", "mahashiva", "shivaradhana", "mahadev", "hara", "om hara", "nikhilashrita"],
    "ganesha": ["ganesha", "ganesh", "ganapathi", "vinayaka", "vakratunda"],
    "vishnu": ["vishnu", "venkateswara", "balaji", "tirupati", "narayana"],
    "devi": ["devi", "durga", "lakshmi", "saraswati", "parvati", "ambika", "amma"],
    "harikatha": ["harikatha", "harikathalu", "katha"],
    "keertana": ["keertana", "keertanalu", "song", "bhajan", "kirtan"],
    "bhakti": ["bhakti", "devotional", "bhagavatam", "puranas"],
    "sappa bharathi": ["sappa bharathi", "bharathi bhagavatarini"],
}


def auto_tags(title: str) -> list[str]:
    title_lower = title.lower()
    tags = []
    for tag, keywords in DEVOTIONAL_TAGS.items():
        if any(kw in title_lower for kw in keywords):
            tags.append(tag)
    if not tags:
        tags = ["devotional", "harikatha", "bhakti"]
    return tags


def fetch_videos() -> list[dict]:
    print("Fetching videos from YouTube channel...")
    print(f"Channel: {CHANNEL_URL}\n")

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

    videos = []
    for line in result.stdout.strip().splitlines():
        if "|||" not in line:
            continue
        title, url = line.split("|||", 1)
        title = title.strip()
        url = url.strip()
        if not title or not url:
            continue
        # Convert full URL to short youtu.be format if needed
        if "watch?v=" in url:
            video_id = url.split("watch?v=")[-1].split("&")[0]
            url = f"https://youtu.be/{video_id}"
        videos.append({
            "title": title,
            "link": url,
            "tags": auto_tags(title),
        })

    return videos


def main():
    # Check yt-dlp is installed
    check = subprocess.run(["yt-dlp", "--version"], capture_output=True)
    if check.returncode != 0:
        print("yt-dlp is not installed. Run: pip install yt-dlp")
        sys.exit(1)

    videos = fetch_videos()

    if not videos:
        print("No videos found. Check the channel URL.")
        sys.exit(1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)

    print(f"Done! {len(videos)} videos saved to videos.json")


if __name__ == "__main__":
    main()
