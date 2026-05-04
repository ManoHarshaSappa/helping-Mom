import json
import sys
from pathlib import Path
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel

from config import YOUTUBE_CHANNEL_URL

_BASE = Path(__file__).parent

with open(_BASE / "videos.json", encoding="utf-8") as _f:
    VIDEOS: list[dict] = json.load(_f)

with open(_BASE / "playlists.json", encoding="utf-8") as _f:
    PLAYLISTS: list[dict] = json.load(_f)

with open(_BASE / "examples.json", encoding="utf-8") as _f:
    EXAMPLES: list[dict] = json.load(_f)


# ── Pydantic schema ───────────────────────────────────────────────────────────

class BestPick(BaseModel):
    pick_type: Literal["video", "playlist"]
    selected_index: int  # index into videos or playlists depending on pick_type


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
    return f"""You are helping a Telugu Harikatha artist pick the best content to recommend in a Facebook post.

RULES:
- If the event is about a full story or series (Ramayana, Veerabrahmendra, Mahabharatham, Valli Kalyanam, Srinivasa Kalyanam, Parvati Kalyanam etc.) → pick_type = "playlist"
- If the event is about a specific song, keertana, or short performance → pick_type = "video"

Return pick_type and selected_index (0-based) from the correct catalog.

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

    if rec.pick_type == "playlist":
        idx = rec.selected_index if 0 <= rec.selected_index < len(PLAYLISTS) else 0
        item = PLAYLISTS[idx]
        title_line = f"ఇక్కడ {item['title']} playlist పెట్టడం జరిగింది."
        link_line  = f"Playlist లింక్: {item['link']}"
        like_line  = "ఈ playlist మీకు నచ్చితే లైక్ చేయండి. మీకు నచ్చిన వాళ్లతో షేర్ చేయండి. మీ అభిప్రాయాన్ని కామెంట్‌లో తెలియజేయండి."
    else:
        idx = rec.selected_index if 0 <= rec.selected_index < len(VIDEOS) else 0
        item = VIDEOS[idx]
        title_line = f"ఇక్కడ {item['title']} వీడియోను పెట్టడం జరిగింది."
        link_line  = f"వీడియో లింక్: {item['link']}"
        like_line  = "ఈ వీడియో మీకు నచ్చితే లైక్ చేయండి. మీకు నచ్చిన వాళ్లతో షేర్ చేయండి. మీ అభిప్రాయాన్ని కామెంట్‌లో తెలియజేయండి."

    lines: list[str] = [
        input_text.strip(),
        "",
        "అందరికీ ధన్యవాదాలు.",
        title_line,
        link_line,
        "",
        like_line,
        "",
        "ఇలాంటి మరిన్ని అందమైన ఆధ్యాత్మిక వీడియోల కోసం నా YouTube ఛానల్ Sappa Bharathi Bhagavatarini ను సబ్‌స్క్రైబ్ చేయండి.",
        YOUTUBE_CHANNEL_URL,
        "",
        "ధన్యవాదాలు 🙏",
    ]

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
