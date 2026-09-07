"""Curated, source-backed topic selection for the independent long-form flow."""

from __future__ import annotations

import json
from pathlib import Path


TOPICS = {
    "good-samaritan": {
        "title_seed": "The Good Samaritan: The Neighbor We Refuse to See",
        "bible_passage": "Luke 10:25-37",
        "bible_url": "https://www.vatican.va/archive/ENG0839/__PWT.HTM",
        "ccc_urls": [
            "https://www.vatican.va/content/catechism/en/part_three/section_two/chapter_two/article_5/i_respect_for_human_life.html",
            "https://www.vatican.va/content/catechism/en/part_three/section_two/chapter_two/article_7/vi_love_for_the_poor.html",
        ],
    },
    "prodigal-son": {
        "title_seed": "The Prodigal Son: What the Father Was Waiting For",
        "bible_passage": "Luke 15:11-32",
        "bible_url": "https://www.vatican.va/archive/ENG0839/__PWY.HTM",
        "ccc_urls": [
            "https://www.vatican.va/content/catechism/en/part_two/section_two/chapter_two/article_4/i_what_is_this_sacrament_called.html",
            "https://www.vatican.va/content/catechism/en/part_two/section_two/chapter_two/article_4.html",
        ],
    },
    "woman-at-the-well": {
        "title_seed": "The Woman at the Well: Why Jesus Asked for Water",
        "bible_passage": "John 4:4-42",
        "bible_url": "https://www.vatican.va/archive/ENG0839/__PXC.HTM",
        "ccc_urls": [
            "https://www.vatican.va/content/catechism/en/part_two/section_two/chapter_one/article_1/iii_how_is_the_sacrament_of_baptism_celebrated.html",
            "https://www.vatican.va/content/catechism/en/part_four/section_one.html",
        ],
    },
    "road-to-emmaus": {
        "title_seed": "The Road to Emmaus: Why They Did Not Recognize Jesus",
        "bible_passage": "Luke 24:13-35",
        "bible_url": "https://www.vatican.va/archive/ENG0839/__PX7.HTM",
        "ccc_urls": [
            "https://www.vatican.va/content/catechism/en/part_two/section_two/chapter_one/article_3/iii_the_eucharist_in_the_economy_of_salvation.html",
            "https://www.vatican.va/content/catechism/en/part_one/section_two/chapter_two/article_5/he_descended_into_hell_on_the_third_day_he_rose_again.html",
        ],
    },
    "calming-the-storm": {
        "title_seed": "Jesus Calms the Storm: The Question the Disciples Missed",
        "bible_passage": "Mark 4:35-41",
        "bible_url": "https://www.vatican.va/archive/ENG0839/__PW6.HTM",
        "ccc_urls": [
            "https://www.vatican.va/content/catechism/en/part_one/section_two/chapter_one/article_1/paragraph_4_the_creator.html",
            "https://www.vatican.va/content/catechism/en/part_four/section_one/chapter_three/article_2/ii_humble_vigilance_of_heart.html",
        ],
    },
    "raising-lazarus": {
        "title_seed": "Lazarus: Why Jesus Waited Before He Came",
        "bible_passage": "John 11:1-44",
        "bible_url": "https://www.vatican.va/archive/ENG0839/__PXJ.HTM",
        "ccc_urls": [
            "https://www.vatican.va/content/catechism/en/part_one/section_two/chapter_two/article_5/paragraph_2_on_the_third_day_he_rose_from_the_dead.html",
            "https://www.vatican.va/content/catechism/en/part_one/section_two/chapter_three/article_11.html",
        ],
    },
    "zacchaeus": {
        "title_seed": "Zacchaeus: The One Thing Jesus Saw That No One Else Did",
        "bible_passage": "Luke 19:1-10",
        "bible_url": "https://www.vatican.va/archive/ENG0839/__PX2.HTM",
        "ccc_urls": [
            "https://www.vatican.va/content/catechism/en/part_three/section_one/chapter_three/article_2/iii_merit.html",
            "https://www.vatican.va/content/catechism/en/part_three/section_two/chapter_two/article_7/ii_respect_for_persons_and_their_goods.html",
        ],
    },
    "peter-walks-on-water": {
        "title_seed": "Peter Walked on Water—Then Looked Away",
        "bible_passage": "Matthew 14:22-33",
        "bible_url": "https://www.vatican.va/archive/ENG0839/__PVN.HTM",
        "ccc_urls": [
            "https://www.vatican.va/content/catechism/en/part_one/section_one/chapter_three/article_1/iii_the_characteristics_of_faith.html",
            "https://www.vatican.va/content/catechism/en/part_four/section_one/chapter_three/article_2/ii_humble_vigilance_of_heart.html",
        ],
    },
}


def load_history(path: str | Path) -> list[str]:
    history_path = Path(path)
    if not history_path.exists():
        return []
    return [line.strip() for line in history_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def select_topic(history_path: str | Path, topic_id: str | None = None) -> tuple[str, dict]:
    if topic_id:
        if topic_id not in TOPICS:
            raise ValueError(f"Unknown long-form topic id: {topic_id}")
        return topic_id, dict(TOPICS[topic_id])
    used = set(load_history(history_path))
    for candidate, config in TOPICS.items():
        if candidate not in used:
            return candidate, dict(config)
    # Start a new ordered rotation only after the complete catalog was used.
    items = list(TOPICS.items())
    candidate, config = items[len(load_history(history_path)) % len(items)]
    return candidate, dict(config)


def record_topic(path: str | Path, topic_id: str) -> None:
    history_path = Path(path)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(topic_id + "\n")


def topic_catalog_json() -> str:
    return json.dumps(TOPICS, ensure_ascii=False, indent=2)
