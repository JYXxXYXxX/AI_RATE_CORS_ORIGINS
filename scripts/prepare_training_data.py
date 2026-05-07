"""
训练数据准备工具

从论文文件批量提取段落，生成训练数据。

用法:
    1. 把人类写的论文放到 data/training/raw/human/ 目录
    2. 把 AI 生成的论文放到 data/training/raw/ai/ 目录
    3. 运行:
       python scripts/prepare_training_data.py

    支持格式: .txt, .md, .docx, .pdf

输出:
    data/training/human.jsonl
    data/training/ai.jsonl
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# 把项目根目录加入 path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings
from app.services.document_loader import extract_text
from app.services.text_processing import clean_body_text, segment_document


SUPPORTED = (".txt", ".md", ".docx", ".pdf")


def extract_segments(file_path: Path, settings: Settings) -> list[str]:
    """从一个文件中提取所有可用段落。"""
    content = file_path.read_bytes()
    try:
        raw_text = extract_text(file_path.name, content)
    except ValueError as exc:
        print(f"  跳过 {file_path.name}: {exc}")
        return []

    cleaned = clean_body_text(raw_text)
    if not cleaned.strip():
        print(f"  跳过 {file_path.name}: 提取正文为空")
        return []

    segments = segment_document(cleaned, settings)
    return [seg.text for seg in segments if len(seg.text) >= 40]


def process_directory(
    input_dir: Path, output_file: Path, label: str, settings: Settings
) -> int:
    """处理一个目录下所有文件，输出到 jsonl。"""
    if not input_dir.exists():
        print(f"目录不存在: {input_dir}，跳过")
        return 0

    files = [
        f for f in input_dir.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED
    ]
    if not files:
        print(f"目录 {input_dir} 下没有找到支持的文件")
        return 0

    total = 0
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as fh:
        for file_path in sorted(files):
            print(f"  处理 {file_path.name} ...", end=" ")
            segments = extract_segments(file_path, settings)
            for seg_text in segments:
                fh.write(
                    json.dumps(
                        {"text": seg_text, "source": file_path.name}, ensure_ascii=False
                    )
                    + "\n"
                )
                total += 1
            print(f"{len(segments)} 段")

    print(f"  [{label}] 共 {total} 段 -> {output_file}")
    return total


def main() -> None:
    settings = Settings()
    raw_dir = Path("data/training/raw")
    out_dir = Path("data/training")

    print("=" * 60)
    print("训练数据准备")
    print("=" * 60)
    print(f"输入目录: {raw_dir.resolve()}")
    print(f"输出目录: {out_dir.resolve()}")
    print()

    if not raw_dir.exists():
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / "human").mkdir(exist_ok=True)
        (raw_dir / "ai").mkdir(exist_ok=True)
        print("已创建目录结构:")
        print(f"  {raw_dir / 'human'}/  <- 放入人类写的论文")
        print(f"  {raw_dir / 'ai'}/     <- 放入 AI 生成的论文")
        print()
        print("请放入文件后重新运行此脚本。")
        return

    print("[1/2] 处理人类论文...")
    human_count = process_directory(
        raw_dir / "human", out_dir / "human.jsonl", "human", settings
    )
    print()

    print("[2/2] 处理 AI 生成论文...")
    ai_count = process_directory(raw_dir / "ai", out_dir / "ai.jsonl", "ai", settings)
    print()

    print("=" * 60)
    print(f"数据准备完成: human={human_count}, ai={ai_count}")
    if human_count >= 500 and ai_count >= 500:
        print("数据量充足，可以开始训练:")
        print("  python scripts/train_aigc_model.py")
    elif human_count >= 100 and ai_count >= 100:
        print("数据量勉强可用，建议补充更多样本以提升效果。")
        print("  python scripts/train_aigc_model.py")
    else:
        print("数据量不足，建议至少准备 500+ 人类段落和 500+ AI 段落。")
    print("=" * 60)


if __name__ == "__main__":
    main()
