"""
Hacker News Fetcher Tool — pulls AI-related stories from the HN Algolia API.
Free, no API key required.
"""

import json
import time
import urllib.request
import urllib.parse
from strands import tool


HN_API = "https://hn.algolia.com/api/v1/search"

AI_KEYWORDS = [
    "LLM", "AI agent", "GPT", "Claude", "Gemini", "Mistral", "Llama",
    "machine learning", "artificial intelligence", "neural network",
    "Anthropic", "OpenAI", "DeepMind", "Hugging Face", "Bedrock",
    "Strands", "MCP", "model context", "fine-tuning", "RAG",
    "transformer", "diffusion model", "multimodal", "agentic"
]


def _fetch_hn(query: str, num_results: int = 8) -> list[dict]:
    seven_days_ago = int(time.time()) - 7 * 24 * 3600
    params = urllib.parse.urlencode({
        "query": query,
        "tags": "story",
        "numericFilters": f"points>10,created_at_i>{seven_days_ago}",
        "hitsPerPage": num_results,
    })
    url = f"{HN_API}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("hits", [])


@tool
def fetch_hn_ai_stories() -> str:
    """
    Fetches top AI-related stories from Hacker News using the Algolia search API.
    Searches for multiple AI keywords and returns deduplicated top stories.
    Returns a JSON list of stories with title, url, source, points, and comments.
    """
    seen_ids = set()
    all_stories = []

    # Search a few broad AI queries
    queries = ["AI agent LLM", "Claude Anthropic OpenAI", "machine learning open source"]

    for query in queries:
        try:
            hits = _fetch_hn(query, num_results=6)
            for hit in hits:
                story_id = hit.get("objectID")
                if story_id in seen_ids:
                    continue
                seen_ids.add(story_id)

                title = hit.get("title", "")
                url = hit.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
                points = hit.get("points", 0)
                comments = hit.get("num_comments", 0)

                all_stories.append({
                    "title": title,
                    "url": url,
                    "source": "Hacker News",
                    "description": f"{points} points, {comments} comments on HN",
                    "published": hit.get("created_at", ""),
                    "points": points,
                })
        except Exception as e:
            print(f"  ✗ HN query '{query}' failed — {e}")

    # Sort by points descending, take top 10
    all_stories.sort(key=lambda x: x.get("points", 0), reverse=True)
    top_stories = all_stories[:10]

    print(f"  ✓ Hacker News: {len(top_stories)} stories fetched")
    return json.dumps(top_stories, ensure_ascii=False)
