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

# Top portion of footer: Harikatha playlists block (inserted before one_line / search_terms)
FOOTER_TOP = """---------------------------------------------------------------------------------------------------
HARIKATHA PLAYLISTS (All Parts):

▶ Sri Valli Kalyanam Harikatha – Complete Series
https://youtube.com/playlist?list=PL2T1fjpT1UqfKhbr5zT3vkxI_gw9_LZMZ

▶ Sri Veera Brahmendra Swamy Harikatha Sudha – Complete Series
https://youtube.com/playlist?list=PL2T1fjpT1UqeCNqfAJ20mpaVaqhFzLqlF

▶ Lord Shri Rama – Complete Stories Collection
https://www.youtube.com/playlist?list=PL2T1fjpT1UqceBhHKXX8fZ6sT29T9hOQr
---------------------------------------------------------------------------------------------------"""

# Bottom portion of footer: everything after Harikatha playlists
FOOTER_BOTTOM = """BEST VIEWED VIDEOS (Most Popular):

▶ శ్రీమద్ విరాట్ పోతులూరి వీరబ్రహ్మేంద్ర స్వామి చరిత్ర – సంపూర్ణ హరికథ (3,00,000+ views)
https://youtu.be/MH8xAZG_oM8

▶ శ్రీరామ జననం – సంపూర్ణ హరికథ (2,40,000+ views)
https://youtu.be/WpKCS_321IA

▶ శ్రీ వల్లీ కళ్యాణం హరికథ (40,000+ views)
https://youtu.be/Bwf105eLluM
---------------------------------------------------------------------------------------------------
AWARDS & RECOGNITION:
డాక్టరేట్, నంది అవార్డు, సిల్వర్ క్రౌన్ అవార్డు మరియు హంస అవార్డు సహా అనేక ప్రతిష్ఠాత్మక పురస్కారాలు అందుకున్న సప్పా భారతి భాగవతారిణి గారి అవార్డుల సేకరణ చూడండి.

▶ Awards Playlist – Moments of Honor
https://www.youtube.com/playlist?list=PL2T1fjpT1Uqeay9A_lvIgHZ_QTJ4o0bVm
---------------------------------------------------------------------------------------------------
Subscribe to our YouTube Channel:
మరిన్ని భక్తి హరికథలు, కీర్తనలు మరియు పురాణ కథల కోసం మా ఛానల్‌ను సబ్‌స్క్రైబ్ చేయండి.
{channel_url}
---------------------------------------------------------------------------------------------------
WhatsApp Group:
https://chat.whatsapp.com/KitCWyU1JwjIKPjZOBWe7g
---------------------------------------------------------------------------------------------------
Telegram Group – Sappa Bharathi Bhagavatarini (join for regular video updates):
https://t.me/sappabharathibhagavatariniyt
---------------------------------------------------------------------------------------------------
More Information / Blog:
https://sappabharathibhagavatarini.blogspot.com/2021/08/sappa-bharathi-bhagavatarini-photos.html
---------------------------------------------------------------------------------------------------
Official Portfolio — DR. Sappa Bharathi Bhagavatarini:
https://manoharshasappa.github.io/DR.SappaBharathiBhagavatarini/
---------------------------------------------------------------------------------------------------
Follow us on Social Media:
Facebook  : https://www.facebook.com/people/Sappa-Bharathi/100008436812038/
Instagram : https://www.instagram.com/sappa_bharathi/
Telegram  : https://t.me/sappabharathibhagavatariniyt
---------------------------------------------------------------------------------------------------
If you like the videos, do like, share and subscribe to my channel Sappa Bharathi Bhagavatarini.
ధన్యవాదాలు 🙏
---------------------------------------------------------------------------------------------------""".format(channel_url=YOUTUBE_CHANNEL_URL)


# ── Pydantic schema ───────────────────────────────────────────────────────────

class YoutubeDesc(BaseModel):
    one_line: str              # ONE short line about the video (Telugu or English, max 1 sentence)
    top_hashtags: str          # EXACTLY 4 hashtags for the very top (space separated)
    remaining_hashtags: str    # remaining 16 hashtags (space separated)
    search_terms: str          # relevant search keywords people type on YouTube, pipe-separated
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

1. one_line — Just ONE short sentence (Telugu or English) about what the video is. Keep it simple.

2. top_hashtags — EXACTLY 4 hashtags only. These go at the very top. Make them the most important/broad ones. Example: "#SappaBharathi #Harikatha #TeluguDevotional #Bhakti"

3. remaining_hashtags — Exactly 16 more hashtags (space separated). Topic-specific, deity name, song name, event type etc. Total with top_hashtags = 20.

4. search_terms — 15-20 keywords/phrases that people actually search on YouTube. Pipe-separated (|). Mix Telugu transliterated and English. Include deity name, song name, artist name, general devotional terms.

5. selected_video_indices — Pick 2 or 3 most related videos (0-based indices).

6. selected_playlist_index — Pick 1 most related playlist index (0-based), or -1 if none matches.

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

    # 1. Title
    lines.append(title.strip())
    lines.append("")

    # 2. Top 4 hashtags — shown as clickable blue links on YouTube
    lines.append(rec.top_hashtags.strip())
    lines.append("")

    # 3. Artist header — all on one line
    lines.append("DR. Sappa Bharathi Bhagavatarini (Top Grade Harikatha Artist) Eluru, Andhra Pradesh Contact: 98483 78407 / 97041 79407 (Please contact only for Harikatha programs) హరికథ కార్యక్రమాల కోసం మాత్రమే సంప్రదించండి")
    lines.append("")
    lines.append("")

    # 4. Remaining 16 hashtags
    lines.append(rec.remaining_hashtags.strip())
    lines.append("")

    lines.append("---------------------------------------------------------------------------------------------------")

    # 5. AI-picked playlist
    if playlist:
        lines.append("📋 Watch Complete Series:")
        lines.append(f"▶ {playlist['title']}")
        lines.append(playlist["link"])
        lines.append("")

    # 6. AI-picked related videos
    if videos:
        lines.append("🎬 Watch More Related Videos:")
        for v in videos:
            views = POPULAR_MAP.get(v["link"], "")
            view_tag = f" — {views} views" if views else ""
            lines.append(f"▶ {v['title']}{view_tag}")
            lines.append(v["link"])
        lines.append("")

    # 7. Harikatha playlists block
    lines.append(FOOTER_TOP)
    lines.append("")
    lines.append("")

    # 8. One short line + search terms (one per line)
    lines.append(rec.one_line.strip())
    for term in [t.strip() for t in rec.search_terms.split("|") if t.strip()]:
        lines.append(term)
    lines.append("")
    lines.append("")
    lines.append("")
    lines.append("")

    # 9. Rest of footer
    lines.append(FOOTER_BOTTOM)

    return "\n".join(lines)
