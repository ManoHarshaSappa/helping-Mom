import json
from pathlib import Path
from typing import List

from openai import OpenAI
from pydantic import BaseModel

from config import YOUTUBE_CHANNEL_URL

_BASE = Path(__file__).parent

with open(_BASE / "videos.json", encoding="utf-8") as _f:
    VIDEOS: list[dict] = json.load(_f)

with open(_BASE / "playlists.json", encoding="utf-8") as _f:
    PLAYLISTS: list[dict] = json.load(_f)

# Popular videos with known view counts
POPULAR_VIDEOS = [
    {"link": "https://youtu.be/MH8xAZG_oM8", "views": "3,00,000+"},
    {"link": "https://youtu.be/WpKCS_321IA", "views": "2,40,000+"},
    {"link": "https://youtu.be/Bwf105eLluM", "views": "40,000+"},
    {"link": "https://youtu.be/QgzV19E8nlQ", "views": "35,000+"},
]

POPULAR_LINKS = {p["link"] for p in POPULAR_VIDEOS}
POPULAR_MAP   = {p["link"]: p["views"] for p in POPULAR_VIDEOS}

# Fixed footer added to every YouTube description
FOOTER = """---------------------------------------------------------------------------------------------------
#sappabharathi #HarikathaBharathi

Name: Sappa Bharathi Bhagavatarini
Location: Eluru resident
Profession: Harikatha artist

Those who want to conduct my Harikatha program can contact me at the following numbers:
Phone: 98483 78407 / 97041 79407
---------------------------------------------------------------------------------------------------
Sri Valli Kalyanam Harikatha (All Parts)
https://youtube.com/playlist?list=PL2T1fjpT1UqfKhbr5zT3vkxI_gw9_LZMZ
---------------------------------------------------------------------------------------------------
Sri Veera Brahmendra Swami Harikatha Sudha (All Parts)
https://youtube.com/playlist?list=PL2T1fjpT1UqeCNqfAJ20mpaVaqhFzLqlF
---------------------------------------------------------------------------------------------------
If you like the videos, please Like 👍, Share 🔁 and Subscribe 🔔 to my channel:
{channel_url}
---------------------------------------------------------------------------------------------------
Join our Telegram group:
https://t.me/sappabharathibhagavatariniyt
---------------------------------------------------------------------------------------------------
For more information:
https://sappabharathibhagavatarini.blogspot.com/2021/08/sappa-bharathi-bhagavatarini-photos.html
---------------------------------------------------------------------------------------------------
Contact (Social Media):
Facebook  : https://www.facebook.com/people/Sappa-Bharathi/100008436812038/
Instagram : https://www.instagram.com/sappa_bharathi/
Telegram  : https://t.me/sappabharathibhagavatariniyt
Blog      : https://sappabharathibhagavatarini.blogspot.com/2021/08/sappa-bharathi-bhagavatarini-photos.html
---------------------------------------------------------------------------------------------------""".format(channel_url=YOUTUBE_CHANNEL_URL)


# ── Pydantic schema ───────────────────────────────────────────────────────────

class YoutubeDesc(BaseModel):
    telugu_description: str    # 4-6 sentences in Telugu about the video
    english_description: str   # 4-6 sentences in English about the video
    hashtags: str              # 10-15 relevant hashtags
    selected_video_indices: List[int]   # 2-3 related video indices
    selected_playlist_index: int        # -1 if no playlist


# ── System prompt ─────────────────────────────────────────────────────────────

def _build_system_prompt() -> str:
    video_catalog = json.dumps(
        [{"index": i, "title": v["title"], "tags": v["tags"]} for i, v in enumerate(VIDEOS)],
        ensure_ascii=False, indent=2,
    )
    playlist_catalog = json.dumps(
        [{"index": i, "title": p["title"]} for i, p in enumerate(PLAYLISTS)],
        ensure_ascii=False, indent=2,
    )
    return f"""You are writing a YouTube video description for Telugu Harikatha artist Sappa Bharathi Bhagavatarini.

Given a video title and optional context, generate:

1. telugu_description — 4 to 6 sentences in Telugu describing what this video contains, why it is special, and what viewers will experience. Warm, devotional, emotional tone.

2. english_description — Same content in English (4-6 sentences). Natural, inviting tone.

3. hashtags — 12-15 relevant hashtags (English + Telugu transliterated). Include #SappaBharathi #Harikatha #TeluguDevotional and topic-specific tags.

4. selected_video_indices — Pick 2 or 3 most related videos from the catalog (0-based indices).

5. selected_playlist_index — Pick 1 most related playlist index (0-based), or -1 if none matches.

VIDEO CATALOG
{video_catalog}

PLAYLIST CATALOG
{playlist_catalog}"""


SYSTEM_PROMPT = _build_system_prompt()


# ── Core function ─────────────────────────────────────────────────────────────

def generate_youtube_description(title: str, context: str = "") -> str:
    client = OpenAI()

    user_input = f"Video Title: {title}"
    if context.strip():
        user_input += f"\nAdditional context: {context.strip()}"

    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        response_format=YoutubeDesc,
    )

    rec: YoutubeDesc | None = response.choices[0].message.parsed
    if rec is None:
        raise RuntimeError("Could not generate description.")

    videos   = [VIDEOS[i] for i in rec.selected_video_indices if 0 <= i < len(VIDEOS)]
    playlist = PLAYLISTS[rec.selected_playlist_index] if 0 <= rec.selected_playlist_index < len(PLAYLISTS) else None

    lines: list[str] = []

    # Title
    lines.append(title.strip())
    lines.append("")

    # Telugu description
    lines.append(rec.telugu_description.strip())
    lines.append("")

    # English description
    lines.append(rec.english_description.strip())
    lines.append("")

    # Related playlist
    if playlist:
        lines.append("📋 Watch Complete Series:")
        lines.append(f"▶ {playlist['title']}")
        lines.append(playlist["link"])
        lines.append("")

    # Related videos
    if videos:
        lines.append("🎬 Watch More Related Videos:")
        for v in videos:
            views = POPULAR_MAP.get(v["link"], "")
            view_tag = f" — 🔥 {views} views" if views else ""
            lines.append(f"▶ {v['title']}{view_tag}")
            lines.append(v["link"])
        lines.append("")

    # Hashtags
    lines.append(rec.hashtags.strip())
    lines.append("")

    # Fixed footer
    lines.append(FOOTER)

    return "\n".join(lines)
