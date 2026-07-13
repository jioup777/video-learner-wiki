"""artifact 契约校验 CLI: python -m scripts.contract_check <artifact_dir>"""
import sys
import os
import json
from pathlib import Path

# Windows 控制台默认 GBK, 强制 utf-8 避免 emoji/中文输出崩溃
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metadata import validate_metadata, ContractError


def check_artifact(artifact_dir: str) -> bool:
    d = Path(artifact_dir)
    required_files = ["metadata.json", "transcript.txt", "post_caption.txt"]
    # video.mp4 / audio.m4a 尽力,不强制(MVP 抖音可能只有 audio)
    ok = True
    for f in required_files:
        if not (d / f).exists():
            print(f"❌ 缺文件: {f}")
            ok = False
    meta_path = d / "metadata.json"
    if not meta_path.exists():
        return False
    try:
        validate_metadata(json.loads(meta_path.read_text(encoding="utf-8")))
        print("✅ metadata.json 契约通过")
    except ContractError as e:
        print(f"❌ 契约违规: {e}")
        ok = False
    return ok


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python -m scripts.contract_check <artifact_dir>")
        sys.exit(1)
    sys.exit(0 if check_artifact(sys.argv[1]) else 1)
