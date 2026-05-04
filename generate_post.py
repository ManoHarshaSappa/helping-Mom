import json
import sys
from pathlib import Path
from typing import List, Literal

from openai import OpenAI
from pydantic import BaseModel

from config import YOUTUBE_CHANNEL_URL

# ── Load catalogs once at import time ────────────────────────────────────────

_BASE = Path(__file__).parent

with open(_BASE / "videos.json", encoding="utf-8") as _f:
    VIDEOS: list[dict] = json.load(_f)

with open(_BASE / "playlists.json", encoding="utf-8") as _f:
    PLAYLISTS: list[dict] = json.load(_f)


# ── Pydantic schema ───────────────────────────────────────────────────────────

class PostRecommendation(BaseModel):
    match_strength: Literal["strong", "medium", "weak"]
    recommendation_type: Literal["videos", "playlist", "both"]
    selected_video_indices: List[int]     # indices into VIDEOS list
    selected_playlist_indices: List[int]  # indices into PLAYLISTS list
    recommendation_text: str              # 2–3 sentences in Telugu


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
    return f"""You are a Telugu devotional content writer helping a Harikatha artist promote her YouTube channel on Facebook.

TASK
Given a Telugu event description, generate a smart recommendation for related content from her channel.

STEP 1 — Identify the theme
Extract the main topic: Rama, Sita, Hanuman, Krishna, Shiva, Ganesha, Venkateswara, Parvati, Valli, devotional songs, keertanas, harikatha story, etc.

STEP 2 — Choose recommendation_type using these rules:
- "playlist"  → event is about a full story or series (e.g., Ramayana, Valli Kalyanam, Mahabharatham, Veerabrahmendra, Srinivasa Kalyanam). A playlist gives the viewer the whole series.
- "videos"    → event is about a specific song, keertana, or short performance. Pick 1–3 individual videos.
- "both"      → event has both a story element AND songs. Recommend 1 playlist + 1 video.

STEP 3 — Choose how many items based on match_strength:
- "strong" → 1 item total (1 playlist OR 1 video)
- "medium" → 2 items total (2 videos OR 1 playlist + 1 video)
- "weak"   → 3 items total (3 videos OR 1 playlist + 2 videos)

STEP 4 — Write recommendation_text (2–3 sentences in Telugu) that:
- Naturally connects the event to the recommended content
- Uses warm devotional language: "ఇలాంటి", "సంబంధిత", "మీకు నచ్చవచ్చు", "తప్పకుండా చూడండి"
- Is emotional, simple, and encouraging

STRICT RULES
- Keep the original user content EXACTLY as-is — never modify it.
- NEVER imply the recommended videos/playlists are from the same event.
- selected_video_indices must be valid 0-based indices from the VIDEO CATALOG below.
- selected_playlist_indices must be valid 0-based indices from the PLAYLIST CATALOG below.
- If recommendation_type is "videos", selected_playlist_indices must be [].
- If recommendation_type is "playlist", selected_video_indices must be [].

VIDEO CATALOG
{video_catalog}

PLAYLIST CATALOG
{playlist_catalog}"""


SYSTEM_PROMPT = _build_system_prompt()


# ── Core generation function ──────────────────────────────────────────────────

def generate_post(input_text: str) -> str:
    client = OpenAI()

    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": input_text.strip()},
        ],
        response_format=PostRecommendation,
    )

    rec: PostRecommendation | None = response.choices[0].message.parsed
    if rec is None:
        raise RuntimeError("Could not generate a recommendation.")

    lines: list[str] = []

    # Section 1 — original performance description (untouched)
    lines.append(input_text.strip())
    lines.append("")

    # Section 2 — Telugu recommendation text
    lines.append(rec.recommendation_text.strip())
    lines.append("")

    # Section 3 — playlists (if any)
    for idx in rec.selected_playlist_indices:
        if 0 <= idx < len(PLAYLISTS):
            playlist = PLAYLISTS[idx]
            lines.append(f"▶ Playlist: {playlist['title']}")
            lines.append(playlist["link"])
            lines.append("")

    # Section 4 — individual videos (if any)
    for idx in rec.selected_video_indices:
        if 0 <= idx < len(VIDEOS):
            video = VIDEOS[idx]
            lines.append(f"▶ {video['title']}")
            lines.append(video["link"])
            lines.append("")

    # Section 5 — channel footer
    lines.append(f"🎙️ మా Youtube Channel : {YOUTUBE_CHANNEL_URL}")
    lines.append("")
    lines.append("ఈ వీడియో మీకు నచ్చితే తప్పకుండా Like 👍, Share 🔁 మరియు Subscribe 🔔 చేయండి.")
    lines.append("మరిన్ని భక్తి పరమైన హరికథలు, కీర్తనలు మరియు పురాణ కథలు వినాలంటే మా ఛానల్ Sappa Bharathi Bhagavatarini ను సబ్‌స్క్రైబ్ చేసుకోండి. 🙏")
    lines.append("")
    lines.append("🙏 ధన్యవాదాలు 🙏")

    return "\n".join(lines)


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        if sys.stdin.isatty():
            print("Telugu performance description నమోదు చేయండి (Ctrl+D to finish):\n")
        text = sys.stdin.read()

    text = text.strip()
    if not text:
        print("Error: Input text is empty.", file=sys.stderr)
        sys.exit(1)

    print("\n⏳ Generating post...\n", file=sys.stderr)
    try:
        post = generate_post(text)
        print("\n" + "═" * 50)
        print(post)
        print("═" * 50)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
