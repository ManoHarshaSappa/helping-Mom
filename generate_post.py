import json
import sys
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel

from config import YOUTUBE_CHANNEL_URL

# ── Load video catalog once ───────────────────────────────────────────────────

_BASE = Path(__file__).parent

with open(_BASE / "videos.json", encoding="utf-8") as _f:
    VIDEOS: list[dict] = json.load(_f)


# ── Pydantic schema ───────────────────────────────────────────────────────────

class BestVideo(BaseModel):
    selected_video_index: int  # single best matching video index


# ── System prompt ─────────────────────────────────────────────────────────────

def _build_system_prompt() -> str:
    catalog = json.dumps(
        [{"index": i, "title": v["title"], "tags": v["tags"]} for i, v in enumerate(VIDEOS)],
        ensure_ascii=False, indent=2,
    )
    return f"""You are helping a Telugu Harikatha artist pick the single best related video from her YouTube channel to share in a Facebook post.

Given the event description, pick the ONE most relevant video from the catalog below.
Return only selected_video_index (0-based integer).

VIDEO CATALOG
{catalog}"""


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
        response_format=BestVideo,
    )

    rec: BestVideo | None = response.choices[0].message.parsed
    if rec is None:
        raise RuntimeError("Could not pick a video.")

    idx = rec.selected_video_index
    if not (0 <= idx < len(VIDEOS)):
        idx = 0
    video = VIDEOS[idx]

    lines: list[str] = [
        input_text.strip(),
        "",
        "మీకు నచ్చే మరో మంచి వీడియో చూడండి 👇",
        "",
        f"▶ {video['title']}",
        video["link"],
        "",
        "ఈ వీడియో నచ్చితే Like 👍, Share 🔁 మరియు Comment ✍️ చేయండి.",
        "",
        "మరిన్ని హరికథలు & భక్తి వీడియోలు కావాలంటే మా YouTube Channel చూడండి 👇",
        YOUTUBE_CHANNEL_URL,
        "",
        "Subscribe చేయడం మర్చిపోకండి 🔔",
        "",
        "🙏 ధన్యవాదాలు 🙏",
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
