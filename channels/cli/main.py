"""
TAIO RemakeStudio CLI (Dành cho người dùng Cấp 2)
Chạy trực tiếp từ Terminal trên máy tính cá nhân.
"""

import argparse
import sys
import os
import json

from flows.manager import FlowManager


def main():
    parser = argparse.ArgumentParser(description="TAIO RemakeStudio CLI - Đọc lại, Dịch lại video/âm thanh")
    parser.add_argument("input", help="Link video TikTok/Facebook hoặc đường dẫn file audio/video")
    parser.add_argument("--flow", default="L1", choices=["L1", "L2", "L3", "L4", "L5"], help="Chọn luồng dịch (L1-L5)")
    parser.add_argument("--level", type=int, default=2, choices=[1, 2, 3, 4], help="Mức đầu ra (1: Chữ, 2: Audio, 3: Video, 4: Summary)")
    parser.add_argument("--voice", default="vi_north_female_1", help="ID giọng đọc (xem config/voices.yaml)")
    parser.add_argument("--song-mode", action="store_true", help="Bật chế độ bài hát tách lời & phiên âm")
    parser.add_argument("--output-dir", default="data/outputs/cli_task", help="Thư mục lưu kết quả")

    args = parser.parse_args()

    print("=" * 60)
    print("🚀 TAIO REMAKESTUDIO (Bản Cấp 2 - Local Run)")
    print(f"🎯 Đầu vào: {args.input}")
    print(f"🔄 Luồng: {args.flow} | Mức: {args.level} | Giọng: {args.voice}")
    print("=" * 60)

    manager = FlowManager()
    try:
        res = manager.process(
            input_target=args.input,
            flow_id=args.flow,
            output_dir=args.output_dir,
            options={
                "target_level": args.level,
                "voice_id": args.voice,
                "song_mode": args.song_mode
            }
        )
        print("\n✅ Xử lý hoàn tất thành công!")
        print(f"📁 Thư mục kết quả: {os.path.abspath(args.output_dir)}")
        print("Tệp xuất bản:")
        for k, v in res.get("files", {}).items():
            print(f"  • {k}: {v}")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
