"""Sleep and Ambient Bible Meditation script generation and curated topics."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from modules.ai_text import chat_complete, extract_json

logger = logging.getLogger(__name__)

SLEEP_TOPICS = {
    "psalm-91": {
        "id": "psalm-91",
        "title_seed": "Fall Asleep in God's Shelter: The Night Fortress of Psalm 91",
        "bible_passage": "Psalm 91:1-16",
        "theme": "Resting under the shadow of the Almighty, divine protection from night terrors and insomnia",
        "verses": [
            "Whoever dwells in the shelter of the Most High will rest in the shadow of the Almighty.",
            "I will say of the Lord, 'He is my refuge and my fortress, my God, in whom I trust.'",
            "He will cover you with his feathers, and under his wings you will find refuge.",
            "You will not fear the terror of night, nor the arrow that flies by day.",
            "For he will command his angels concerning you to guard you in all your ways.",
        ],
    },
    "psalm-23": {
        "id": "psalm-23",
        "title_seed": "Sleep in God's Peace: Psalm 23 for Deep Rest and Healing",
        "bible_passage": "Psalm 23:1-6",
        "theme": "The Good Shepherd leading beside quiet waters, restoring the tired soul, banishing fear in dark valleys",
        "verses": [
            "The Lord is my shepherd, I lack nothing.",
            "He makes me lie down in green pastures, he leads me beside quiet waters, he refreshes my soul.",
            "Even though I walk through the darkest valley, I will fear no evil, for you are with me.",
            "Your rod and your staff, they comfort me.",
            "Surely your goodness and love will follow me all the days of my life.",
        ],
    },
    "psalm-121": {
        "id": "psalm-121",
        "title_seed": "The Lord Who Never Sleeps: Nighttime Prayers for Insomnia and Rest",
        "bible_passage": "Psalm 121:1-8",
        "theme": "The Keeper of Israel neither slumbers nor sleeps, constant watch over your sleep and spirit",
        "verses": [
            "I lift up my eyes to the mountains—where does my help come from? My help comes from the Lord, the Maker of heaven and earth.",
            "He will not let your foot slip—he who watches over you will not slumber.",
            "Indeed, he who watches over Israel will neither slumber nor sleep.",
            "The Lord watches over you—the Lord is your shade at your right hand.",
            "The Lord will keep your going out and your coming in from this time forth and forevermore.",
        ],
    },
    "peace-be-still": {
        "id": "peace-be-still",
        "title_seed": "Peace Be Still: Calming Night Thoughts With Jesus",
        "bible_passage": "Mark 4:35-41 & Matthew 11:28-30",
        "theme": "Jesus calming the turbulent storm of overthinking, taking upon His gentle yoke, resting the weary soul",
        "verses": [
            "He got up, rebuked the wind and said to the waves, 'Quiet! Be still!' Then the wind died down and it was completely calm.",
            "Come to me, all you who are weary and burdened, and I will give you rest.",
            "Take my yoke upon you and learn from me, for I am gentle and humble in heart, and you will find rest for your souls.",
            "Peace I leave with you; my peace I give you. Do not let your hearts be troubled and do not be afraid.",
        ],
    },
    "releasing-anxiety": {
        "id": "releasing-anxiety",
        "title_seed": "Cast All Your Cares Upon Him: Overcoming Night Anxiety and Finding Rest",
        "bible_passage": "Philippians 4:6-9 & 1 Peter 5:6-10",
        "theme": "The peace of God which surpasses all understanding guarding hearts and minds in Christ Jesus",
        "verses": [
            "Do not be anxious about anything, but in every situation, by prayer and petition, present your requests to God.",
            "And the peace of God, which transcends all understanding, will guard your hearts and your minds in Christ Jesus.",
            "Cast all your anxiety on him because he cares for you.",
            "In peace I will lie down and sleep, for you alone, Lord, make me dwell in safety.",
        ],
    },
    "psalm-4": {
        "id": "psalm-4",
        "title_seed": "In Peace I Will Lie Down and Sleep: Resting in God's Faithfulness",
        "bible_passage": "Psalm 4:1-8",
        "theme": "Resting serenely in the assurance that God alone makes you dwell in safety",
        "verses": [
            "Answer me when I call to you, my righteous God. Give me relief from my distress.",
            "Know that the Lord has set apart his faithful servant; the Lord hears when I call to him.",
            "Tremble and do not sin; when you are on your beds, search your hearts and be silent.",
            "In peace I will lie down and sleep, for you alone, Lord, make me dwell in safety.",
        ],
    },
    "psalm-46": {
        "id": "psalm-46",
        "title_seed": "Be Still, and Know That I Am God: Quiet Waters in the Storm",
        "bible_passage": "Psalm 46:1-11",
        "theme": "God as our refuge and strength, an ever-present help in trouble, quieting nocturnal anxiety",
        "verses": [
            "God is our refuge and strength, an ever-present help in trouble.",
            "Therefore we will not fear, though the earth give way and the mountains fall into the heart of the sea.",
            "He says, 'Be still, and know that I am God; I will be exalted among the nations.'",
            "The Lord Almighty is with us; the God of Jacob is our fortress.",
        ],
    },
    "matthew-6": {
        "id": "matthew-6",
        "title_seed": "Do Not Worry About Tomorrow: Overcoming Nighttime Overthinking",
        "bible_passage": "Matthew 6:25-34",
        "theme": "Jesus reassuring that the Heavenly Father provides for each day, banishing tomorrow's worries",
        "verses": [
            "Therefore I tell you, do not worry about your life, what you will eat or drink; or about your body.",
            "Look at the birds of the air; they do not sow or reap or store away in barns, and yet your heavenly Father feeds them.",
            "Can any one of you by worrying add a single hour to your life?",
            "Therefore do not worry about tomorrow, for tomorrow will worry about itself.",
        ],
    },
    "psalm-27": {
        "id": "psalm-27",
        "title_seed": "The Lord Is My Light: Deliverance From Fear in the Night",
        "bible_passage": "Psalm 27:1-14",
        "theme": "The Lord is my light and my salvation, whom shall I fear; resting safely in His sacred tent",
        "verses": [
            "The Lord is my light and my salvation—whom shall I fear? The Lord is the stronghold of my life.",
            "One thing I ask from the Lord, this only do I seek: that I may dwell in the house of the Lord all the days of my life.",
            "For in the day of trouble he will keep me safe in his dwelling; he will hide me in the shelter of his sacred tent.",
            "Wait for the Lord; be strong and take heart and wait for the Lord.",
        ],
    },
    "psalm-63": {
        "id": "psalm-63",
        "title_seed": "Through the Watches of the Night: Deep Rest in God's Gentle Presence",
        "bible_passage": "Psalm 63:1-8",
        "theme": "Meditating on God's steadfast love on your bed through the stillness of night",
        "verses": [
            "You, God, are my God, earnestly I seek you; I thirst for you, my whole being longs for you.",
            "Because your love is better than life, my lips will glorify you.",
            "On my bed I remember you; I think of you through the watches of the night.",
            "Because you are my help, I sing in the shadow of your wings. I cling to you; your right hand upholds me.",
        ],
    },
    "john-14": {
        "id": "john-14",
        "title_seed": "My Peace I Leave With You: Unshakable Calm for the Restless Soul",
        "bible_passage": "John 14:1-6, 27",
        "theme": "The supernatural peace of Christ dispelling troubled hearts and fear",
        "verses": [
            "Do not let your hearts be troubled. You believe in God; believe also in me.",
            "Peace I leave with you; my peace I give you. I do not give to you as the world gives.",
            "Do not let your hearts be troubled and do not be afraid.",
        ],
    },
    "proverbs-3": {
        "id": "proverbs-3",
        "title_seed": "Your Sleep Will Be Sweet: Godly Promises for Peaceful Rest",
        "bible_passage": "Proverbs 3:21-26",
        "theme": "When you lie down, you will not be afraid; your sleep will be sweet under the Lord's wisdom",
        "verses": [
            "Maintain sound wisdom and discretion; they will be life for your soul.",
            "Then you will go on your way in safety, and your foot will not stumble.",
            "When you lie down, you will not be afraid; when you lie down, your sleep will be sweet.",
            "Have no fear of sudden disaster, for the Lord will be at your side.",
        ],
    },
    "psalm-139": {
        "id": "psalm-139",
        "title_seed": "Resting in Everlasting Arms: You Are Known and Protected Tonight",
        "bible_passage": "Psalm 139:1-18",
        "theme": "God's omnipresent love enclosing you behind and before, darkness is as light to Him",
        "verses": [
            "You have searched me, Lord, and you know me. You know when I sit and when I rise.",
            "You hem me in behind and before, and you lay your hand upon me.",
            "If I say, 'Surely the darkness will hide me,' even the darkness will not be dark to you.",
            "How precious to me are your thoughts, God! When I awake, I am still with you.",
        ],
    },
    "isaiah-40": {
        "id": "isaiah-40",
        "title_seed": "He Gives Strength to the Weary: Renewing Your Soul While You Sleep",
        "bible_passage": "Isaiah 40:28-31",
        "theme": "The everlasting God who does not faint or grow weary restoring your tired strength",
        "verses": [
            "The Lord is the everlasting God, the Creator of the ends of the earth. He will not grow tired or weary.",
            "He gives strength to the weary and increases the power of the weak.",
            "Those who hope in the Lord will renew their strength. They will soar on wings like eagles.",
            "They will run and not grow weary, they will walk and not be faint.",
        ],
    },
    "psalm-34": {
        "id": "psalm-34",
        "title_seed": "The Angel of the Lord Around You: Healing Rest for the Brokenhearted",
        "bible_passage": "Psalm 34:1-18",
        "theme": "God delivering from all fears, angels encamping around those who fear Him",
        "verses": [
            "I sought the Lord, and he answered me; he delivered me from all my fears.",
            "Those who look to him are radiant; their faces are never covered with shame.",
            "The angel of the Lord encamps around those who fear him, and he delivers them.",
            "The Lord is close to the brokenhearted and saves those who are crushed in spirit.",
        ],
    },
}

DEFAULT_SLEEP_PROMPTS = [
    (
        "masterpiece oil painting in dark chiaroscuro, an ancient wooden window overlooking a gentle night rain "
        "and distant misty olive grove under a star-filled velvet sky, a single warm glowing candle on the stone sill, "
        "a leather-bound Bible beside it, deep indigo and amber tones, tranquil, calm, 8k resolution, no human faces"
    ),
    (
        "fine art oil painting, quiet candlelit interior of a first-century stone chamber, soft golden warm glow "
        "illuminating an open scroll of ancient scripture on an olive wood table, shadows melting softly into the walls, "
        "serene atmosphere of peace and reverent rest, no people"
    ),
    (
        "classical oil painting, tranquil sea of Galilee at midnight under a vast canopy of quiet stars, calm water "
        "reflecting soft moonlight, distant dark silhouettes of hills, peaceful nocturnal atmosphere, painterly impasto "
        "texture, deep midnight blues and muted silver, no faces"
    ),
    (
        "baroque oil painting, a rustic oil lamp glowing with a warm ember light in a quiet prayer alcove, "
        "gentle rain streaks visible through an archway, rich earth tones, deep contemplative shadows, sacred peaceful sanctuary, "
        "museum quality, no human figures"
    ),
]


def load_sleep_history(history_file: Path) -> list[str]:
    if not history_file.exists():
        return []
    return [line.strip() for line in history_file.read_text(encoding="utf-8").splitlines() if line.strip()]


def record_sleep_topic(history_file: Path, topic_id: str) -> None:
    history_file.parent.mkdir(parents=True, exist_ok=True)
    with history_file.open("a", encoding="utf-8") as f:
        f.write(f"{topic_id}\n")


def select_sleep_topic(history_file: Path, requested_id: str | None = None) -> tuple[str, dict[str, Any]]:
    if requested_id and requested_id in SLEEP_TOPICS:
        return requested_id, SLEEP_TOPICS[requested_id]
    used = load_sleep_history(history_file)
    for topic_id, topic_data in SLEEP_TOPICS.items():
        if topic_id not in used:
            return topic_id, topic_data
    # If all used, cycle back to the first
    first_id = list(SLEEP_TOPICS.keys())[0]
    return first_id, SLEEP_TOPICS[first_id]


def build_fallback_sleep_script(topic: dict[str, Any]) -> dict[str, Any]:
    passage = topic["bible_passage"]
    theme = topic["theme"]
    verses_text = " ".join(topic["verses"])

    sections = [
        {
            "heading": "Opening & Deep Breath Relaxation",
            "narration": (
                "Welcome, dear friend. Take a moment right now to close your eyes and let the weight of this day fall from your shoulders. "
                "The tasks you completed, and the things left unfinished—surrender them all into the loving hands of Jesus Christ. "
                "Take a slow, deep breath in... filling your spirit with God's unconditional grace. "
                "And gently exhale... releasing every worry, every ounce of tension from your body. "
                "You are safe here tonight. God is in control. His presence is wrapping around you like a warm mantle. "
                "Breathe in peace, and breathe out fear. Tonight, we rest under the shelter of His holy word."
            ),
        },
        {
            "heading": f"Reflections on {passage}",
            "narration": (
                f"Tonight, let your heart meditate upon {passage}. "
                f"Scripture tells us: {verses_text} "
                "Consider these sacred promises as you lay your head down. God does not demand that you figure out tomorrow tonight. "
                "He asks only that you trust Him. When the night feels quiet and your thoughts begin to race, remember that the Almighty "
                "is closer to you than your very breath. Under His wings, you find a sanctuary where darkness has no power. "
                "His faithfulness is your shield and your rampart. Whatever trial you faced today, it is not greater than the God who sustains you. "
                "Let the quiet truth of His love silence every anxiety in your mind."
            ),
        },
        {
            "heading": "A Nighttime Prayer of Surrender",
            "narration": (
                "Let us pray together. Heavenly Father, I come before You tonight in the stillness of this hour. "
                "I bring You my tired body, my weary mind, and every unspoken concern resting heavy on my heart. "
                "Lord, I release every fear of tomorrow. I surrender every person I love into Your sovereign protection. "
                "Place Your holy angels around my home tonight. Protect my dreams, restore my soul, and fill this room with the warmth "
                "of the Holy Spirit. Lord Jesus, grant me the deep, restorative sleep that You give to Your beloved. "
                "May I wake tomorrow renewed in strength, purpose, and joy."
            ),
        },
        {
            "heading": "Closing Blessing & Gentle Rest",
            "narration": (
                "May the Lord bless you and keep you. "
                "May the Lord make His face shine upon you and be gracious unto you. "
                "May the Lord turn His face toward you and give you peace. "
                "Sleep now, dear soul, in heavenly peace. The Lord is watching over you. "
                "Sleep in peace. Rest in grace. Amen."
            ),
        },
    ]

    full_narration = "\n\n".join(section["narration"] for section in sections)

    return {
        "title": f"{topic['title_seed']} | 2 Hours of Peaceful Night Prayers & Scriptures",
        "passage": passage,
        "summary": (
            f"Rest deeply tonight with calming scriptures and bedtime prayers centered on {passage}. "
            "Designed to ease insomnia, quiet overthinking, and help you fall asleep under God's loving protection."
        ),
        "thumbnail_text": "SLEEP IN PEACE",
        "sections": sections,
        "narration": full_narration,
        "visual_prompts": DEFAULT_SLEEP_PROMPTS,
        "tags": [
            "bible sleep meditation",
            "psalm 91 sleep",
            "fall asleep fast christian",
            "peaceful sleep prayer",
            "bible stories for sleep",
            "sleep in gods peace",
            "christian ambient",
            "calming scripture for anxiety",
            "night prayer",
            "bedtime bible prayer",
        ],
    }


def generate_sleep_script(topic: dict[str, Any]) -> dict[str, Any]:
    system_prompt = (
        "You are an expert contemplative Christian author and audio pastor specializing in peaceful, "
        "reverent bedtime scripture meditations and sleep prayers for listeners struggling with insomnia and anxiety.\n"
        "Tone: Gentle, deeply comforting, unhurried, pastoral, non-dogmatic, warm.\n"
        "Avoid: Fearbait, end-times dread, fake personal testimonies, harsh theological disputes, or dramatic cliffhangers.\n"
        "Return ONLY a valid JSON object matching the requested schema."
    )

    user_prompt = f"""Write a soothing 30-40 minute bedtime scripture reflection and prayer based on {topic['bible_passage']} ({topic['theme']}).

