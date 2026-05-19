"""知网报告解析模块。

支持解析知网查重报告和 AIGC 检测报告的 PDF、HTML、Word 格式。
解析后返回统一的 CnkiReport 结构，包含风险段落、重复率、AIGC率等信息。

设计原则：
1. 宽容解析：格式识别失败时不抛出异常，返回尽可能提取的信息
2. 分级提取：先提取总体指标，再提取风险片段
3. 未知片段降级：无法解析的片段放入 "unmatched" 而非丢弃
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Literal

from pypdf import PdfReader


@dataclass
class CnkiRiskSpan:
    span_id: str
    text: str
    risk_type: Literal["similarity", "aigc"]
    risk_level: Literal["high", "medium", "low"]
    similarity: float | None = None
    aigc_score: float | None = None
    matched_source: str | None = None
    page_number: int | None = None
    raw_meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class CnkiReport:
    report_type: Literal["similarity", "aigc", "mixed"]
    total_copy_ratio: float | None = None
    aigc_ratio: float | None = None
    remove_reference_ratio: float | None = None
    single_max_ratio: float | None = None
    generated_at: str | None = None
    risky_spans: list[CnkiRiskSpan] = field(default_factory=list)
    raw_meta: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 文本预处理
# ---------------------------------------------------------------------------


def _normalize_for_matching(text: str) -> str:
    """归一化文本用于匹配对比。"""
    # 统一全角半角
    text = unicodedata.normalize("NFKC", text)
    # 去除多余空白
    text = re.sub(r"\s+", "", text)
    # 去除常见标点差异
    text = text.replace("，", ",").replace("。", ".").replace("；", ";").replace("：", ":")
    return text.strip()


# ---------------------------------------------------------------------------
# 正则模式库
# ---------------------------------------------------------------------------

_TOTAL_COPY_RE = re.compile(
    r"(?:总文字复制比|文字复制比|总复制比|重复率|查重率)[^\d]{0,12}(\d{1,3}(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
_AIGC_RE = re.compile(
    r"(?:AIGC|AI特征值|AI检测结果|AIGC检测结果|AI检测率|AIGC检测率|AI写作|AI生成|疑似AIGC|疑似AI|AIGC率|AI率|AI比例)[^\d]{0,16}(\d{1,3}(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
_REMOVE_REF_RE = re.compile(
    r"(?:去除引用文献复制比|去除引用复制比|去除引用)[^\d]{0,12}(\d{1,3}(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
_SINGLE_MAX_RE = re.compile(
    r"(?:单篇最大文字复制比|单篇最大复制比|单篇最大)[^\d]{0,12}(\d{1,3}(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)

# 知网报告中的风险片段标记模式
_SIMILARITY_MARKER_RE = re.compile(
    r"(?:相似比|相似比例|复制比|重复比例)[^\d]{0,8}(\d{1,3}(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)

# 知网 "原文对照" 视图中常见的相似来源标记
_SOURCE_RE = re.compile(
    r"(?:相似来源|来源|比对来源)[^：:]*[:：]\s*(.+?)(?:\n|\r|$)",
    re.IGNORECASE,
)

# 日期提取
_DATE_RE = re.compile(
    r"(\d{4}[年/\-]\d{1,2}[月/\-]\d{1,2}[日]?)",
)


# ---------------------------------------------------------------------------
# 报告类型判断
# ---------------------------------------------------------------------------


def _detect_report_type(text: str) -> Literal["similarity", "aigc", "mixed"]:
    """根据文本内容判断报告类型。"""
    text_lower = text.lower()
    has_similarity = any(
        kw in text_lower
        for kw in [
            "复制比",
            "重复率",
            "查重",
            "相似度",
            "大学生论文联合比对库",
            "学术论文联合比对库",
        ]
    )
    has_aigc = any(
        kw in text_lower
        for kw in ["aigc", "ai特征", "ai检测", "ai写作", "ai生成", "疑似ai"]
    )

    if has_similarity and has_aigc:
        return "mixed"
    if has_aigc:
        return "aigc"
    return "similarity"


# ---------------------------------------------------------------------------
# 指标提取
# ---------------------------------------------------------------------------


def _extract_percent(text: str, pattern: re.Pattern) -> float | None:
    m = pattern.search(text)
    if m:
        val = float(m.group(1))
        return min(val, 100.0)
    return None


def _extract_total_copy_ratio(text: str) -> float | None:
    direct = _extract_percent(text, _TOTAL_COPY_RE)
    if direct is not None:
        return direct

    self_write = _extract_self_write_rate(text)
    if self_write is not None:
        return round(max(0.0, 100.0 - self_write), 2)

    compact = re.sub(r"\s+", "", text)
    match = re.search(
        "(?:\u603b\u6587\u5b57\u590d\u5236\u6bd4|\u6587\u5b57\u590d\u5236\u6bd4|\u603b\u590d\u5236\u6bd4|\u91cd\u590d\u7387|\u67e5\u91cd\u7387)(\d{1,3}(?:\.\d+)?)%",
        compact,
        re.IGNORECASE,
    )
    if not match:
        match = re.search(r"(?:duplication|similarity)(\d{1,3}(?:\.\d+)?)%", compact, re.IGNORECASE)
    if match:
        return min(float(match.group(1)), 100.0)

    compact_self_write = _extract_self_write_rate(compact)
    if compact_self_write is not None:
        return round(max(0.0, 100.0 - compact_self_write), 2)

    return None


def _extract_self_write_rate(text: str) -> float | None:
    match = re.search(
        "(?:\u81ea\u5199\u7387|\u81ea\u5beb\u7387|\u539f\u521b\u7387|\u539f\u5275\u7387|\u81ea\u64b0\u7387|\u81ea\u64b0\u6bd4)[^\d]{0,8}(\d{1,3}(?:\.\d+)?)\s*%",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    return min(float(match.group(1)), 100.0)


def _extract_aigc_ratio(text: str) -> float | None:
    direct = _extract_percent(text, _AIGC_RE)
    if direct is not None:
        return direct

    compact = re.sub(r"\s+", "", text)
    compact_match = re.search(
        r"(?:AIGC|AI特征值|AI检测结果|AIGC检测结果|AI检测率|AIGC检测率|AI写作|AI生成|疑似AIGC|疑似AI|AIGC率|AI率|AI比例)(\d{1,3}(?:\.\d+)?)%",
        compact,
        re.IGNORECASE,
    )
    if compact_match:
        return min(float(compact_match.group(1)), 100.0)

    return _extract_aigc_ratio_from_table(text)


def _extract_aigc_ratio_from_table(text: str) -> float | None:
    compact = re.sub(r"\s+", "", text).upper()
    if "AIGC" not in compact and "AI生成" not in text and "疑AI" not in text and "AIGC生成" not in compact:
        return None

    section = text
    anchor_match = re.search(r"(?:AIGC|AI\s*GC|疑AI|AI生成)", text, re.IGNORECASE)
    if anchor_match:
        start = max(0, anchor_match.start() - 120)
        section = text[start : start + 6000]

    pairs: list[tuple[int, int]] = []
    for numer_text, denom_text in re.findall(r"(?<!\d)(\d{1,6})/(\d{2,7})(?!\d)", section):
        numer = int(numer_text)
        denom = int(denom_text)
        if denom < 100 or denom > 500000:
            continue
        if numer < 0 or numer > denom:
            continue
        pairs.append((numer, denom))

    if len(pairs) < 2:
        return None

    total_numer = sum(item[0] for item in pairs)
    total_denom = sum(item[1] for item in pairs)
    if total_denom <= 0:
        return None

    percent = round(total_numer * 100 / total_denom, 2)
    return percent if 0 <= percent <= 100 else None


def _extract_date(text: str) -> str | None:
    m = _DATE_RE.search(text)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# PDF 解析
# ---------------------------------------------------------------------------


def _parse_pdf_report(file_path: str) -> CnkiReport:
    """解析知网 PDF 报告。"""
    reader = PdfReader(file_path)
    full_text = ""
    pages_text: list[tuple[int, str]] = []

    for i, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
            pages_text.append((i, page_text))
            full_text += page_text + "\n"
        except Exception:
            continue

    report_type = _detect_report_type(full_text)

    report = CnkiReport(
        report_type=report_type,
        total_copy_ratio=_extract_total_copy_ratio(full_text),
        aigc_ratio=_extract_aigc_ratio(full_text),
        remove_reference_ratio=_extract_percent(full_text, _REMOVE_REF_RE),
        single_max_ratio=_extract_percent(full_text, _SINGLE_MAX_RE),
        generated_at=_extract_date(full_text),
    )

    # 提取风险片段
    spans = _extract_risk_spans_from_text(full_text, report_type)

    # 尝试为每个 span 分配页码（通过文本定位）
    _assign_page_numbers(spans, pages_text)

    report.risky_spans = spans
    report.raw_meta = {"page_count": len(reader.pages), "parser": "pdf"}
    return report


# ---------------------------------------------------------------------------
# HTML 解析
# ---------------------------------------------------------------------------


class _CnkiHtmlParser(HTMLParser):
    """轻量级知网 HTML 报告解析器。"""

    def __init__(self) -> None:
        super().__init__()
        self.in_red_span = False
        self.in_orange_span = False
        self.in_yellow_span = False
        self.current_risk_level: Literal["high", "medium", "low"] | None = None
        self.current_text_parts: list[str] = []
        self.colored_spans: list[tuple[str, Literal["high", "medium", "low"], str]] = []
        self.all_text = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k: v for k, v in attrs}
        style = attr_dict.get("style", "") or ""
        class_name = attr_dict.get("class", "") or ""

        # 知网 HTML 报告中常见的颜色标记
        if "color:red" in style or "color: red" in style or class_name in ("red", "risk-high", "highlight-red"):
            self.in_red_span = True
            self.current_risk_level = "high"
        elif "color:orange" in style or "color: orange" in style or class_name in ("orange", "risk-medium", "highlight-orange"):
            self.in_orange_span = True
            self.current_risk_level = "medium"
        elif "color:#ff9900" in style or class_name in ("yellow", "risk-low", "highlight-yellow"):
            self.in_yellow_span = True
            self.current_risk_level = "low"

    def handle_endtag(self, tag: str) -> None:
        if tag in ("span", "font", "p", "div"):
            if self.current_risk_level and self.current_text_parts:
                text = "".join(self.current_text_parts).strip()
                if len(text) >= 10:
                    self.colored_spans.append((text, self.current_risk_level, ""))
            self.in_red_span = False
            self.in_orange_span = False
            self.in_yellow_span = False
            self.current_risk_level = None
            self.current_text_parts = []

    def handle_data(self, data: str) -> None:
        self.all_text += data
        if self.in_red_span or self.in_orange_span or self.in_yellow_span:
            self.current_text_parts.append(data)


def _parse_html_report(file_path: str) -> CnkiReport:
    """解析知网 HTML 报告。"""
    content = Path(file_path).read_text(encoding="utf-8", errors="ignore")

    parser = _CnkiHtmlParser()
    parser.feed(content)

    report_type = _detect_report_type(parser.all_text)

    report = CnkiReport(
        report_type=report_type,
        total_copy_ratio=_extract_total_copy_ratio(parser.all_text),
        aigc_ratio=_extract_aigc_ratio(parser.all_text),
        remove_reference_ratio=_extract_percent(parser.all_text, _REMOVE_REF_RE),
        single_max_ratio=_extract_percent(parser.all_text, _SINGLE_MAX_RE),
        generated_at=_extract_date(parser.all_text),
    )

    spans: list[CnkiRiskSpan] = []
    for idx, (text, level, _) in enumerate(parser.colored_spans):
        # 尝试从附近文本提取相似比例
        similarity = _extract_similarity_near_text(parser.all_text, text)
        spans.append(
            CnkiRiskSpan(
                span_id=f"span_{idx:04d}",
                text=text,
                risk_type="similarity" if report_type in ("similarity", "mixed") else "aigc",
                risk_level=level,
                similarity=similarity,
                raw_meta={"parser": "html_color"},
            )
        )

    # 如果 HTML 颜色标记没有提取到足够片段，fallback 到文本启发式
    if len(spans) < 3:
        text_spans = _extract_risk_spans_from_text(parser.all_text, report_type)
        spans = _merge_spans(spans, text_spans)

    report.risky_spans = spans
    report.raw_meta = {"parser": "html", "colored_span_count": len(parser.colored_spans)}
    return report


# ---------------------------------------------------------------------------
# Word (DOCX) 解析
# ---------------------------------------------------------------------------


def _parse_docx_report(file_path: str) -> CnkiReport:
    """解析知网 Word 报告。"""
    from docx import Document
    from docx.shared import RGBColor

    doc = Document(file_path)
    full_text = ""
    colored_paras: list[tuple[str, Literal["high", "medium", "low"], str]] = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        full_text += text + "\n"

        # 检测字体颜色判断风险等级
        risk_level: Literal["high", "medium", "low"] | None = None
        for run in para.runs:
            if run.font.color and run.font.color.rgb:
                rgb = run.font.color.rgb
                # 红色系
                if rgb[0] > 200 and rgb[1] < 100 and rgb[2] < 100:
                    risk_level = "high"
                    break
                # 橙/黄色系
                if rgb[0] > 200 and rgb[1] > 120 and rgb[2] < 100:
                    risk_level = "medium"
                    break
                # 紫色/其他
                if rgb[2] > 150 and rgb[0] > 100:
                    risk_level = "low"
                    break

        if risk_level and len(text) >= 10:
            colored_paras.append((text, risk_level, ""))

    report_type = _detect_report_type(full_text)

    report = CnkiReport(
        report_type=report_type,
        total_copy_ratio=_extract_total_copy_ratio(full_text),
        aigc_ratio=_extract_aigc_ratio(full_text),
        remove_reference_ratio=_extract_percent(full_text, _REMOVE_REF_RE),
        single_max_ratio=_extract_percent(full_text, _SINGLE_MAX_RE),
        generated_at=_extract_date(full_text),
    )

    spans: list[CnkiRiskSpan] = []
    for idx, (text, level, _) in enumerate(colored_paras):
        similarity = _extract_similarity_near_text(full_text, text)
        spans.append(
            CnkiRiskSpan(
                span_id=f"span_{idx:04d}",
                text=text,
                risk_type="similarity" if report_type in ("similarity", "mixed") else "aigc",
                risk_level=level,
                similarity=similarity,
                raw_meta={"parser": "docx_color"},
            )
        )

    if len(spans) < 3:
        text_spans = _extract_risk_spans_from_text(full_text, report_type)
        spans = _merge_spans(spans, text_spans)

    report.risky_spans = spans
    report.raw_meta = {"parser": "docx", "colored_para_count": len(colored_paras)}
    return report


# ---------------------------------------------------------------------------
# 通用文本启发式风险片段提取
# ---------------------------------------------------------------------------


def _extract_risk_spans_from_text(
    text: str, report_type: Literal["similarity", "aigc", "mixed"]
) -> list[CnkiRiskSpan]:
    """从纯文本中启发式提取风险片段。

    知网报告的结构特征：
    - 报告正文中，被标记的段落通常前后有百分比或来源信息
    - 使用段落长度和上下文特征进行过滤
    """
    spans: list[CnkiRiskSpan] = []
    paragraphs = [p.strip() for p in re.split(r"[\n\r]+", text) if p.strip()]

    for idx, para in enumerate(paragraphs):
        # 跳过过短段落（通常是页眉页脚、页码）
        if len(para) < 15 or len(para) > 800:
            continue

        # 特征1：段落本身包含百分比数字（如 "相似比 23%"）
        sim_match = _SIMILARITY_MARKER_RE.search(para)
        if sim_match:
            similarity = float(sim_match.group(1))
            level = _similarity_to_level(similarity)
            spans.append(
                CnkiRiskSpan(
                    span_id=f"span_t{idx:04d}",
                    text=_clean_span_text(para),
                    risk_type="similarity",
                    risk_level=level,
                    similarity=similarity,
                    raw_meta={"extract_method": "inline_percent"},
                )
            )
            continue

        # 特征2：下一段包含 "相似来源" 或 "比对来源"
        if idx + 1 < len(paragraphs):
            next_para = paragraphs[idx + 1]
            if _SOURCE_RE.search(next_para) and len(para) >= 20:
                # 尝试从后续文本找相似比例
                context = "\n".join(paragraphs[idx : idx + 3])
                similarity = _extract_similarity_near_text(context, para)
                level = _similarity_to_level(similarity) if similarity else "medium"
                spans.append(
                    CnkiRiskSpan(
                        span_id=f"span_t{idx:04d}",
                        text=_clean_span_text(para),
                        risk_type="similarity",
                        risk_level=level,
                        similarity=similarity,
                        matched_source=_extract_source(next_para),
                        raw_meta={"extract_method": "source_hint"},
                    )
                )
                continue

        # 特征3：AIGC 报告中的标记文本
        if report_type in ("aigc", "mixed"):
            aigc_match = re.search(r"(?:AIGC|AI)疑似度[^\d]{0,8}(\d{1,3}(?:\.\d+)?)\s*%", para, re.IGNORECASE)
            if aigc_match:
                aigc_score = float(aigc_match.group(1))
                level = _similarity_to_level(aigc_score)
                spans.append(
                    CnkiRiskSpan(
                        span_id=f"span_t{idx:04d}",
                        text=_clean_span_text(para),
                        risk_type="aigc",
                        risk_level=level,
                        aigc_score=aigc_score,
                        raw_meta={"extract_method": "aigc_inline"},
                    )
                )

    # 去重：基于归一化文本
    seen = set()
    unique_spans = []
    for span in spans:
        key = _normalize_for_matching(span.text)
        if key not in seen and len(key) >= 10:
            seen.add(key)
            unique_spans.append(span)

    return unique_spans


def _similarity_to_level(similarity: float | None) -> Literal["high", "medium", "low"]:
    if similarity is None:
        return "medium"
    if similarity >= 40:
        return "high"
    if similarity >= 20:
        return "medium"
    return "low"


def _clean_span_text(text: str) -> str:
    """清理提取的风险片段文本。"""
    # 去除页眉页脚常见内容
    text = re.sub(r"第\s*\d+\s*页\s*共\s*\d+\s*页", "", text)
    text = re.sub(r"Page\s*\d+\s*of\s*\d+", "", text, flags=re.IGNORECASE)
    # 去除知网报告特有的导航文字
    text = re.sub(r"^(?:目录|摘要|报告编号|检测时间|检测机构)[:：].*", "", text)
    return text.strip()


def _extract_similarity_near_text(context: str, target: str) -> float | None:
    """在 target 附近的 context 中查找相似比例。"""
    # 查找 target 前后 200 字符内的百分比
    idx = context.find(target[:30])
    if idx == -1:
        idx = 0
    window = context[max(0, idx - 200) : idx + len(target) + 200]
    m = _SIMILARITY_MARKER_RE.search(window)
    if m:
        return float(m.group(1))
    # 尝试更宽泛的匹配
    m = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%", window)
    if m:
        val = float(m.group(1))
        if 0 < val <= 100:
            return val
    return None


def _extract_source(text: str) -> str | None:
    m = _SOURCE_RE.search(text)
    return m.group(1).strip() if m else None


# ---------------------------------------------------------------------------
# Span 合并与去重
# ---------------------------------------------------------------------------


def _merge_spans(
    colored_spans: list[CnkiRiskSpan], text_spans: list[CnkiRiskSpan]
) -> list[CnkiRiskSpan]:
    """合并来自不同提取策略的 spans，去重。"""
    seen: set[str] = set()
    result: list[CnkiRiskSpan] = []

    for span in colored_spans + text_spans:
        key = _normalize_for_matching(span.text)
        if key not in seen and len(key) >= 10:
            seen.add(key)
            result.append(span)

    return result


# ---------------------------------------------------------------------------
# 页码分配
# ---------------------------------------------------------------------------


def _assign_page_numbers(
    spans: list[CnkiRiskSpan], pages_text: list[tuple[int, str]]
) -> None:
    """根据文本匹配为 span 分配页码。"""
    for span in spans:
        for page_num, page_text in pages_text:
            if span.text[:30] in page_text or _normalize_for_matching(span.text)[:30] in _normalize_for_matching(page_text):
                span.page_number = page_num
                break


# ---------------------------------------------------------------------------
# 统一入口
# ---------------------------------------------------------------------------


def parse_cnki_report(file_path: str) -> CnkiReport:
    """自动检测格式并解析知网报告。

    Args:
        file_path: 报告文件路径

    Returns:
        CnkiReport 对象，包含解析后的风险信息

    Raises:
        ValueError: 不支持的文件格式
    """
    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        return _parse_pdf_report(file_path)
    if suffix in (".html", ".htm"):
        return _parse_html_report(file_path)
    if suffix == ".docx":
        return _parse_docx_report(file_path)

    raise ValueError(f"不支持的知网报告格式: {suffix}，仅支持 .pdf、.html、.docx")


def parse_cnki_report_bytes(filename: str, content: bytes) -> CnkiReport:
    """从内存中的文件内容解析知网报告。"""
    import tempfile
    import os

    suffix = Path(filename).suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        return parse_cnki_report(tmp_path)
    finally:
        os.unlink(tmp_path)
