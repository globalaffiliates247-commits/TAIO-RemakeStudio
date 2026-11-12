#!/bin/bash
# Tạo clip mẫu cho kiểm thử M1 trong tests/fixtures/. Chạy từ thư mục gốc repo:
#   bash scripts/make_test_fixtures.sh
# - en_speech.mp4 : giọng đọc tiếng Anh do macOS tạo bằng lệnh `say` (có sẵn, miễn phí)
# - vi_speech.mp4 : ưu tiên clip Facebook tiếng Việt đã tải trong lần thử trước (data/outputs),
#                   không có thì dùng giọng tiếng Việt "Linh" của macOS (nếu đã tải giọng này)
# - drums_song.mp3: bài nhạc tổng hợp có trống rõ (đã kèm sẵn trong bộ cài)
set -uo pipefail
cd "$(dirname "$0")/.."
OUT=tests/fixtures; mkdir -p "$OUT"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

to_mp4() { # audio_vào, mp4_ra: ghép nền đen khổ dọc để thử được cả Mức 3 (video lồng tiếng)
  ffmpeg -y -loglevel error -f lavfi -i color=c=black:s=720x1280:r=24 -i "$1" \
    -shortest -c:v libx264 -pix_fmt yuv420p -c:a aac -b:a 128k "$2"
}

echo "▶ en_speech.mp4"
cat > "$TMP/en.txt" <<'TXT'
Good morning everyone. Today I want to share three simple habits that help small business owners save time every week.
First, write down your three most important tasks before you open your email.
Second, use a timer and work on one task for twenty five minutes without checking your phone.
Third, at the end of the day, spend five minutes reviewing what you finished and what you will do tomorrow.
These habits sound simple, but if you practice them for one month, you will feel much more in control of your work.
TXT
if say -v Samantha -o "$TMP/en.aiff" -f "$TMP/en.txt" 2>/dev/null || say -o "$TMP/en.aiff" -f "$TMP/en.txt"; then
  to_mp4 "$TMP/en.aiff" "$OUT/en_speech.mp4" && echo "  ✅ $OUT/en_speech.mp4"
else
  echo "  ❌ lệnh say lỗi"
fi

echo "▶ vi_speech.mp4"
FB="$(find data -type f -name 'fb_*.mp3' 2>/dev/null | head -1)"
if [ -n "$FB" ]; then
  ffmpeg -y -loglevel error -t 45 -i "$FB" "$TMP/vi.wav" && to_mp4 "$TMP/vi.wav" "$OUT/vi_speech.mp4" \
    && echo "  ✅ $OUT/vi_speech.mp4 (45 giây đầu của $FB)"
elif say -v '?' | grep -qi 'vi_VN'; then
  VOICE="$(say -v '?' | grep -i 'vi_VN' | head -1 | awk '{print $1}')"
  say -v "$VOICE" -o "$TMP/vi.aiff" "Xin chào các bạn. Hôm nay mình chia sẻ ba thói quen giúp người làm kinh doanh nhỏ tiết kiệm thời gian mỗi tuần. Thứ nhất, viết ra ba việc quan trọng nhất trước khi mở email. Thứ hai, bấm giờ hai mươi lăm phút và chỉ làm một việc. Thứ ba, cuối ngày dành năm phút xem lại những gì đã xong." \
    && to_mp4 "$TMP/vi.aiff" "$OUT/vi_speech.mp4" && echo "  ✅ $OUT/vi_speech.mp4 (giọng $VOICE của macOS)"
else
  echo "  ⚠️  Chưa có clip tiếng Việt. Cách nhanh nhất: thu 30 giây bằng QuickTime hoặc Ghi âm trên iPhone,"
  echo "     lưu thành $OUT/vi_speech.m4a rồi chạy lại script; hoặc tải giọng 'Linh' trong"
  echo "     Cài đặt hệ thống > Trợ năng > Nội dung được đọc > Giọng hệ thống."
  M4A="$(ls "$OUT"/vi_speech.m4a 2>/dev/null | head -1)"
  [ -n "$M4A" ] && to_mp4 "$M4A" "$OUT/vi_speech.mp4" && echo "  ✅ đã chuyển $M4A thành $OUT/vi_speech.mp4"
fi

echo "▶ drums_song.mp3"
[ -f "$OUT/drums_song.mp3" ] && echo "  ✅ $OUT/drums_song.mp3 (nhạc tổng hợp 32 giây, 100 BPM: trống + bass + hợp âm)" \
  || echo "  ⚠️  thiếu $OUT/drums_song.mp3 (có trong bộ cài, giải nén lại)"

echo ""
echo "Kiểm tra thời lượng:"
for f in "$OUT"/*.mp4 "$OUT"/*.mp3; do
  [ -f "$f" ] && printf "  %-32s %s giây\n" "$f" "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")"
done
