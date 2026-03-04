"""
RSS Fetcher Tool — pulls stories from technical AI blogs and tutorials.
"""

import html
import json
import re
import urllib.request
import defusedxml.ElementTree as ET
from xml.etree.ElementTree import Element
from strands import tool


RSS_SOURCES = {
    "Simon Willison":      "https://simonwillison.net/atom/everything/",
    "Hugging Face Blog":   "https://huggingface.co/blog/feed.xml",
    "Sebastian Raschka":   "https://magazine.sebastianraschka.com/feed",
}

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _fetch_xml(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (AI Digest Bot)"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _get_link(item: Element) -> str:
    """Extract URL from either RSS <link> (text) or Atom <link href="...">."""
    link_el = item.find("link")
    if link_el is not None:
        # RSS: text content
        if link_el.text and link_el.text.strip():
            return link_el.text.strip()
        # Atom: href attribute
        href = link_el.get("href", "")
        if href:
            return href
    # Atom feeds may have multiple <link> elements; find rel="alternate"
    for el in item.findall("atom:link", ATOM_NS):
        if el.get("rel", "alternate") == "alternate":
            return el.get("href", "")
    return ""


def _parse_feed(xml_text: str, source_name: str, max_items: int = 8) -> list[dict]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    # Support both RSS <item> and Atom <entry>
    items = root.findall(".//item") or root.findall(".//atom:entry", ATOM_NS)

    stories = []
    for item in items[:max_items]:
        title_el = item.find("title")
        desc_el = (item.find("description")
                   or item.find("atom:summary", ATOM_NS)
                   or item.find("atom:content", ATOM_NS))
        pub_el = item.find("pubDate") or item.find("atom:published", ATOM_NS)

        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        link = _get_link(item)

        raw_desc = desc_el.text or "" if desc_el is not None else ""
        raw_desc = re.sub(r"<[^>]+>", " ", raw_desc)
        description = html.unescape(re.sub(r"\s+", " ", raw_desc).strip())[:400]

        pub_date = pub_el.text.strip() if pub_el is not None and pub_el.text else ""

        if title and link:
            stories.append({
                "title": title,
                "url": link,
                "source": source_name,
                "description": description,
                "published": pub_date,
            })

    return stories


@tool
def fetch_rss_stories() -> str:
    """
    Fetches the latest AI articles from technical blogs (Simon Willison,
    Hugging Face, Sebastian Raschka). Returns a JSON list of stories.
    """
    all_stories = []

    for source_name, url in RSS_SOURCES.items():
        try:
            xml_text = _fetch_xml(url)
            stories = _parse_feed(xml_text, source_name)
            all_stories.extend(stories)
            print(f"  ✓ {source_name}: {len(stories)} stories fetched")
        except Exception as e:
            print(f"  ✗ {source_name}: failed — {e}")

    return json.dumps(all_stories, ensure_ascii=False)
