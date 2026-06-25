"""
==========================================================
  MODULE: SUBTITLE PARSER — Word-level timing extraction
  Parse SRT from Edge TTS into per-word timestamps
  for word-by-word subtitle rendering.
==========================================================

Edge TTS generates SRT with phrase-level timing.
We estimate word-level timing by distributing time
proportionally based on word character count.
"""

import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WordTiming:
    word: str
    start: float
    end: float


@dataclass
class PhraseTiming:
    words: list[WordTiming]
    start: float
    end: float


def parse_srt_to_phrases(srt_path: str) -> list[PhraseTiming]:
    """
    Parse SRT file into phrases with word-level timing.
    
    Edge TTS SRT format:
    1
    00:00:00,000 --> 00:00:02,500
    Hello world this is a test
    
    Returns:
        List of PhraseTiming with per-word timestamps
    """
    if not srt_path or not __import__('os').path.exists(srt_path):
        return []
    
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split into subtitle blocks
    blocks = re.split(r'\n\s*\n', content.strip())
    phrases = []
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 3:
            continue
        
        # Find the timing line (contains "-->")
        timing_line = None
        text_line_idx = None
        for i, line in enumerate(lines):
            if '-->' in line:
                timing_line = line
                text_line_idx = i + 1
                break
        
        if not timing_line or text_line_idx is None or text_line_idx >= len(lines):
            continue
        
        # Parse timestamps
        times = timing_line.split('-->')
        if len(times) != 2:
            continue
        
        start = _parse_timestamp(times[0].strip())
        end = _parse_timestamp(times[1].strip())
        
        if start is None or end is None:
            continue
        
        # Get text (may span multiple lines)
        text = ' '.join(lines[text_line_idx:]).strip()
        if not text:
            continue
        
        # Split into words and estimate timing
        words = text.split()
        if not words:
            continue
        
        # Distribute time proportionally by character count
        total_chars = sum(len(w) for w in words)
        duration = end - start
        
        if total_chars == 0 or duration <= 0:
            continue
        
        word_timings = []
        current_time = start
        
        for word in words:
            # Word duration proportional to its character count
            word_ratio = len(word) / total_chars
            word_duration = duration * word_ratio
            
            word_timings.append(WordTiming(
                word=word,
                start=current_time,
                end=current_time + word_duration
            ))
            current_time += word_duration
        
        phrases.append(PhraseTiming(
            words=word_timings,
            start=start,
            end=end
        ))
    
    logger.info(f"Parsed {len(phrases)} phrases, {sum(len(p.words) for p in phrases)} words from SRT")
    return phrases


def _parse_timestamp(ts: str) -> float | None:
    """Parse SRT timestamp 'HH:MM:SS,mmm' to seconds."""
    try:
        ts = ts.strip().replace(',', '.')
        parts = ts.split(':')
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        return None
    except (ValueError, IndexError):
        return None


def get_active_word(phrases: list[PhraseTiming], t: float) -> tuple[str, int, float] | None:
    """
    Get the word being spoken at time t.
    
    Returns:
        (word_text, word_index_in_phrase, phrase_index) or None
    """
    for pi, phrase in enumerate(phrases):
        if phrase.start <= t <= phrase.end:
            for wi, word in enumerate(phrase.words):
                if word.start <= t <= word.end:
                    return (word.word, wi, pi)
            # If between words, return the last word
            for wi in range(len(phrase.words) - 1, -1, -1):
                if t >= phrase.words[wi].start:
                    return (phrase.words[wi].word, wi, pi)
    return None


def get_current_phrase(phrases: list[PhraseTiming], t: float) -> PhraseTiming | None:
    """Get the phrase being spoken at time t."""
    for phrase in phrases:
        if phrase.start <= t <= phrase.end:
            return phrase
    return None
