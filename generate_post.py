import json
import sys
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


# ── Pydantic schema ───────────────────────────────────────────────────────────

class BestPick(BaseModel):
    selected_video_indices: List[int]  # 0–4 videos; empty list if none
    selected_playlist_index: int       # -1 if no playlist


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
    return f"""You are helping a Telugu Harikatha artist recommend related YouTube content for a Facebook post.

Given the event description, decide freely what to recommend based on how much related content exists:

HOW TO DECIDE:
- Strong single match → 1 video (selected_video_indices = [x], selected_playlist_index = -1)
- Multiple related songs/keertanas → 2, 3, or 4 videos
- Full story/series (Ramayana, Veerabrahmendra, Mahabharatham, Valli Kalyanam, Srinivasa Kalyanam, Parvati Kalyanam, Girija Kalyanam etc.) → 1 playlist (selected_video_indices = [], selected_playlist_index = x)
- Full story AND related songs → playlist + 1 or 2 videos
- No strong match → pick 3–4 loosely related videos

RULES:
- selected_video_indices: list of 0–4 valid video indices (0-based). Empty list [] if no videos.
- selected_playlist_index: valid playlist index (0-based), or -1 if no playlist.
- Never recommend more than 4 videos total.
- Never recommend more than 1 playlist.

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
        response_format=BestPick,
    )

    rec: BestPick | None = response.choices[0].message.parsed
    if rec is None:
        raise RuntimeError("Could not pick content.")

    has_playlist = rec.selected_playlist_index != -1 and 0 <= rec.selected_playlist_index < len(PLAYLISTS)
    videos = [VIDEOS[i] for i in rec.selected_video_indices if 0 <= i < len(VIDEOS)]
    playlist = PLAYLISTS[rec.selected_playlist_index] if has_playlist else None

    lines: list[str] = [input_text.strip(), "", "అందరికీ ధన్యవాదాలు.", ""]

    # Playlist section
    if playlist:
        lines.append(f"ఇక్కడ {playlist['title']} playlist పెట్టడం జరిగింది.")
        lines.append(f"Playlist లింక్: {playlist['link']}")
        lines.append("")

    # Videos section
    if videos:
        if len(videos) == 1:
            lines.append(f"ఇక్కడ {videos[0]['title']} వీడియోను పెట్టడం జరిగింది.")
            lines.append(f"వీడియో లింక్: {videos[0]['link']}")
        else:
            lines.append("ఇక్కడ కొన్ని సంబంధిత వీడియోలు పెట్టడం జరిగింది.")
            lines.append("")
            for v in videos:
                lines.append(f"▶ {v['title']}")
                lines.append(v['link'])
                lines.append("")

    lines.append("")

    # Like/share/comment line — changes based on what was recommended
    if playlist and videos:
        lines.append("ఈ వీడియోలు మరియు playlist మీకు నచ్చితే లైక్ చేయండి. మీకు నచ్చిన వాళ్లతో షేర్ చేయండి. మీ అభిప్రాయాన్ని కామెంట్‌లో తెలియజేయండి.")
    elif playlist:
        lines.append("ఈ playlist మీకు నచ్చితే లైక్ చేయండి. మీకు నచ్చిన వాళ్లతో షేర్ చేయండి. మీ అభిప్రాయాన్ని కామెంట్‌లో తెలియజేయండి.")
    elif len(videos) > 1:
        lines.append("ఈ వీడియోలు మీకు నచ్చితే లైక్ చేయండి. మీకు నచ్చిన వాళ్లతో షేర్ చేయండి. మీ అభిప్రాయాన్ని కామెంట్‌లో తెలియజేయండి.")
    else:
        lines.append("ఈ వీడియో మీకు నచ్చితే లైక్ చేయండి. మీకు నచ్చిన వాళ్లతో షేర్ చేయండి. మీ అభిప్రాయాన్ని కామెంట్‌లో తెలియజేయండి.")

    lines.append("")
    lines.append("ఇలాంటి మరిన్ని అందమైన ఆధ్యాత్మిక వీడియోల కోసం నా YouTube ఛానల్ Sappa Bharathi Bhagavatarini ను సబ్‌స్క్రైబ్ చేయండి.")
    lines.append(YOUTUBE_CHANNEL_URL)
    lines.append("")
    lines.append("ధన్యవాదాలు 🙏")

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
