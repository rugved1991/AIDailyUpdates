"""
Save Digest Tool — writes the final markdown digest to the digests/ folder.
"""

import html
import os
from datetime import datetime
from strands import tool


DIGEST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "digests")


@tool
def save_digest(content: str) -> str:
    """
    Saves the final AI news digest markdown content to a dated file
    in the digests/ directory.

    Args:
        content: The full markdown content of the digest to save.

    Returns:
        The filepath where the digest was saved.
    """
    os.makedirs(DIGEST_DIR, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"digest-{today}.md"
    filepath = os.path.join(DIGEST_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html.unescape(content))

    print(f"  ✓ Digest saved to: {filepath}")
    return filepath
