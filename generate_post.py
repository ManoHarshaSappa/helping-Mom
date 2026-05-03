#!/usr/bin/env python3
"""
Harikatha Promotion: AI Content Assistant
Generates structured Telugu social media posts for Harikatha performances.

Usage:
    python generate_post.py "Telugu performance description..."
    echo "Telugu text" | python generate_post.py
"""

import json
import sys
from pathlib import Path
from typing import List, Literal

from openai import OpenAI
from pydantic import BaseModel

from config import YOUTUBE_CHANNEL_URL

# ── Load video collection (once at import time) ──────────────────────────────

VIDEOS_FILE = Path(__file__).parent / "videos.json"
with open(VIDEOS_FILE, encoding="utf-8") as _f:
    VIDEOS: list[dict] = json.load(_f)


# ── Pydantic schema for Claude's structured output ───────────────────────────

class PostRecommendation(BaseModel):
    match_strength: Literal["strong", "medium", "weak"]
    selected_video_indices: List[int]
    recommendation_text: str  # 2–3 sentences in Telugu


# ── System prompt (static — cached across requests) ──────────────────────────

def _build_system_prompt() -> str:
    catalog = json.dumps(
        [
            {"index": i, "title": v["title"], "tags": v["tags"]}
            for i, v in enumerate(VIDEOS)
        ],
        ensure_ascii=False,
        indent=2,
    )
    return f"""You are a Telugu devotional content writer helping a Harikatha artist create social media posts.

TASK
Given a Telugu event description, you must:
1. Identify the topic/theme (e.g., Rama, Sita, Hanuman, Krishna, Shiva, Ganesha, temple, festival).
2. Select the most relevant videos from the catalog below.
3. Determine match strength and number of videos to recommend:
   - strong match → 1 video
   - medium match → 2 videos
   - weak match   → 3 videos
4. Write a short, natural Telugu recommendation paragraph that:
   - Suggests the selected videos as similar or related devotional content
   - Encourages users to watch
   - Uses words like "ఇలాంటి", "సంబంధిత", "మీకు నచ్చవచ్చు"
   - Is devotional, emotional, and simple in tone

STRICT RULES
- Keep the original user content EXACTLY as-is — do NOT modify it.
- NEVER imply the recommended videos are from the same event as the description.
- Do NOT use aggressive marketing language or exaggerated claims.
- selected_video_indices must be valid 0-based indices from the catalog below.

VIDEO CATALOG
{catalog}"""


SYSTEM_PROMPT = _build_system_prompt()


# ── Core generation function ──────────────────────────────────────────────────

def generate_post(input_text: str) -> str:
    """Generate a complete Telugu social media post from a performance description.

    Args:
        input_text: A short Telugu text describing a recent Harikatha performance.

    Returns:
        A formatted multi-section social media post as a string.
    """
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
        raise RuntimeError("OpenAI could not generate a recommendation.")

    # ── Assemble the final post ───────────────────────────────────────────────
    lines: list[str] = []

    # Section 1 — original input text, preserved exactly
    lines.append(input_text.strip())
    lines.append("")

    # Section 2 — Telugu recommendation with video links
    lines.append(rec.recommendation_text.strip())
    lines.append("")

    for idx in rec.selected_video_indices:
        if 0 <= idx < len(VIDEOS):
            video = VIDEOS[idx]
            lines.append(f"▶ {video['title']}")
            lines.append(video["link"])
            lines.append("")

    # Section 3 — channel link and call to action
    lines.append(f"🎙️ Youtube Channel : {YOUTUBE_CHANNEL_URL}")
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
