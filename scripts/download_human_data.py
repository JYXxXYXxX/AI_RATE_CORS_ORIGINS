"""
公开学术数据集下载与转换脚本

从 HuggingFace 公开数据集批量获取中文学术论文摘要/段落，
转换为训练数据格式 (data/training/human.jsonl)。

数据来源 (全部公开合规):
  1. CSL (Chinese Scientific Literature) - 39.6万篇中文论文摘要
  2. CNewSum / LCSTS - 中文文本摘要数据集

用法:
    pip install datasets
    python scripts/download_human_data.py

可选参数:
    --count       需要的段落数量 (默认 2000)
    --output      输出文件路径 (默认 data/training/human.jsonl)
    --min-length  最短字符数 (默认 80)
    --source      数据源: csl / all (默认 csl)
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path


def download_csl(count: int, min_length: int) -> list[dict[str, str]]:
    """从 CSL (Chinese Scientific Literature) 下载论文摘要。

    CSL 包含 39.6 万篇中文学术论文的标题、摘要、关键词、学科分类。
    来源: COLING 2022 论文，公开数据集。
    """
    try:
        from datasets import load_dataset
    except ImportError:
        print("需要安装 datasets: pip install datasets")
        sys.exit(1)

    print("正在从 HuggingFace 下载 CSL 数据集...")
    print("(首次下载约 200MB，会自动缓存)")
    print()

    try:
        ds = load_dataset("neuclir/csl", split="train")
    except Exception:
        # 备选路径
        try:
            ds = load_dataset("ydshieh/csl", split="train")
        except Exception as exc:
            print(f"CSL 数据集下载失败: {exc}")
            print("请检查网络连接，或尝试使用代理。")
            return []

    print(f"CSL 数据集加载成功: {len(ds)} 条记录")

    samples: list[dict[str, str]] = []
    indices = list(range(len(ds)))
    random.shuffle(indices)

    for idx in indices:
        if len(samples) >= count:
            break

        record = ds[idx]
        abstract = (record.get("abstract") or "").strip()

        if len(abstract) < min_length:
            continue

        # 过滤掉英文为主的摘要
        chinese_chars = sum(1 for ch in abstract if "\u4e00" <= ch <= "\u9fff")
        if chinese_chars < len(abstract) * 0.3:
            continue

        category = record.get("category") or record.get("discipline") or ""
        samples.append({
            "text": abstract,
            "source": "CSL",
            "category": str(category),
            "title": (record.get("title") or "")[:100],
        })

    print(f"  从 CSL 提取了 {len(samples)} 条有效摘要")
    return samples


def download_clc_abstracts(count: int, min_length: int) -> list[dict[str, str]]:
    """尝试从其他公开中文学术数据集获取数据。"""
    try:
        from datasets import load_dataset
    except ImportError:
        return []

    samples: list[dict[str, str]] = []

    # 尝试 CLUE/CLUEWSC 等公开中文数据集中的长文本
    datasets_to_try = [
        ("seamew/CNewSum", "train", "article", "CNewSum"),
        ("ccdv/cnn_dailymail", None, None, None),  # 跳过英文
    ]

    for ds_name, split_name, text_field, source_label in datasets_to_try:
        if not text_field or not source_label:
            continue
        if len(samples) >= count:
            break
        try:
            print(f"  尝试加载 {ds_name}...")
            ds = load_dataset(ds_name, split=split_name or "train")
            indices = list(range(len(ds)))
            random.shuffle(indices)
            added = 0
            for idx in indices:
                if len(samples) >= count or added >= count // 2:
                    break
                text = (ds[idx].get(text_field) or "").strip()
                if len(text) < min_length:
                    continue
                chinese_chars = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
                if chinese_chars < len(text) * 0.3:
                    continue
                # 截取合适长度的段落（200-600字）
                if len(text) > 600:
                    # 随机截取一段
                    start = random.randint(0, len(text) - 400)
                    # 找句子边界
                    end_markers = ["。", "！", "？", "；"]
                    end = start + 400
                    for pos in range(end, min(end + 200, len(text))):
                        if text[pos] in end_markers:
                            end = pos + 1
                            break
                    text = text[start:end].strip()
                if len(text) >= min_length:
                    samples.append({"text": text, "source": source_label})
                    added += 1
            print(f"    从 {ds_name} 提取了 {added} 条")
        except Exception as exc:
            print(f"    {ds_name} 加载失败: {exc}，跳过")
            continue

    return samples


def main() -> None:
    parser = argparse.ArgumentParser(description="下载公开学术数据集作为人类训练数据")
    parser.add_argument("--count", type=int, default=2000, help="需要的段落数量")
    parser.add_argument("--output", default="data/training/human.jsonl", help="输出文件路径")
    parser.add_argument("--min-length", type=int, default=80, help="最短字符数")
    parser.add_argument("--source", default="csl", choices=["csl", "all"], help="数据源")
    args = parser.parse_args()

    print("=" * 60)
    print("公开学术数据集下载")
    print("=" * 60)
    print(f"  目标数量: {args.count}")
    print(f"  输出文件: {args.output}")
    print(f"  数据源:   {args.source}")
    print("=" * 60)
    print()

    all_samples: list[dict[str, str]] = []

    # CSL 是主力数据源
    csl_samples = download_csl(args.count, args.min_length)
    all_samples.extend(csl_samples)

    if args.source == "all" and len(all_samples) < args.count:
        remaining = args.count - len(all_samples)
        extra = download_clc_abstracts(remaining, args.min_length)
        all_samples.extend(extra)

    if not all_samples:
        print()
        print("未获取到任何数据。可能的原因:")
        print("  1. 网络无法访问 HuggingFace（需要科学上网或设置镜像）")
        print()
        print("设置 HuggingFace 国内镜像:")
        print("  set HF_ENDPOINT=https://hf-mirror.com")
        print("  python scripts/download_human_data.py")
        sys.exit(1)

    # 打乱并截取
    random.shuffle(all_samples)
    all_samples = all_samples[:args.count]

    # 写入文件
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        for sample in all_samples:
            fh.write(json.dumps(sample, ensure_ascii=False) + "\n")

    print()
    print("=" * 60)
    print(f"下载完成: {len(all_samples)} 条人类学术段落")
    print(f"文件: {output_path.resolve()}")
    print()

    # 统计
    categories = {}
    for s in all_samples:
        cat = s.get("category", "未分类")
        categories[cat] = categories.get(cat, 0) + 1
    if categories:
        print("学科分布 (前10):")
        for cat, cnt in sorted(categories.items(), key=lambda x: -x[1])[:10]:
            print(f"  {cat}: {cnt}")

    print()
    print("下一步:")
    print("  1. 生成 AI 段落: python scripts/generate_ai_training_data.py --count 500")
    print("  2. 开始训练:     python scripts/train_aigc_model.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
