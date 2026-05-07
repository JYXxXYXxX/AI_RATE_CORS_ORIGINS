"""将 CSL 本地数据转换为 human.jsonl 训练数据。"""

import json
import os

MIN_LENGTH = 80  # 最短字符数
OUTPUT = "data/training/human.jsonl"
CSL_BASE = "CSL/benchmark"

# 优先用 cls_dcp（有完整摘要），再补充其他子集
SOURCES = [
    ("cls_dcp", "train.tsv"),
    ("cls_dcp", "dev.tsv"),
    ("cls_dcp", "test.tsv"),
    ("ts", "train.tsv"),
    ("ts", "dev.tsv"),
    ("ts", "test.tsv"),
    ("kg", "train.tsv"),
    ("kg", "dev.tsv"),
    ("kg", "test.tsv"),
    ("cls_ctg", "train.tsv"),
    ("cls_ctg", "dev.tsv"),
    ("cls_ctg", "test.tsv"),
]

seen = set()
samples = []

for sub, name in SOURCES:
    path = os.path.join(CSL_BASE, sub, name)
    if not os.path.exists(path):
        continue
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 2:
                continue
            text = parts[1].strip()
            if len(text) < MIN_LENGTH:
                continue
            # 检查中文比例
            cn = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
            if cn < len(text) * 0.3:
                continue
            # 去重
            key = text[:100]
            if key in seen:
                continue
            seen.add(key)
            samples.append({"text": text, "source": f"CSL/{sub}/{name}"})

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as f:
    for s in samples:
        f.write(json.dumps(s, ensure_ascii=False) + "\n")

print(f"转换完成: {len(samples)} 条人类学术文本 -> {OUTPUT}")