Schema requirements:
{{
  "title": "A captivating, comforting YouTube title (e.g. 'Fall Asleep in God's Peace | 2 Hours of Calming Psalms & Night Prayers')",
  "passage": "{topic['bible_passage']}",
  "summary": "A 2-paragraph YouTube description explaining the calming focus of this sleep prayer",
  "thumbnail_text": "2-3 bold soothing words (e.g. 'SLEEP IN PEACE', 'HE PROTECTS YOU', 'REST WITH GOD')",
  "sections": [
    {{
      "heading": "Opening & Deep Breath Relaxation",
      "narration": "Gentle guidance inviting listener to lay down their worries, take slow deep breaths, and invite Jesus' peace."
    }},
    {{
      "heading": "Scripture Reading & Sacred Reflection",
      "narration": "Slow, contemplative exploration of {topic['bible_passage']}. Quote verses peacefully and reflect on God's abiding protection."
    }},
    {{
      "heading": "Nighttime Prayer of Surrender",
      "narration": "A heartfelt prayer releasing fear, giving family and burdens to God, asking for angel protection over the home."
    }},
    {{
      "heading": "Benediction & Closing Peace",
      "narration": "Aaronic blessing and tender closing words leading into silent rest."
    }}
  ],
  "visual_prompts": [
    "4 detailed 16:9 prompts for dark atmospheric oil paintings (candlelight, ancient scripture, night rain, starry sky, no faces, museum quality)"
  ],
  "tags": ["list of 10-12 relevant search tags for sleep prayers and christian relaxation"]
}}

Ensure the narration is poetic, calming, and deeply grounded in scripture."""

    try:
        raw_text = chat_complete(system_prompt, user_prompt, temperature=0.7)
        data = extract_json(raw_text)
        if (
            isinstance(data, dict)
            and "sections" in data
            and len(data["sections"]) >= 3
            and "title" in data
        ):
            data["narration"] = "\n\n".join(sec["narration"] for sec in data["sections"])
            if not data.get("visual_prompts") or len(data["visual_prompts"]) < 4:
                data["visual_prompts"] = DEFAULT_SLEEP_PROMPTS
            return data
    except Exception as e:
        logger.warning(f"Could not generate dynamic sleep script ({e}), falling back to curated script.")

    return build_fallback_sleep_script(topic)
