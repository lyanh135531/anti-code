# Kế hoạch Nâng cấp Hệ thống YouTube Automation

Để tăng lượt xem (Views) và người đăng ký (Subscribers), chúng ta cần tập trung vào 3 yếu tố then chốt: **CTR (Tỷ lệ nhấp)**, **Retention (Tỷ lệ giữ chân)** và **Conversion (Chuyển đổi sub)**. Dưới đây là các nâng cấp đề xuất cho mã nguồn.

## User Review Required

> [!IMPORTANT]
> **API Costs**: Việc nâng cấp giọng nói lên ElevenLabs hoặc OpenAI TTS sẽ làm phát sinh chi phí hàng tháng thay vì miễn phí như Edge TTS hiện tại. Bạn có sẵn sàng đầu tư cho chất lượng "Premium" không?

> [!NOTE]
> **Rendering Time**: Thêm các hiệu ứng chuyển cảnh và hiệu ứng cinematic (Ken Burns) sẽ tăng thời gian render video (có thể tăng gấp 2-3 lần).

## Proposed Changes

### 1. Nâng cấp Chất lượng Âm thanh (Retention)
Thay thế `edge-tts` (giọng robot ổn nhưng chưa có cảm xúc) bằng các giải pháp cao cấp hơn.

#### [MODIFY] [tts.py](file:///c:/Project/anti-code/youtube-auto/modules/tts.py)
*   Tích hợp ElevenLabs API hoặc OpenAI Audio API.
*   Bổ sung tính năng tự động điều chỉnh biểu cảm (stability, clarity) dựa trên ngữ cảnh script.

### 2. Nâng cấp Visual & Video Effects (Retention)
Video hiện tại chủ yếu dùng ảnh tĩnh. Cần làm video "sống" hơn.

#### [MODIFY] [video_maker.py](file:///c:/Project/anti-code/youtube-auto/modules/video_maker.py)
*   **Ken Burns Effect**: Tự động zoom-in/zoom-out và lia máy nhẹ trên các bức ảnh để tạo cảm giác chuyển động.
*   **Animated Captions**: Hiển thị phụ đề kiểu "Talking Heads" (từng từ hoặc cụm từ nổi bật) ở giữa màn hình thay vì fix ở dưới.
*   **Background Music Dynamics**: Tự động thay đổi nhạc nền theo tâm trạng (mood) của từng phân đoạn script.

### 3. Nâng cấp Thumbnail (CTR)
Thumbnail hiện tại dùng Pillow vẽ đè text lên ảnh. Cần sự chuyên nghiệp và "clickbait" hơn một chút theo hướng nghệ thuật.

#### [MODIFY] [thumbnail_maker.py](file:///c:/Project/anti-code/youtube-auto/modules/thumbnail_maker.py)
*   **AI Visual Generation**: Dùng Gemini (Image Generation) hoặc Stable Diffusion để tạo ảnh nền độc bản, cực kỳ ấn tượng thay vì search ảnh trên mạng.
*   **Glow & Contrast**: Thêm hiệu ứng phát sáng (glow) quanh đối tượng chính và tăng độ tương phản màu sắc cực đại.

### 4. Nâng cấp Script & Engagement (Subscribers)
Prompt hiện tại chưa tập trung mạnh vào việc giữ chân và yêu cầu sub.

#### [MODIFY] [script_gen.py](file:///c:/Project/anti-code/youtube-auto/modules/script_gen.py)
*   **The 3-Second Hook**: Ép Gemini tạo ra 3-5 variants của câu mở đầu cực kỳ gây tò mò.
*   **Dynamic CTA**: Tự động chèn lời kêu gọi đăng ký (CTA) vào đúng thời điểm Retention cao nhất (thường là phút thứ 2 hoặc ngay sau một ý quan trọng).

### 5. Nâng cấp SEO & Trend Discovery (Reach)
Hiện tại hệ thống chỉ tự brainstorm ý tưởng. Cần bắt kịp xu hướng.

#### [MODIFY] [idea_gen.py](file:///c:/Project/anti-code/youtube-auto/modules/idea_gen.py)
*   **Google Trends Integration**: Fetch các từ khóa đang hot trong ngách tôn giáo/triết học để Gemini dựa vào đó lên bài.
*   **Competitor Analysis Pattern**: Nhập link các video hot nhất trong ngách để AI phân tích và đề xuất "phản biện" hoặc "mở rộng" nội dung đó.

## Open Questions

1.  **Budget**: Bạn ưu tiên giải pháp miễn phí/rẻ (tiếp tục dùng Edge TTS, Google Search Image) hay giải pháp trả phí để đạt chất lượng top-tier (ElevenLabs, Midjourney/DALL-E)?
2.  **Rendering**: Bạn đang chạy server mạnh không? Nếu thêm hiệu ứng cinematic thì MoviePy sẽ tốn nhiều CPU/RAM hơn.
3.  **Language**: Bạn có muốn mở rộng kênh sang các ngôn ngữ khác (Anh, Tây Ban Nha) để tận dụng thị trường toàn cầu không?

## Verification Plan

### Manual Verification
*   Kiểm tra chất lượng giọng nói mới (ElevenLabs/OpenAI) so với Edge TTS.
*   Render video thử nghiệm để xem hiệu ứng zoom và animated captions có mượt không.
*   So sánh Thumbnail cũ vs Thumbnail mới (AI generated) về mức độ ấn tượng.
