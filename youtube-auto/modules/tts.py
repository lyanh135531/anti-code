"""
==========================================================
  MODULE: TEXT-TO-SPEECH
  Dùng Edge TTS (Microsoft, miễn phí) - Giọng rất tự nhiên
==========================================================
"""

import asyncio
import logging
import re
import os
from pathlib import Path
import edge_tts

logger = logging.getLogger(__name__)


def _clean_script_for_tts(script: str) -> str:
    """
    Xử lý script trước khi đưa vào TTS:
    - Xóa các marker [SECTION:...], [PAUSE], v.v.
    - Làm sạch ký tự đặc biệt
    """
    # Xóa các heading markers
    text = re.sub(r'\[SECTION:[^\]]*\]', '', script)
    # Xóa [PAUSE X.Xs] markers (sẽ được thêm vào sau nếu edge-tts hỗ trợ)
    text = re.sub(r'\[PAUSE[^\]]*\]', ' ', text)
    # Xóa dấu [] còn lại
    text = re.sub(r'\[[^\]]*\]', '', text)
    # Xóa markdown (**, *, #)
    text = re.sub(r'[\*\#\_]+', '', text)
    # Chuẩn hóa khoảng trắng
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


async def _generate_audio_async(text: str, output_path: str, voice: str, rate: str, pitch: str):
    """Async function để tạo audio bằng Edge TTS."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)


def text_to_speech(
    script: str,
    output_path: str | Path,
    voice: str   = "en-US-AriaNeural",
    rate: str    = "-5%",
    pitch: str   = "+0Hz"
) -> str:
    """
    Chuyển script thành file audio MP3.
    
    Args:
        script:       Nội dung văn bản
        output_path:  Đường dẫn file output (.mp3)
        voice:        Tên giọng đọc Edge TTS
        rate:         Tốc độ đọc (-50% đến +100%)
        pitch:        Cao độ giọng (-50Hz đến +50Hz)
        
    Returns:
        Đường dẫn file audio đã tạo
    """
    output_path = str(output_path)
    clean_text = _clean_script_for_tts(script)

    if not clean_text.strip():
        raise ValueError("Script rỗng sau khi làm sạch!")

    word_count = len(clean_text.split())
    logger.info(f"TTS: {word_count} từ, giọng: {voice}, tốc độ: {rate}")

    # Chạy async trong event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            _generate_audio_async(clean_text, output_path, voice, rate, pitch)
        )
    finally:
        loop.close()

    # Kiểm tra file đã được tạo
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"File audio không được tạo: {output_path}")

    size_kb = os.path.getsize(output_path) / 1024
    logger.info(f"Audio đã tạo: {output_path} ({size_kb:.1f} KB)")
    return output_path


def get_audio_duration(audio_path: str | Path) -> float:
    """
    Lấy thời lượng file audio (giây).
    Dùng moviepy để đọc duration.
    """
    try:
        from moviepy.editor import AudioFileClip
        with AudioFileClip(str(audio_path)) as audio:
            return audio.duration
    except Exception as e:
        logger.warning(f"Không đọc được duration audio: {e}")
        # Ước tính: ~140 từ/phút trung bình
        return 0.0


async def list_available_voices() -> list:
    """Liệt kê tất cả giọng Edge TTS có sẵn tiếng Anh."""
    all_voices = await edge_tts.list_voices()
    en_voices = [v for v in all_voices if v["Locale"].startswith("en")]
    return en_voices


def print_english_voices():
    """In danh sách giọng tiếng Anh để người dùng chọn."""
    loop = asyncio.new_event_loop()
    voices = loop.run_until_complete(list_available_voices())
    loop.close()
    print("\n📢 Danh sách giọng tiếng Anh có sẵn:")
    print("-" * 60)
    for v in voices:
        print(f"  {v['ShortName']:<35} | {v['Gender']:<8} | {v['Locale']}")
    print("-" * 60)


if __name__ == "__main__":
    # Test: In danh sách giọng
    print_english_voices()
