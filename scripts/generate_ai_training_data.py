"""
AI 学术段落批量生成脚本

调用大模型 API 批量生成中文学术论文段落，作为 AIGC 检测模型的训练数据。

支持的 API：
  - OpenAI 兼容接口（DeepSeek、Kimi、通义千问、本地 Ollama 等）
  - 默认使用 DeepSeek

用法:
    1. 设置环境变量:
       set AI_GEN_API_KEY=你的API密钥
       set AI_GEN_BASE_URL=https://api.deepseek.com/v1    (可选，默认 DeepSeek)
       set AI_GEN_MODEL=deepseek-chat                      (可选)

    2. 运行:
       python scripts/generate_ai_training_data.py

    3. 生成结果保存到 data/training/ai.jsonl

可选参数:
    --count         生成段落数量 (默认 500)
    --output        输出文件路径 (默认 data/training/ai.jsonl)
    --model         模型名称
    --base-url      API 地址
    --api-key       API 密钥 (也可用环境变量)
    --subjects      指定学科列表，逗号分隔
    --delay         请求间隔秒数 (默认 0.5)
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# 学术场景 prompt 模板
# ---------------------------------------------------------------------------

SUBJECTS = [
    "教育学", "心理学", "计算机科学", "经济学", "管理学",
    "法学", "文学", "历史学", "社会学", "新闻传播学",
    "马克思主义理论", "公共管理", "工商管理", "环境科学",
    "机械工程", "土木工程", "电子信息", "护理学", "药学",
]

SECTION_TYPES = [
    ("摘要", "写一段学术论文的摘要"),
    ("引言/绪论", "写一段学术论文的引言或绪论"),
    ("文献综述", "写一段学术论文的文献综述"),
    ("研究方法", "写一段学术论文的研究方法描述"),
    ("数据分析", "写一段学术论文的数据分析与结果"),
    ("讨论", "写一段学术论文的讨论部分"),
    ("结论", "写一段学术论文的结论"),
    ("正文论述", "写一段学术论文的正文论述"),
]

DEGREE_LEVELS = ["本科毕业论文", "硕士学位论文", "博士学位论文", "期刊论文"]

STYLE_VARIANTS = [
    "直接输出段落正文，不要标题，不要编号。",
    "直接输出段落正文，语言应严谨学术化。",
    "直接输出段落正文，适当使用专业术语。",
    "直接输出段落正文，段落 200-500 字左右。",
    "直接输出段落正文，逻辑层次分明。",
]


def build_prompt() -> str:
    """随机组合一个生成 prompt。"""
    subject = random.choice(SUBJECTS)
    section_name, section_instruction = random.choice(SECTION_TYPES)
    degree = random.choice(DEGREE_LEVELS)
    style = random.choice(STYLE_VARIANTS)

    # 部分请求加入具体研究主题，使生成内容更多样
    topic_hints = [
        "",
        f"研究主题可以是{subject}领域中的任意具体问题。",
        f"可以围绕{subject}中某个具体现象或案例展开。",
        f"内容应该涉及{subject}的前沿议题或经典问题。",
    ]
    topic = random.choice(topic_hints)

    return (
        f"你是一名中国高校的{subject}专业学生，正在写{degree}。\n"
        f"请{section_instruction}（{section_name}部分）。\n"
        f"{topic}\n"
        f"{style}\n"
        f"字数要求：200-500字。"
    )


# ---------------------------------------------------------------------------
# API 调用
# ---------------------------------------------------------------------------

def call_api(
    prompt: str,
    *,
    base_url: str,
    api_key: str,
    model: str,
) -> str | None:
    """调用 OpenAI 兼容接口生成文本。"""
    try:
        import httpx
    except ImportError:
        print("需要 httpx 库: pip install httpx")
        sys.exit(1)

    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个学术写作助手，只输出论文段落正文，不要输出任何标题、编号或额外说明。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": random.uniform(0.7, 1.0),
        "max_tokens": 800,
    }

    try:
        # 本地 Ollama 不走系统代理，远程 API 用默认代理
        is_local = "127.0.0.1" in base_url or "localhost" in base_url
        transport = None
        if is_local:
            transport = httpx.HTTPTransport(proxy=None)

        timeout = httpx.Timeout(connect=10, read=180, write=30, pool=10)
        with httpx.Client(timeout=timeout, transport=transport) as client:
            response = client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            return content if len(content) >= 80 else None
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        print(f"  API 调用失败: {exc}")
        return None


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="批量生成 AI 学术段落训练数据")
    parser.add_argument("--count", type=int, default=500, help="生成段落数量")
    parser.add_argument("--output", default="data/training/ai.jsonl", help="输出文件路径")
    parser.add_argument("--model", default=None, help="模型名称")
    parser.add_argument("--base-url", default=None, help="API 地址")
    parser.add_argument("--api-key", default=None, help="API 密钥")
    parser.add_argument("--subjects", default=None, help="指定学科，逗号分隔")
    parser.add_argument("--delay", type=float, default=0.5, help="请求间隔秒数")
    args = parser.parse_args()

    api_key = (args.api_key or os.environ.get("AI_GEN_API_KEY", "")).strip()
    base_url = (args.base_url or os.environ.get("AI_GEN_BASE_URL", "https://api.deepseek.com/v1")).strip()
    model = (args.model or os.environ.get("AI_GEN_MODEL", "deepseek-chat")).strip()

    # 本地 Ollama 不需要 API key
    is_local = "127.0.0.1" in base_url or "localhost" in base_url
    if not api_key and not is_local:
        print("错误: 未设置 API 密钥")
        print("请设置环境变量 AI_GEN_API_KEY 或使用 --api-key 参数")
        print()
        print("支持的 API 服务:")
        print("  DeepSeek:  https://api.deepseek.com/v1")
        print("  Kimi:      https://api.moonshot.cn/v1")
        print("  通义千问:  https://dashscope.aliyuncs.com/compatible-mode/v1")
        print("  Ollama:    http://localhost:11434/v1  (本地，无需 API key)")
        sys.exit(1)

    if args.subjects:
        global SUBJECTS
        SUBJECTS = [s.strip() for s in args.subjects.split(",") if s.strip()]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 如果文件已存在，追加模式（可以分多次跑）
    existing_count = 0
    if output_path.exists():
        existing_count = sum(1 for line in output_path.read_text(encoding="utf-8").splitlines() if line.strip())
        print(f"已有数据: {existing_count} 条，本次追加生成")

    print("=" * 60)
    print("AI 学术段落批量生成")
    print("=" * 60)
    print(f"  API:     {base_url}")
    print(f"  模型:    {model}")
    print(f"  目标:    {args.count} 条")
    print(f"  输出:    {output_path}")
    print(f"  学科:    {', '.join(SUBJECTS[:5])}{'...' if len(SUBJECTS) > 5 else ''}")
    print("=" * 60)
    print()

    success = 0
    failed = 0
    consecutive_failures = 0

    with output_path.open("a", encoding="utf-8") as fh:
        for i in range(args.count):
            prompt = build_prompt()
            print(f"  [{i + 1}/{args.count}] 生成中...", end=" ", flush=True)

            content = call_api(prompt, base_url=base_url, api_key=api_key, model=model)

            if content:
                # 清理：去掉可能的标题行、编号等
                lines = content.strip().splitlines()
                # 去掉第一行如果看起来像标题
                if lines and len(lines[0]) < 30 and not lines[0].endswith(("。", "！", "？", "；")):
                    lines = lines[1:]
                clean_text = "\n".join(lines).strip()

                if len(clean_text) >= 80:
                    record = {
                        "text": clean_text,
                        "source": f"{model}",
                        "prompt_hash": hash(prompt) % (10**8),
                    }
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                    fh.flush()
                    success += 1
                    consecutive_failures = 0
                    print(f"OK ({len(clean_text)} 字)")
                else:
                    failed += 1
                    consecutive_failures += 1
                    print(f"太短 ({len(clean_text)} 字)，跳过")
            else:
                failed += 1
                consecutive_failures += 1
                print("失败")

            # 连续失败 10 次自动停止，避免空跑
            if consecutive_failures >= 10:
                print()
                print(f"  连续失败 {consecutive_failures} 次，自动停止。")
                print(f"  请检查: 1)API服务是否正常  2)密钥是否正确  3)模型名是否存在")
                break

            if args.delay > 0:
                time.sleep(args.delay)

    print()
    print("=" * 60)
    print(f"完成: 成功 {success}, 失败 {failed}")
    print(f"累计数据: {existing_count + success} 条")
    print(f"文件: {output_path.resolve()}")

    if existing_count + success >= 500:
        print()
        print("数据量已达标，可以配合人类数据开始训练:")
        print("  python scripts/train_aigc_model.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
