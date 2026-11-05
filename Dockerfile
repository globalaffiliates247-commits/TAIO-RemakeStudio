FROM python:3.11-slim

# Cài đặt ffmpeg cho xử lý video/audio và curl để kiểm tra health check
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg nodejs ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cài đặt các thư viện Python
COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

# Sao chép toàn bộ mã nguồn vào container
COPY . .

# Khởi tạo các thư mục dữ liệu
RUN mkdir -p data/uploads data/outputs

# Môi trường chạy mặc định trên Render
ENV PORT=10000
EXPOSE 10000

# Health check cho Render
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

# Khởi chạy máy chủ ứng dụng
CMD ["python", "main.py"]
