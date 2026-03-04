"""
AI News Digest Agent
====================
A multi-agent Strands pipeline that fetches, ranks, and writes
a daily AI news digest from Hacker News, TLDR AI, and The Batch.

Sources:  Hacker News AI stories + TLDR AI RSS + The Batch RSS
Output:   digests/digest-YYYY-MM-DD.md
Cost:     ~$0.001-0.003 per run using Nova Micro + Nova Lite

Usage:
    python agent.py

Setup:
    pip install strands-agents strands-agents-tools
    Configure AWS credentials (for Bedrock) OR set ANTHROPIC_API_KEY
    for Claude direct API usage.
"""

import json
import sys
import os
from datetime import datetime

# Load .env file if present (optional — falls back to system env vars)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Model config — swap these to change cost/quality tradeoff
# ---------------------------------------------------------------------------
# Option A: Amazon Bedrock (default) — requires AWS credentials
RANKER_MODEL_ID  = "amazon.nova-micro-v1:0"   # cheapest, fast — good for ranking
WRITER_MODEL_ID  = "amazon.nova-lite-v1:0"    # slightly smarter — good for writing

# Option B: Anthropic direct API — set ANTHROPIC_API_KEY env var and uncomment below
# RANKER_MODEL_ID = "claude-haiku-4-5-20251001"
# WRITER_MODEL_ID = "claude-haiku-4-5-20251001"
# ---------------------------------------------------------------------------

from strands import Agent
from strands.models import BedrockModel

# Add tools directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tools"))
from rss_fetcher import fetch_rss_stories
from hn_fetcher import fetch_hn_ai_stories
from yt_fetcher import fetch_youtube_stories
from save_digest import save_digest
from article_fetcher import fetch_article_text


def load_prompt(name: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "prompts", f"{name}.txt")
    with open(path, encoding="utf-8") as f:
        return f.read()


def build_ranker_agent() -> Agent:
    """Cheap model — just needs to classify and rank JSON."""
    return Agent(
        model=BedrockModel(model_id=RANKER_MODEL_ID),
        system_prompt=load_prompt("ranker"),
    )


def build_writer_agent() -> Agent:
    """Slightly smarter model — writes the final digest and saves it."""
    return Agent(
        model=BedrockModel(model_id=WRITER_MODEL_ID),
        system_prompt=load_prompt("writer"),
        tools=[save_digest],
    )


def run_digest():
    today = datetime.now().strftime("%B %d, %Y")
    print(f"\n{'='*55}")
    print(f"  🤖 AI Digest Agent — {today}")
    print(f"{'='*55}\n")

    # ── Step 1: Fetch stories from all sources ──────────────────
    print("📡 Step 1: Fetching stories...")
    rss_raw = fetch_rss_stories()
    hn_raw  = fetch_hn_ai_stories()
    yt_raw  = fetch_youtube_stories()

    rss_stories = json.loads(rss_raw)
    hn_stories  = json.loads(hn_raw)
    yt_stories  = json.loads(yt_raw)
    all_stories = rss_stories + hn_stories + yt_stories

    print(f"\n  Total raw stories: {len(all_stories)}\n")

    if not all_stories:
        print("❌ No stories fetched. Check your network connection.")
        return

    # ── Step 2: Rank & deduplicate ──────────────────────────────
    print("🔍 Step 2: Ranking and deduplicating...")
    ranker = build_ranker_agent()

    rank_prompt = f"""
Here are {len(all_stories)} raw stories fetched today ({today}).
Please deduplicate, filter to AI-only, score, and return the top 10 as JSON.

STORIES:
{json.dumps(all_stories, ensure_ascii=False, indent=2)}
"""
    rank_response = ranker(rank_prompt)

    # Extract just the JSON array from the response text
    ranked_text = str(rank_response)
    start = ranked_text.find("[")
    end = ranked_text.rfind("]")
    if start != -1 and end != -1:
        ranked_text = ranked_text[start:end + 1]

    try:
        ranked_stories = json.loads(ranked_text)
        print(f"  ✓ Ranked {len(ranked_stories)} stories\n")
    except json.JSONDecodeError:
        print("  ⚠ Could not parse ranked JSON — using raw stories for writing")
        ranked_stories = all_stories[:10]

    # ── Step 2.5: Enrich stories with article content ───────────
    # Excerpts are trimmed to 600 chars before passing to the writer to avoid
    # overwhelming Nova Lite's tool-call generation with a 15-story prompt.
    print("🌐 Step 2.5: Fetching article content...")
    for story in ranked_stories:
        url = story.get("url", "")
        content = fetch_article_text(url, max_chars=600)
        if content:
            story["article_excerpt"] = content
            print(f"  ✓ {story.get('title', '')[:55]}")
        else:
            print(f"  ✗ (no content) {story.get('title', '')[:50]}")
    print()

    # ── Step 3: Write and save digest ──────────────────────────
    print("✍️  Step 3: Writing digest...")
    writer = build_writer_agent()

    write_prompt = f"""
Today is {today}.

Here are the top ranked AI stories for today's digest:

{json.dumps(ranked_stories, ensure_ascii=False, indent=2)}

Write the full digest in the required markdown format, then call save_digest with the complete content.
"""
    writer(write_prompt)

    # ── Done ────────────────────────────────────────────────────
    digest_path = os.path.join(
        os.path.dirname(__file__),
        "digests",
        f"digest-{datetime.now().strftime('%Y-%m-%d')}.md"
    )
    print(f"\n{'='*55}")
    print(f"  ✅ Done! Digest saved to:")
    print(f"     {digest_path}")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    run_digest()
