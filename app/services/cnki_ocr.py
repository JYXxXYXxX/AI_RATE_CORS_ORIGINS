from __future__ import annotations

import difflib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.services.document_loader import extract_text


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
TEXT_EXTENSIONS = {".txt", ".md", ".docx", ".pdf"}


def extract_cnki_feedback_preview(filename: str, content: bytes) -> dict[str, Any]:
    suffix = Path(filename).suffix.lower()
    warnings: list[str] = []
    if suffix in TEXT_EXTENSIONS:
        text = extract_text(filename, content)
        engine = "text-extract"
    elif suffix in IMAGE_EXTENSIONS:
        text = _extract_image_text(content, suffix)
        engine = "tesseract"
    else:
        raise ValueError(
            "only pdf, docx, txt, md, png, jpg, jpeg, bmp, tif, tiff, webp are supported"
        )

    normalized_text = _normalize_text(text)

    # 基础字段
    duplication_percent = _extract_percent(
        normalized_text,
        [
            r"(?:总文字复制比|文字复制比|总复制比|重复率|查重率)[^\d]{0,12}(\d{1,3}(?:\.\d+)?)\s*%",
            r"(?:duplication|similarity)[^\d]{0,12}(\d{1,3}(?:\.\d+)?)\s*%",
        ],
    )
    aigc_percent = _extract_percent(
        normalized_text,
        [
            # 知网 AIGC 报告常见格式：AI特征值、AI检测结果、AIGC率等
            r"(?:AIGC|AI特征值|AI检测结果|AIGC检测结果|AI检测率|AIGC检测率|AI写作|AI生成|疑似AIGC|疑似AI|AIGC率|AI率|AI比例)[^\d]{0,16}(\d{1,3}(?:\.\d+)?)\s*%",
            r"(?:ai writing|ai)[^\d]{0,12}(\d{1,3}(?:\.\d+)?)\s*%",
        ],
    )
    report_date = _extract_date(normalized_text)

    # 扩展字段：更详细的查重指标
    remove_reference_percent = _extract_percent(
        normalized_text,
        [
            r"(?:去除引用文献复制比|去除引用复制比|去除引用)[^\d]{0,12}(\d{1,3}(?:\.\d+)?)\s*%",
        ],
    )
    single_max_dup_percent = _extract_percent(
        normalized_text,
        [
            r"(?:单篇最大文字复制比|单篇最大复制比|单篇最大)[^\d]{0,12}(\d{1,3}(?:\.\d+)?)\s*%",
        ],
    )

    # 疑似剽窃分类
    suspected_plagiarism = _extract_suspected_plagiarism(normalized_text)

    # 提取文本片段（被检测论文片段 + 相似来源）
    fragments = _extract_fragments(normalized_text)

    matched_fields: list[str] = []
    if duplication_percent is not None:
        matched_fields.append("cnki_dup_percent")
    else:
        warnings.append("未识别到查重率，请检查截图清晰度或手动填写。")
    if aigc_percent is not None:
        matched_fields.append("cnki_aigc_percent")
    else:
        warnings.append("未识别到 AIGC 率，请检查截图清晰度或手动填写。")
    if report_date is not None:
        matched_fields.append("report_date")
    else:
        warnings.append("未识别到报告日期，可手动补充。")
    if remove_reference_percent is not None:
        matched_fields.append("remove_reference_dup_percent")
    if single_max_dup_percent is not None:
        matched_fields.append("single_max_dup_percent")
    if suspected_plagiarism:
        matched_fields.append("suspected_plagiarism")
    if fragments:
        matched_fields.append("fragments")

    preview = normalized_text.strip().replace("\n", " ")
    preview = preview[:240] + ("..." if len(preview) > 240 else "")

    return {
        "filename": filename,
        "cnki_dup_percent": duplication_percent,
        "cnki_aigc_percent": aigc_percent,
        "report_date": report_date,
        "remove_reference_dup_percent": remove_reference_percent,
        "single_max_dup_percent": single_max_dup_percent,
        "suspected_plagiarism": suspected_plagiarism,
        "fragments": fragments,
        "extracted_text_preview": preview,
        "matched_fields": matched_fields,
        "ocr_engine": engine,
        "warnings": warnings,
    }


def match_fragments_to_sections(
    fragments: list[dict[str, Any]],
    sections: list[dict[str, Any]],
    min_ratio: float = 0.55,
) -> list[dict[str, Any]]:
    """将知网报告中的文本片段与论文原文段落做模糊匹配。"""
    matched: list[dict[str, Any]] = []
    for frag in fragments:
        source_text = frag.get("source_text", "")
        if not source_text or len(source_text) < 8:
            continue
        best_match = None
        best_ratio = 0.0
        for sec in sections:
            sec_text = sec.get("content") or sec.get("text_preview") or ""
            if not sec_text:
                continue
            # 先用快速包含检查，再用 difflib 精确匹配
            if source_text in sec_text:
                ratio = 1.0
            else:
                ratio = difflib.SequenceMatcher(
                    None, source_text[:200], sec_text[:600]
                ).quick_ratio()
                # 如果片段较短，也试试在段落中找最长公共子串
                if ratio < min_ratio and len(source_text) >= 15:
                    ratio = difflib.SequenceMatcher(
                        None, source_text, sec_text
                    ).find_longest_match(
                        0, len(source_text), 0, len(sec_text)
                    ).size / max(len(source_text), 1)
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = sec
        if best_match and best_ratio >= min_ratio:
            matched.append(
                {
                    **frag,
                    "matched_section_index": best_match.get("section_index"),
                    "matched_section_title": best_match.get("section_title")
                    or best_match.get("title"),
                    "matched_text_preview": (
                        best_match.get("content")
                        or best_match.get("text_preview")
                        or ""
                    )[:200],
                    "match_ratio": round(best_ratio, 3),
                }
            )
        else:
            matched.append(frag)
    return matched


