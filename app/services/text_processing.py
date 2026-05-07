import re
from dataclasses import dataclass

from app.config import Settings


REFERENCE_HEADING_RE = re.compile(
    r"^\s*(参考文献|References|Bibliography)\s*[:：]?\s*$", re.IGNORECASE | re.MULTILINE
)
ACK_HEADING_RE = re.compile(
    r"^\s*(致谢|鸣谢|Acknowledgements?)\s*[:：]?\s*$", re.IGNORECASE | re.MULTILINE
)
TOC_HEADING_RE = re.compile(
    r"^\s*(目录|目\s*录|Contents)\s*$", re.IGNORECASE | re.MULTILINE
)
SECTION_HEADING_RE = re.compile(
    r"^\s*((第[一二三四五六七八九十百\d]+[章节部分篇])|([0-9一二三四五六七八九十]+[.、][0-9.、]*\s*[\u4e00-\u9fffA-Za-z])|(摘要|引言|绪论|结论|总结|Abstract|Conclusion|Introduction))"
)
PAGE_NO_RE = re.compile(r"^\s*(第\s*)?\d{1,4}\s*(页)?\s*$")
WHITESPACE_RE = re.compile(r"[ \t\r\f\v]+")
BLANK_RE = re.compile(r"\n{3,}")
SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[。！？!?；;])")


@dataclass(frozen=True)
class TextSegment:
    index: int
    text: str
    section_title: str | None
    paragraph_index: int


def normalize_text(text: str) -> str:
    normalized = text.replace("\u3000", " ")
    normalized = re.sub(r"-\n", "", normalized)
    normalized = WHITESPACE_RE.sub(" ", normalized)
    normalized = re.sub(r"\n[ \t]+", "\n", normalized)
    normalized = BLANK_RE.sub("\n\n", normalized)
    return normalized.strip()


def strip_references(text: str) -> str:
    cut_positions = []
    for pattern in (REFERENCE_HEADING_RE, ACK_HEADING_RE):
        match = pattern.search(text)
        if match:
            if pattern is ACK_HEADING_RE and len(text[: match.start()]) > 40:
                cut_positions.append(match.start())
                continue
            suffix = text[match.end() :]
            markers = len(
                re.findall(
                    r"(\[\d+\]|\(\d{4}\)|\bdoi\b|出版社|期刊|学报)",
                    suffix,
                    re.IGNORECASE,
                )
            )
            if len(text[: match.start()]) > 40 and (markers > 0 or len(suffix) > 80):
                cut_positions.append(match.start())

    if not cut_positions:
        return text
    return text[: min(cut_positions)].strip()


def strip_toc(text: str) -> str:
    lines = text.splitlines()
    cleaned: list[str] = []
    in_toc = False
    skipped = 0

    for line in lines:
        stripped = line.strip()
        if TOC_HEADING_RE.match(stripped):
            in_toc = True
            skipped = 0
            continue

        if in_toc:
            skipped += 1
            looks_like_toc = bool(
                re.search(r"\.{2,}\s*\d+$", stripped)
                or re.search(r"\s+\d{1,3}$", stripped)
            )
            if skipped <= 80 and (looks_like_toc or not stripped):
                continue
            in_toc = False

        cleaned.append(line)

    return "\n".join(cleaned)


def strip_page_noise(text: str) -> str:
    lines = text.splitlines()
    short_counts: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        if 0 < len(stripped) <= 32:
            short_counts[stripped] = short_counts.get(stripped, 0) + 1

    repeating = {line for line, count in short_counts.items() if count >= 3}
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if PAGE_NO_RE.match(stripped):
            continue
        if stripped in repeating:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def clean_body_text(text: str) -> str:
    text = normalize_text(text)
    text = strip_page_noise(text)
    text = strip_toc(text)
    text = strip_references(text)
    return normalize_text(text)


def segment_text(text: str, settings: Settings) -> list[str]:
    return [segment.text for segment in segment_document(text, settings)]


def segment_document(text: str, settings: Settings) -> list[TextSegment]:
    text = clean_body_text(text)
    paragraphs = [item.strip() for item in re.split(r"\n{2,}", text) if item.strip()]
    segments: list[TextSegment] = []
    current_section: str | None = None
    paragraph_index = 0

    for paragraph in paragraphs:
        if SECTION_HEADING_RE.match(paragraph) and len(paragraph) <= 80:
            current_section = paragraph
            continue

        paragraph_index += 1
        if len(paragraph) <= settings.target_segment_chars * 1.35:
            if _is_valid_body_segment(paragraph, settings):
                segments.append(
                    _make_segment(segments, paragraph, current_section, paragraph_index)
                )
            continue

        buffer = ""
        for sentence in SENTENCE_BOUNDARY_RE.split(paragraph):
            sentence = sentence.strip()
            if not sentence:
                continue
            if (
                len(buffer) + len(sentence) > settings.target_segment_chars
                and len(buffer) >= settings.min_segment_chars
            ):
                segments.append(
                    _make_segment(
                        segments, buffer.strip(), current_section, paragraph_index
                    )
                )
                buffer = sentence
            else:
                buffer = f"{buffer}{sentence}" if buffer else sentence
        if _is_valid_body_segment(buffer, settings):
            segments.append(
                _make_segment(
                    segments, buffer.strip(), current_section, paragraph_index
                )
            )

    if not segments and text:
        segments = [
            _make_segment(segments, text[: settings.target_segment_chars], None, 1)
        ]

    return segments


def preview_text(text: str, limit: int = 96) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return f"{compact[:limit]}..."


def _make_segment(
    segments: list[TextSegment],
    text: str,
    section_title: str | None,
    paragraph_index: int,
) -> TextSegment:
    return TextSegment(
        index=len(segments),
        text=text,
        section_title=section_title,
        paragraph_index=paragraph_index,
    )


def _is_valid_body_segment(text: str, settings: Settings) -> bool:
    stripped = text.strip()
    if len(stripped) >= settings.min_segment_chars:
        return True
    if len(stripped) < 45:
        return False
    return len(re.findall(r"[\u4e00-\u9fff]", stripped)) >= 35 and bool(
        re.search(r"[。！？!?；;]", stripped)
    )
