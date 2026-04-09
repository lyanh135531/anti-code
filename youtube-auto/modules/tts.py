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


def _split_text_into_chunks(text: str, max_chars: int = 2500) -> list[str]:
    """
    Chia văn bản thành các đoạn nhỏ hơn để tránh timeout/lỗi service.
    Cố gắng chia theo đoạn văn hoặc câu.
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    # Chia theo đoạn văn trước
    paragraphs = text.split('\n\n')
    current_chunk = ""

    for p in paragraphs:
        if len(current_chunk) + len(p) + 2 <= max_chars:
            current_chunk += (p + '\n\n')
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # Nếu bản thân đoạn văn quá dài, chia theo câu
            if len(p) > max_chars:
                sentences = re.split(r'(?<=[.!?])\s+', p)
                sub_chunk = ""
                for s in sentences:
                    if len(sub_chunk) + len(s) + 1 <= max_chars:
                        sub_chunk += (s + ' ')
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk.strip())
                        sub_chunk = s + ' '
                current_chunk = sub_chunk
            else:
                current_chunk = p + '\n\n'
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def _offset_srt(srt_content: str, offset_seconds: float) -> str:
    """Cộng thêm offset vào tất cả timestamp trong file SRT."""
    if offset_seconds <= 0:
        return srt_content

    def _add_offset(match):
        h, m, s, ms = map(int, match.groups())
        total_ms = (h * 3600 + m * 60 + s) * 1000 + ms
        new_ms = total_ms + int(offset_seconds * 1000)
        
        nh = new_ms // 3600000
        new_ms %= 3600000
        nm = new_ms // 60000
        new_ms %= 60000
        ns = new_ms // 1000
        nms = new_ms % 1000
        return f"{nh:02}:{nm:02}:{ns:02},{nms:03}"

    pattern = r"(\d{2}):(\d{2}):(\d{2}),(\d{3})"
    return re.sub(pattern, _add_offset, srt_content)


async def _generate_audio_chunk(text: str, voice: str, rate: str, pitch: str, retries: int = 3) -> tuple[bytes, str]:
    """Tạo audio và phụ đề cho một đoạn văn bản với cơ chế retry."""
    for attempt in range(retries):
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            submaker = edge_tts.SubMaker()
            audio_data = bytearray()
            
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.extend(chunk["data"])
                elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                    submaker.feed(chunk)
            
            if not audio_data:
                raise RuntimeError("Không nhận được dữ liệu audio từ server.")
                
            return bytes(audio_data), submaker.get_srt()
        except Exception as e:
            if attempt < retries - 1:
                wait_time = 2 * (attempt + 1)
                logger.warning(f"Lỗi TTS chunk (lần {attempt+1}): {e}. Thử lại sau {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise e


async def _generate_audio_async(text: str, output_path: str, voice: str, rate: str, pitch: str):
    """Chia nhỏ text và tạo audio toàn bộ."""
    chunks = _split_text_into_chunks(text)
    full_audio = bytearray()
    full_srt = ""
    cumulative_duration = 0.0
    
    vtt_path = str(output_path).rsplit(".", 1)[0] + ".srt"
    
    for i, chunk_text in enumerate(chunks):
        if len(chunks) > 1:
            logger.info(f"Đang xử lý TTS đoạn {i+1}/{len(chunks)}...")
        
        audio_chunk, srt_chunk = await _generate_audio_chunk(chunk_text, voice, rate, pitch)
        
        # Offset SRT
        offset_srt_content = _offset_srt(srt_chunk, cumulative_duration)
        full_srt += offset_srt_content + "\n"
        
        # Lưu vào buffer tổng
        full_audio.extend(audio_chunk)
        
        # Cập nhật thời lượng (ước tính hoặc chính xác)
        # Để chính xác hơn, ta nên dùng moviepy đọc chunk hoặc lấy từ SRT cuối cùng
        # Cách nhanh nhất là lấy timestamp cuối cùng của SRT vừa tạo
        times = re.findall(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", srt_chunk)
        if times:
            h, m, s, ms = map(int, times[-1])
            duration = h * 3600 + m * 60 + s + ms / 1000.0
            cumulative_duration += duration
    
    # Ghi file tổng
    with open(output_path, "wb") as f:
        f.write(full_audio)
        
    with open(vtt_path, "w", encoding="utf-8") as f:
        # Chuẩn hóa số thứ tự trong SRT tổng
        lines = full_srt.strip().split('\n')
        normalized_srt = ""
        index = 1
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if re.match(r'^\d+$', line):
                normalized_srt += f"{index}\n"
                index += 1
                i += 1
            else:
                normalized_srt += f"{lines[i]}\n"
                i += 1
        f.write(normalized_srt)


def text_to_speech(
    script: str,
    output_path: str | Path,
    voice: str   = "en-US-GuyNeural",
    rate: str    = "-5%",
    pitch: str   = "+0Hz"
) -> str:
    """
    Chuyển script thành file audio MP3 với cơ chế fallback voice.
    """
    output_path = str(output_path)
    clean_text = _clean_script_for_tts(script)

    if not clean_text.strip():
        raise ValueError("Script rỗng sau khi làm sạch!")

    word_count = len(clean_text.split())
    logger.info(f"TTS: {word_count} từ, giọng: {voice}, tốc độ: {rate}")

    # Danh sách giọng fallback
    # Nếu là Andrew (Multilingual), fallback về Guy (Standard Male)
    # Nếu là Aria (Standard Female), fallback về Sonia (GB-Female)
    fallback_voices = [voice]
    if "Andrew" in voice:
        fallback_voices.append("en-US-GuyNeural")
    elif "Aria" in voice:
        fallback_voices.append("en-GB-SoniaNeural")
    
    # Thêm một giọng cực kỳ ổn định cuối cùng
    if "en-US-GuyNeural" not in fallback_voices:
        fallback_voices.append("en-US-GuyNeural")

    success = False
    last_error = None
    
    for current_voice in fallback_voices:
        try:
            if current_voice != voice:
                logger.info(f"🔄 Đang thử giọng fallback: {current_voice}")
                
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    _generate_audio_async(clean_text, output_path, current_voice, rate, pitch)
                )
            finally:
                loop.close()
                
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                success = True
                break
        except Exception as e:
            last_error = e
            logger.warning(f"Giọng {current_voice} thất bại: {e}")
            if os.path.exists(output_path):
                os.remove(output_path)  # Xóa file rác/lỗi

    if not success:
        raise RuntimeError(f"Tất cả các giọng TTS đều thất bại. Lỗi cuối: {last_error}")

    size_kb = os.path.getsize(output_path) / 1024
    logger.info(f"Audio đã tạo: {output_path} ({size_kb:.1f} KB)")
    return output_path
    return output_path


def get_audio_duration(audio_path: str | Path) -> float:
    """
    Lấy thời lượng file audio (giây).
    Dùng moviepy để đọc duration.
    """
    try:
        from moviepy import AudioFileClip
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