def _extract_image_text(content: bytes, suffix: str) -> str:
    tesseract = shutil.which("tesseract") or shutil.which("tesseract.exe")
    if not tesseract:
        raise ValueError(
            "image OCR requires tesseract.exe installed, or upload a PDF/text file instead"
        )
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp.flush()
        temp_path = Path(tmp.name)
    try:
        result = subprocess.run(
            [tesseract, str(temp_path), "stdout", "-l", "chi_sim+eng"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout
    finally:
        temp_path.unlink(missing_ok=True)


def _extract_percent(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            if 0 <= value <= 100:
                return round(value, 2)
    return None


def _extract_date(text: str) -> str | None:
    match = re.search(r"((20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})日?)", text)
    if not match:
        return None
    year = int(match.group(2))
    month = int(match.group(3))
    day = int(match.group(4))
    return f"{year:04d}-{month:02d}-{day:02d}"


def _extract_suspected_plagiarism(text: str) -> dict[str, int] | None:
    """提取疑似剽窃分类计数：观点、文字表述、数据。"""
    result: dict[str, int] = {}
    patterns = [
        ("观点", r"疑似剽窃观点[^\d]{0,8}(\d+)"),
        ("文字表述", r"疑似剽窃文字表述[^\d]{0,8}(\d+)"),
        ("数据", r"疑似剽窃数据[^\d]{0,8}(\d+)"),
        ("图片", r"疑似剽窃图片[^\d]{0,8}(\d+)"),
    ]
    for label, pattern in patterns:
        match = re.search(pattern, text)
        if match:
            result[label] = int(match.group(1))
    return result if result else None


def _extract_fragments(text: str) -> list[dict[str, Any]]:
    """
    从OCR文本中提取知网报告中的具体片段。
    支持两种格式：
    1. 查重报告：被检测论文片段 + 相似来源片段 + 来源
    2. AIGC报告：疑似AIGC片段
    """
    fragments: list[dict[str, Any]] = []

    # 模式A：查重报告的片段对（被检测论文片段 + 相似来源片段）
    # 使用正则匹配：
    # 被检测论文片段：[换行]内容[换行]相似来源片段：[换行]内容[换行]来源：...
    dup_pattern = re.compile(
        r"(?:被检测论文片段|检测片段|论文片段)[：:\s]*\n?(.{10,400})\n?\s*(?:相似来源片段|来源片段)[：:\s]*\n?(.{10,400})\n?\s*(?:来源|出处)[：:\s]*([^\n]{2,80})?",
        re.DOTALL,
    )
    for m in dup_pattern.finditer(text):
        source_text = _clean_fragment(m.group(1))
        similar_text = _clean_fragment(m.group(2))
        origin = _clean_fragment(m.group(3)) if m.group(3) else None
        if len(source_text) >= 10:
            fragments.append(
                {
                    "type": "duplication",
                    "source_text": source_text,
                    "similar_text": similar_text,
                    "origin": origin,
                }
            )

    # 模式B：AIGC报告的片段
    aigc_pattern = re.compile(
        r"(?:疑似AIGC片段|AIGC片段|AI片段|疑似AI生成片段)[：:\s]*\n?(.{10,400})(?=\n?\s*(?:疑似AIGC片段|AIGC片段|AI片段|被检测论文片段|总文字复制比|$))",
        re.DOTALL,
    )
    for m in aigc_pattern.finditer(text):
        source_text = _clean_fragment(m.group(1))
        if len(source_text) >= 10:
            fragments.append(
                {
                    "type": "aigc",
                    "source_text": source_text,
                    "similar_text": None,
                    "origin": None,
                }
            )

    # 模式C：通用高亮片段（如果没有匹配到结构化格式，尝试提取带引号或特殊标记的长文本）
    if not fragments:
        # 尝试匹配知网报告中常见的高亮段落格式
        generic_pattern = re.compile(
            r"[\u201c\u201d\\']([^\u201c\u201d\\'\n]{15,300})[\u201c\u201d\\']",
        )
        for m in generic_pattern.finditer(text):
            source_text = _clean_fragment(m.group(1))
            if len(source_text) >= 15 and not _is_likely_metadata(source_text):
                fragments.append(
                    {
                        "type": "unknown",
                        "source_text": source_text,
                        "similar_text": None,
                        "origin": None,
                    }
                )

    # 去重
    seen: set[str] = set()
    unique_fragments: list[dict[str, Any]] = []
    for f in fragments:
        key = f["source_text"][:60]
        if key not in seen:
            seen.add(key)
            unique_fragments.append(f)

    return unique_fragments[:20]  # 最多返回20个片段


def _clean_fragment(text: str) -> str:
    """清理提取的片段文本。"""
    text = text.strip()
    # 去掉多余的换行和空格
    text = re.sub(r"\s+", " ", text)
    # 去掉常见的OCR噪音
    text = text.replace("|", "").replace("【", "").replace("】", "")
    return text.strip()


def _is_likely_metadata(text: str) -> bool:
    """判断文本是否可能是元数据而非论文片段。"""
    metadata_keywords = [
        "复制比",
        "重复率",
        "查重率",
        "AIGC率",
        "AI率",
        "文字复制比",
        "去除引用",
        "单篇最大",
        "疑似剽窃",
        "报告编号",
        "检测时间",
        "检测系统",
    ]
    for kw in metadata_keywords:
        if kw in text:
            return True
    return False


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
