"""
YouTube Fetcher — fetches latest videos from AI YouTube channels and extracts transcripts.

Requires:
    YOUTUBE_API_KEY environment variable (free, from Google Cloud Console)
    pip install youtube-transcript-api

Uses the YouTube Data API v3 playlistItems endpoint (1 quota unit per call, very cheap)
instead of the search endpoint (100 units per call) to stay well within the free 10k/day limit.
"""

import json
import os
import urllib.parse
import urllib.request

from strands import tool

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    HAS_TRANSCRIPT_API = True
except ImportError:
    HAS_TRANSCRIPT_API = False

# YouTube channel handles to fetch from.
# Find a channel's handle by visiting the channel page on YouTube — it's the @name in the URL.
YOUTUBE_CHANNELS = {
    "Yannic Kilcher":    "@YannicKilcher",
    "AI Explained":      "@aiexplained",
    "Two Minute Papers": "@TwoMinutePapers",
}

_YT_API_BASE = "https://www.googleapis.com/youtube/v3"
_MAX_VIDEOS_PER_CHANNEL = 2  # Keep low — transcripts add significant tokens


def _yt_get(path: str, params: dict, api_key: str) -> dict:
    params["key"] = api_key
    url = f"{_YT_API_BASE}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (AI Digest Bot)"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_uploads_playlist(handle: str, api_key: str) -> str | None:
    """Resolve a @handle to the channel's uploads playlist ID (costs 1 quota unit)."""
    data = _yt_get("channels", {
        "part": "contentDetails",
        "forHandle": handle.lstrip("@"),
    }, api_key)
    items = data.get("items", [])
    if not items:
        return None
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def _get_latest_videos(playlist_id: str, api_key: str) -> list[dict]:
    """Fetch the most recent videos from an uploads playlist (costs 1 quota unit)."""
    data = _yt_get("playlistItems", {
        "part": "snippet",
        "playlistId": playlist_id,
        "maxResults": _MAX_VIDEOS_PER_CHANNEL,
    }, api_key)

    videos = []
    for item in data.get("items", []):
        snippet = item["snippet"]
        video_id = snippet["resourceId"]["videoId"]
        # Skip deleted/private videos
        if snippet.get("title") in ("Deleted video", "Private video"):
            continue
        videos.append({
            "video_id": video_id,
            "title": snippet["title"],
            "published": snippet["publishedAt"],
            "description": snippet.get("description", "")[:400],
        })
    return videos


def _get_transcript(video_id: str, max_chars: int = 1500) -> str:
    """
    Fetch and return a plain text transcript excerpt for a YouTube video.
    Returns empty string if transcripts are unavailable or disabled.
    """
    if not HAS_TRANSCRIPT_API:
        return ""
    try:
        # Prefer manually created English transcript; fall back to auto-generated
        entries = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["en", "en-US", "en-GB"]
        )
        text = " ".join(e["text"] for e in entries)
        # Clean up common transcript artifacts
        text = text.replace("\n", " ").replace("[Music]", "").replace("[Applause]", "")
        return " ".join(text.split())[:max_chars]
    except Exception:
        return ""


@tool
def fetch_youtube_stories() -> str:
    """
    Fetches the latest videos from AI YouTube channels and extracts transcript excerpts.
    Requires YOUTUBE_API_KEY environment variable.
    Returns a JSON list of stories in the same format as other fetchers.
    Silently skips if the API key is not configured.
    """
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        print("  ✗ YouTube: YOUTUBE_API_KEY not set — skipping")
        return json.dumps([])

    if not HAS_TRANSCRIPT_API:
        print("  ✗ YouTube: youtube-transcript-api not installed — run: pip install youtube-transcript-api")
        return json.dumps([])

    all_stories = []

    for source_name, handle in YOUTUBE_CHANNELS.items():
        try:
            playlist_id = _get_uploads_playlist(handle, api_key)
            if not playlist_id:
                print(f"  ✗ {source_name}: could not resolve handle {handle}")
                continue

            videos = _get_latest_videos(playlist_id, api_key)

            for video in videos:
                transcript = _get_transcript(video["video_id"])
                story = {
                    "title": video["title"],
                    "url": f"https://www.youtube.com/watch?v={video['video_id']}",
                    "source": source_name,
                    "description": video["description"],
                    "published": video["published"],
                }
                if transcript:
                    story["article_excerpt"] = transcript
                all_stories.append(story)

            print(f"  ✓ {source_name}: {len(videos)} videos fetched")

        except Exception as e:
            print(f"  ✗ {source_name}: failed — {e}")

    return json.dumps(all_stories, ensure_ascii=False)
