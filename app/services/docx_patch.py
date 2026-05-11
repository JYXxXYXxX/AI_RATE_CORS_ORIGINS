"""DOCX Patch 服务。

核心职责：基于原始 docx 母版，精确应用 text patches。
关键改进：通过 paragraphIndex 直接定位段落，而不是模糊字符串匹配。
"""

from __future__ import annotations

import io
from pathlib import Path

from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import qn


RISK_COLORS = {
    "high": "FFCDD2",
    "medium": "FFE0B2",
    "low": "E1BEE7",
    "normal": "C8E6C9",
}


def _set_para_shading(paragraph, color_hex: str) -> None:
    pPr = paragraph._element.get_or_add_pPr()
    shading = parse_xml(
        f'<w:shd xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        f'w:fill="{color_hex}" w:val="clear"/>'
    )
    pPr.append(shading)


def _try_replace_in_runs(paragraph, old_text: str, new_text: str) -> bool:
    """尝试在段落内跨 run 替换文本，保留格式。

    策略：
    1. 收集所有 run 的文本，拼接成完整字符串
    2. 找到 old_text 的位置
    3. 计算跨越了哪些 run
    4. 第一个 run 保留样式并承载 prefix + new_text
    5. 中间 runs 清空
    6. 最后一个 run 承载 suffix
    """
    runs = paragraph.runs
    if not runs:
        return False

    # 收集所有文本和位置映射
    run_texts = []
    total = ""
    for run in runs:
        t = run.text
        run_texts.append(t)
        total += t

    # 查找 old_text
    idx = total.find(old_text)
    if idx == -1:
        return False

    end_idx = idx + len(old_text)

    # 计算 old_text 跨越了哪些 run
    current_pos = 0
    start_run = -1
    end_run = -1
    for i, t in enumerate(run_texts):
        run_start = current_pos
        run_end = current_pos + len(t)
        if start_run == -1 and run_end > idx:
            start_run = i
        if start_run != -1 and run_end >= end_idx:
            end_run = i
            break
        current_pos = run_end

    if start_run == -1 or end_run == -1:
        return False

    # 计算在 start_run 和 end_run 中的偏移
    prefix_len = idx - sum(len(run_texts[j]) for j in range(start_run))
    suffix_len = sum(len(run_texts[j]) for j in range(end_run + 1)) - end_idx

    prefix = run_texts[start_run][:prefix_len]
    suffix = run_texts[end_run][len(run_texts[end_run]) - suffix_len:]

    # 替换
    runs[start_run].text = prefix + new_text + suffix
    for i in range(start_run + 1, end_run + 1):
        runs[i].text = ""

    return True


def _fallback_replace_paragraph(paragraph, new_text: str) -> None:
    """兜底方案：清空所有 runs，用第一个 run 的样式写新文本。"""
    if paragraph.runs:
        paragraph.runs[0].text = new_text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.add_run(new_text)


def export_docx_with_patches(
    original_path: str,
    blocks: list[dict],
    patches: list[dict],
) -> bytes:
    """基于原始 docx 母版，应用 patches 并添加风险背景色。

    Args:
        original_path: 原始 docx 文件路径
        blocks: 文档 blocks 列表，每个 block 包含 block_id, text, risk_score, source_map
        patches: 改写 patches 列表，每个 patch 包含 block_id, old_text, new_text

    Returns:
        docx 文件的字节内容
    """
    path = Path(original_path)
    if not path.exists() or path.suffix.lower() != ".docx":
        raise ValueError("原始 docx 文件不存在")

    doc = Document(original_path)
    patch_map = {p["block_id"]: p for p in patches}

    for block in blocks:
        if block.get("block_type") != "paragraph":
            continue

        patch = patch_map.get(block["block_id"])
        para_idx = block.get("source_map", {}).get("paragraphIndex")
        if para_idx is None or para_idx >= len(doc.paragraphs):
            continue

        para = doc.paragraphs[para_idx]

        # 如果有 patch，替换文本
        if patch:
            old_text = patch["old_text"]
            new_text = patch["new_text"]
            if not _try_replace_in_runs(para, old_text, new_text):
                _fallback_replace_paragraph(para, new_text)

        # 添加风险背景色
        risk_score = block.get("risk_score") or 0
        color = RISK_COLORS["normal"]
        if risk_score >= 70:
            color = RISK_COLORS["high"]
        elif risk_score >= 60:
            color = RISK_COLORS["medium"]
        elif risk_score >= 30:
            color = RISK_COLORS["low"]
        _set_para_shading(para, color)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()
