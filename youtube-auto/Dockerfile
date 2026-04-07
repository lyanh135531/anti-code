FROM python:3.11-slim

# Cài đặt các thư viện hệ thống cần thiết cho moviepy, edge-tts, etc.
RUN apt-get update && \
    apt-get install -y ffmpeg imagemagick fonts-liberation && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Fix lỗi ImageMagick policy chặn convert text và PDF của MoviePy
RUN if [ -f /etc/ImageMagick-6/policy.xml ]; then \
        sed -i 's/rights="none" pattern="PDF"/rights="read|write" pattern="PDF"/' /etc/ImageMagick-6/policy.xml || true; \
        sed -i 's/rights="none" pattern="LABEL"/rights="read|write" pattern="LABEL"/' /etc/ImageMagick-6/policy.xml || true; \
        sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@\*"/' /etc/ImageMagick-6/policy.xml || true; \
    fi

# Thiết lập thư mục làm việc
WORKDIR /app

# Copy và cài đặt thư viện
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Lệnh chạy auto mặc định (scheduler.py)
CMD ["python", "scheduler.py"]
