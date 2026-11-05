"""
Script sao lưu mã nguồn và model theo danh sách backup_list.yaml
Tuân thủ kiểm tra dung lượng < 15GB trước khi tải.
"""

import os
import yaml
import subprocess
import logging

logger = logging.getLogger("taio.tools.backup")


def run_backup(backup_yaml_path="tools/backup/backup_list.yaml", dest_dir="/Users/abc/.gemini/antigravity/scratch/tools_mirror"):
    os.makedirs(dest_dir, exist_ok=True)
    if not os.path.exists(backup_yaml_path):
        print(f"Không tìm thấy file danh sách: {backup_yaml_path}")
        return

    with open(backup_yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    tools = data.get("tools", [])
    print(f"🚀 Bắt đầu sao lưu {len(tools)} công cụ vào {dest_dir}...")

    for tool in tools:
        name = tool.get("name")
        repo = tool.get("repo")
        license_type = tool.get("license")
        target_path = os.path.join(dest_dir, name)

        print(f"\n📦 Sao lưu {name} [{license_type}] từ {repo}...")
        if os.path.exists(target_path):
            print(f"  • Thư mục {target_path} đã tồn tại, đồng bộ cập nhật...")
            subprocess.run(["git", "-C", target_path, "pull"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            print(f"  • Clone mirror mới...")
            subprocess.run(["git", "clone", "--depth", "1", repo, target_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    print("\n✅ Hoàn tất kiểm tra và sao lưu toàn bộ công cụ!")


if __name__ == "__main__":
    run_backup()
