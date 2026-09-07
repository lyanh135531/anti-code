"""Fetch and validate the official source pack used by long-form generation."""

from __future__ import annotations

import html
import re
from pathlib import Path
from urllib.parse import urlparse

import requests


ALLOWED_SOURCE_HOSTS = frozenset({"bible.usccb.org", "www.vatican.va", "vatican.va"})
INTERPRETATION_URL = (
    "https://www.vatican.va/content/catechism/en/part_one/section_one/chapter_two/"
    "article_3/iii_the_holy_spirit%2C_interpreter_of_scripture.html"
)


def is_allowed_source(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in ALLOWED_SOURCE_HOSTS


def _extract_text(raw_html: str) -> str:
    cleaned = re.sub(r"(?is)<(script|style|nav|footer|header).*?>.*?</\1>", " ", raw_html)
    cleaned = re.sub(r"(?s)<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def fetch_source(url: str, timeout: int = 45) -> str:
    if not is_allowed_source(url):
        raise ValueError(f"Source host is not allowed: {url}")
    response = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": "SpiritusSourceVerifier/1.0 (+YouTube educational production)"},
    )
    response.raise_for_status()
    text = _extract_text(response.text)
    if len(text) < 500:
        raise RuntimeError(f"Official source returned too little usable text: {url}")
    return text[:18_000]


def build_source_pack(topic: dict, output_path: str | Path) -> dict:
    urls = [("BIBLE", topic["bible_url"]), ("CCC_INTERPRETATION", INTERPRETATION_URL)]
    urls.extend((f"CCC_TOPIC_{index}", url) for index, url in enumerate(topic["ccc_urls"], 1))
    sources = []
    for source_id, url in urls:
        sources.append({"id": source_id, "url": url, "text": fetch_source(url)})
    pack = {
        "bible_passage": topic["bible_passage"],
        "sources": sources,
        "allowed_hosts": sorted(ALLOWED_SOURCE_HOSTS),
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    import json

    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    return pack
