"""
AIGC 检测模型训练脚本

使用 chinese-roberta-wwm-ext 微调段落级二分类（human=0 / AI=1）。

用法:
    1. 准备数据目录 data/training/，结构如下:
       data/training/
       ├── human.jsonl   # 每行 {"text": "..."}
       └── ai.jsonl      # 每行 {"text": "..."}

       也支持纯文本格式（每行一条段落）:
       data/training/
       ├── human.txt
       └── ai.txt

    2. 运行训练:
       python scripts/train_aigc_model.py

    3. 训练完成后模型自动保存到 data/models/aigc-detector/
       服务重启后 LocalTransformerDetector 会自动加载。

可选参数:
    --model-name    底座模型 (默认 hfl/chinese-roberta-wwm-ext)
    --epochs        训练轮数 (默认 5)
    --batch-size    批大小 (默认 16)
    --lr            学习率 (默认 2e-5)
    --max-length    最大 token 长度 (默认 512)
    --output-dir    模型输出目录 (默认 data/models/aigc-detector)
    --data-dir      训练数据目录 (默认 data/training)
    --eval-split    验证集比例 (默认 0.15)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------


def load_samples(data_dir: str) -> tuple[list[str], list[int]]:
    """从 data_dir 加载训练数据，返回 (texts, labels)。"""
    data_path = Path(data_dir)
    texts: list[str] = []
    labels: list[int] = []

    # 支持 jsonl 格式
    human_jsonl = data_path / "human.jsonl"
    ai_jsonl = data_path / "ai.jsonl"
    # 支持纯文本格式
    human_txt = data_path / "human.txt"
    ai_txt = data_path / "ai.txt"

    human_count = 0
    ai_count = 0

    for source, label in [(human_jsonl, 0), (ai_jsonl, 1)]:
        if source.exists():
            for line in source.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    text = record.get("text", "").strip()
                except (json.JSONDecodeError, AttributeError):
                    text = line.strip()
                if len(text) >= 40:
                    texts.append(text)
                    labels.append(label)
                    if label == 0:
                        human_count += 1
                    else:
                        ai_count += 1

    for source, label in [(human_txt, 0), (ai_txt, 1)]:
        if source.exists():
            for line in source.read_text(encoding="utf-8").splitlines():
                text = line.strip()
                if len(text) >= 40:
                    texts.append(text)
                    labels.append(label)
                    if label == 0:
                        human_count += 1
                    else:
                        ai_count += 1

    print(f"数据加载完成: human={human_count}, ai={ai_count}, total={len(texts)}")
    return texts, labels


# ---------------------------------------------------------------------------
# 训练
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="训练 AIGC 段落级二分类模型")
    parser.add_argument(
        "--model-name",
        default="hfl/chinese-roberta-wwm-ext",
        help="HuggingFace 底座模型",
    )
    parser.add_argument("--epochs", type=int, default=5, help="训练轮数")
    parser.add_argument("--batch-size", type=int, default=16, help="批大小")
    parser.add_argument("--lr", type=float, default=2e-5, help="学习率")
    parser.add_argument("--max-length", type=int, default=512, help="最大 token 长度")
    parser.add_argument(
        "--output-dir", default="data/models/aigc-detector", help="模型输出目录"
    )
    parser.add_argument("--data-dir", default="data/training", help="训练数据目录")
    parser.add_argument("--eval-split", type=float, default=0.15, help="验证集比例")
    args = parser.parse_args()

    # 检查依赖
    try:
        import torch  # noqa: F401
        from transformers import (  # noqa: F401
            AutoTokenizer,
            AutoModelForSequenceClassification,
            Trainer,
            TrainingArguments,
        )
        from datasets import Dataset  # noqa: F401
        from sklearn.metrics import accuracy_score, precision_recall_fscore_support  # noqa: F401
    except ImportError as exc:
        print(f"缺少依赖: {exc}")
        print("请运行: pip install torch transformers datasets scikit-learn")
        sys.exit(1)

    import torch
    from transformers import (
        AutoTokenizer,
        AutoModelForSequenceClassification,
        Trainer,
        TrainingArguments,
    )
    from datasets import Dataset
    import datasets
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support
    import numpy as np

    # 加载数据
    texts, labels = load_samples(args.data_dir)
    if len(texts) < 100:
        print(
            f"训练数据不足 ({len(texts)} 条)，建议至少准备 1000 条 human + 1000 条 AI 段落。"
        )
        if len(texts) < 20:
            print("数据量太少，无法训练。")
            sys.exit(1)

    # 构建 Dataset
    dataset = Dataset.from_dict({"text": texts, "label": labels})
    dataset = dataset.cast_column(
        "label", datasets.ClassLabel(names=["human", "ai_generated"])
    )
    dataset = dataset.shuffle(seed=42)
    split = dataset.train_test_split(
        test_size=args.eval_split, seed=42, stratify_by_column="label"
    )
    train_dataset = split["train"]
    eval_dataset = split["test"]
    print(f"训练集: {len(train_dataset)}, 验证集: {len(eval_dataset)}")

    # 加载 tokenizer 和模型
    print(f"加载底座模型: {args.model_name}")
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=2,
        id2label={0: "human", 1: "ai_generated"},
        label2id={"human": 0, "ai_generated": 1},
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"训练设备: {device}")

    # Tokenize
    def tokenize_fn(examples: dict) -> dict:
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=args.max_length,
            padding="max_length",
        )

    train_dataset = train_dataset.map(
        tokenize_fn, batched=True, remove_columns=["text"]
    )
    eval_dataset = eval_dataset.map(tokenize_fn, batched=True, remove_columns=["text"])
    train_dataset.set_format("torch")
    eval_dataset.set_format("torch")

    # 评估函数
    def compute_metrics(eval_pred: tuple) -> dict:
        logits, labels_arr = eval_pred
        predictions = np.argmax(logits, axis=-1)
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels_arr, predictions, average="binary", pos_label=1
        )
        acc = accuracy_score(labels_arr, predictions)
        return {
            "accuracy": round(acc, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    # 训练参数
    output_dir = args.output_dir
    training_args = TrainingArguments(
        output_dir=output_dir + "/checkpoints",
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        learning_rate=args.lr,
        weight_decay=0.01,
        warmup_ratio=0.1,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        greater_is_better=True,
        logging_steps=50,
        fp16=torch.cuda.is_available(),
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        compute_metrics=compute_metrics,
    )

    # 开始训练
    print("=" * 60)
    print("开始训练")
    print("=" * 60)
    trainer.train()

    # 评估
    print("=" * 60)
    print("最终评估")
    print("=" * 60)
    metrics = trainer.evaluate()
    for key, value in metrics.items():
        print(f"  {key}: {value}")

    # 保存最终模型
    final_dir = Path(output_dir)
    final_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    print(f"\n模型已保存到: {final_dir.resolve()}")
    print("服务重启后 LocalTransformerDetector 将自动加载该模型。")

    # 保存训练元信息
    meta = {
        "base_model": args.model_name,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.lr,
        "max_length": args.max_length,
        "train_samples": len(split["train"]),
        "eval_samples": len(split["test"]),
        "eval_metrics": {
            k: v for k, v in metrics.items() if isinstance(v, (int, float))
        },
    }
    meta_path = final_dir / "training_meta.json"
    meta_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"训练元信息已保存到: {meta_path}")


if __name__ == "__main__":
    main()
