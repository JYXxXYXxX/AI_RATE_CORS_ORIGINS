from __future__ import annotations

import hashlib
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

TEMPLATE_PHRASES = [
    "具有重要的理论意义和现实意义",
    "为后续研究提供参考",
    "丰富了相关研究成果",
    "对相关实践具有借鉴价值",
    "本文首先分析",
    "其次探讨",
    "最后提出",
    "综上所述",
    "有助于进一步提升",
    "可以看出",
]

SENTENCE_RE = re.compile(r"[^。！？!?；;]+[。！？!?；;]?")
SPACE_RE = re.compile(r"\s+")

# 用于检测乱码：只保留"正常论文该有的字符"
# 允许：CJK中文、基本拉丁(英文/数字/标点)、CJK标点、全角字符、通用标点、空白
# 一旦出现希腊/西里尔/亚美尼亚/阿拉伯等异域字符，直接判为乱码
_LEGIBLE_RE = re.compile(
    r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\u0000-\u007f\u2000-\u206f\s]+"
)
# 明显不属于中文学术论文的字符块（希腊、西里尔、亚美尼亚、格鲁吉亚、阿拉伯等）
_WEIRD_SCRIPT_RE = re.compile(
    r"[\u0370-\u04ff\u0530-\u058f\u0600-\u06ff\u0750-\u077f\u10a0-\u10ff\u1f00-\u1fff]+"
)
_ASCII_RUN_RE = re.compile(r"[A-Za-z0-9_]+")


def _is_garbled(text: str, threshold: float = 0.60) -> bool:
    """判断文本是否为乱码/不可读内容。

    策略：
    1. 如果包含希腊/西里尔/亚美尼亚等异域字符，直接判为乱码；
    2. 否则计算"正常可读字符"占比，低于阈值判为乱码。
    """
    if not text:
        return True
    # 策略1：出现异域字符直接判乱码
    weird = sum(len(m.group(0)) for m in _WEIRD_SCRIPT_RE.finditer(text))
    if weird > 0:
        return True
    # 策略2：可读字符占比过低
    legible = sum(len(m.group(0)) for m in _LEGIBLE_RE.finditer(text))
    ratio = legible / len(text)
    if ratio < threshold:
        return True

    # 策略3：大量碎片化英数字穿插在中文中，通常是解析错位后的乱码
    ascii_runs = _ASCII_RUN_RE.findall(text)
    if ascii_runs:
        ascii_chars = sum(len(item) for item in ascii_runs)
        short_runs = [item for item in ascii_runs if len(item) <= 2]
        single_runs = [item for item in ascii_runs if len(item) == 1]
        ascii_ratio = ascii_chars / max(len(text), 1)
        if ascii_ratio >= 0.14 and len(short_runs) >= 6:
            return True
        if len(ascii_runs) >= 8 and len(single_runs) / len(ascii_runs) >= 0.6:
            return True

    return False


# ---------------------------------------------------------------------------
# 语义 embedding 模型（进程单例）
# ---------------------------------------------------------------------------
_embedding_model: Any = None
_embedding_load_attempted = False
_EMBEDDING_DIMS = 768


def _get_embedding_model() -> Any:
    """延迟加载 sentence-transformers 模型，失败时返回 None。"""
    global _embedding_model, _embedding_load_attempted
    if _embedding_load_attempted:
        return _embedding_model
    _embedding_load_attempted = True
    try:
        from sentence_transformers import SentenceTransformer
        import os

        model_name = os.environ.get(
            "AI_RATE_EMBEDDING_MODEL",
            "shibing624/text2vec-base-chinese",
        )
        _embedding_model = SentenceTransformer(model_name)
        logger.info("语义 embedding 模型已加载: %s", model_name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("加载 embedding 模型失败: %s，将使用 hash 占位向量", exc)
        _embedding_model = None
    return _embedding_model


@dataclass(frozen=True)
class DuplicationSectionScore:
    section_index: int
    raw_score: float
    normalized_score: float
    risk_level: str
    reasons: list[str]
    best_overlap_with: int | None
    template_hits: list[str]
    duplicate_sentence_count: int
    quote_ratio: float


@dataclass(frozen=True)
class SimilarityEvidence:
    section_index: int
    matched_source: str
    matched_title: str
    matched_snippet: str
    similarity_score: float
    overlap_chars: int
    match_type: str
    source_url: str | None = None


@dataclass(frozen=True)
class DuplicationDocumentScore:
    overall_score: float
    template_density: float
    duplicate_sentence_ratio: float
    max_section_score: float
    evidence_count: int
    section_scores: list[DuplicationSectionScore]
    matches: list[SimilarityEvidence]


def build_embedding_vector(text: str, dims: int = 768) -> str:
    """生成段落的 embedding 向量字符串，用于存入 pgvector。

    优先使用 sentence-transformers 语义模型；模型不可用时降级为 hash 占位。
    """
    if dims <= 0:
        raise ValueError("dims must be positive")

    model = _get_embedding_model()
    if model is not None:
        return _build_semantic_vector(model, text, dims)
    return _build_hash_vector_fallback(text, dims)


def build_embedding_vectors_batch(texts: list[str], dims: int = 768) -> list[str]:
    """批量生成 embedding 向量，利用 SentenceTransformer 的 batch encoding 加速。"""
    if dims <= 0:
        raise ValueError("dims must be positive")

    model = _get_embedding_model()
    if model is None:
        return [_build_hash_vector_fallback(text, dims) for text in texts]

    compacted = [SPACE_RE.sub("", text).strip() for text in texts]
    empty_vector = "[" + ",".join("0" for _ in range(dims)) + "]"

    # 找出非空文本的索引
    non_empty_indices = [i for i, c in enumerate(compacted) if c]
    non_empty_texts = [compacted[i] for i in non_empty_indices]

    results = [empty_vector] * len(texts)
    if non_empty_texts:
        vectors = model.encode(
            non_empty_texts, normalize_embeddings=True, batch_size=32
        )
        for idx, vec in zip(non_empty_indices, vectors):
            if len(vec) > dims:
                vec = vec[:dims]
            elif len(vec) < dims:
                vec = np.concatenate([vec, np.zeros(dims - len(vec))])
            results[idx] = "[" + ",".join(f"{v:.6f}" for v in vec.tolist()) + "]"
    return results


def _build_semantic_vector(model: Any, text: str, dims: int) -> str:
    """用 sentence-transformers 模型生成真实语义向量。"""
    compact = SPACE_RE.sub("", text).strip()
    if not compact:
        return "[" + ",".join("0" for _ in range(dims)) + "]"

    vector = model.encode(compact, normalize_embeddings=True)
    # 如果模型维度与 dims 不一致，截断或补零
    if len(vector) > dims:
        vector = vector[:dims]
    elif len(vector) < dims:
        vector = np.concatenate([vector, np.zeros(dims - len(vector))])
    values = [f"{v:.6f}" for v in vector.tolist()]
    return "[" + ",".join(values) + "]"


def _build_hash_vector_fallback(text: str, dims: int) -> str:
    """模型不可用时的降级方案：hash 占位向量。"""
    vector = np.zeros(dims, dtype=np.float32)
    compact = SPACE_RE.sub("", text)
    if not compact:
        return "[" + ",".join("0" for _ in range(dims)) + "]"

    for n in (2, 3, 4):
        if len(compact) < n:
            continue
        for index in range(len(compact) - n + 1):
            gram = compact[index : index + n]
            digest = hashlib.sha1(gram.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], byteorder="big") % dims
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign

    norm = float(np.linalg.norm(vector))
    if norm > 0:
        vector /= norm
    values = [f"{value:.6f}" for value in vector.tolist()]
    return "[" + ",".join(values) + "]"


def score_duplication(
    sections: list[dict[str, Any]],
    cross_doc_matches: list[dict[str, Any]] | None = None,
) -> DuplicationDocumentScore:
    """计算段落级查重分数。

    sections: 当前文档的段落列表。
    cross_doc_matches: 可选，从 pgvector 检索到的跨文档相似段落列表，
        每条包含 section_index, distance, document_title, text_preview 等。
    """
    if not sections:
        return DuplicationDocumentScore(
            overall_score=0.0,
            template_density=0.0,
            duplicate_sentence_ratio=0.0,
            max_section_score=0.0,
            evidence_count=0,
            section_scores=[],
            matches=[],
        )

    normalized_texts = [_normalize(section["content"]) for section in sections]
    shingle_sets = [_char_shingles(text) for text in normalized_texts]
    sentences_by_section = [_extract_sentences(text) for text in normalized_texts]
    duplicate_counter = Counter(
        sentence
        for sentences in sentences_by_section
        for sentence in sentences
        if len(sentence) >= 18
    )

    section_scores: list[DuplicationSectionScore] = []
    matches: list[SimilarityEvidence] = []

    for index, section in enumerate(sections):
        current_text = normalized_texts[index]
        current_shingles = shingle_sets[index]
        template_hits = [
            phrase for phrase in TEMPLATE_PHRASES if phrase in current_text
        ]
        duplicate_sentences = [
            sentence
            for sentence in sentences_by_section[index]
            if duplicate_counter[sentence] >= 2
        ]
        quote_ratio = _quote_ratio(section["content"])

        best_similarity = 0.0
        best_match_index: int | None = None
        for other_index, other_shingles in enumerate(shingle_sets):
            if other_index == index:
                continue
            similarity = _jaccard(current_shingles, other_shingles)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match_index = other_index

        template_score = min(1.0, len(template_hits) / 5)
        duplicate_sentence_score = min(
            1.0, len(duplicate_sentences) / max(len(sentences_by_section[index]), 1)
        )
        raw_score = (
            0.58 * best_similarity
            + 0.24 * template_score
            + 0.24 * duplicate_sentence_score
            - 0.08 * quote_ratio
        )
        raw_score = max(0.0, raw_score)
        normalized_score = max(0.0, min(1.0, raw_score))
        reasons = _build_reasons(
            best_similarity, template_hits, duplicate_sentences, quote_ratio
        )
        risk_level = _risk_level(normalized_score)

        section_scores.append(
            DuplicationSectionScore(
                section_index=section["section_index"],
                raw_score=round(raw_score, 4),
                normalized_score=round(normalized_score, 4),
                risk_level=risk_level,
                reasons=reasons,
                best_overlap_with=best_match_index,
                template_hits=template_hits[:4],
                duplicate_sentence_count=len(duplicate_sentences),
                quote_ratio=round(quote_ratio, 4),
            )
        )

        if best_match_index is not None and best_similarity >= 0.18:
            matched_section = sections[best_match_index]
            snippet = (matched_section.get("text_preview") or "")[:180]
            if not _is_garbled(snippet):
                matches.append(
                    SimilarityEvidence(
                        section_index=section["section_index"],
                        matched_source="local_corpus",
                        matched_title=matched_section.get("section_title")
                        or f"正文段落 {best_match_index + 1}",
                        matched_snippet=snippet,
                        similarity_score=round(best_similarity, 4),
                        overlap_chars=max(
                            0,
                            math.floor(
                                min(
                                    section["char_count"], matched_section["char_count"]
                                )
                                * best_similarity
                            ),
                        ),
                        match_type="exact" if best_similarity >= 0.58 else "semantic",
                    )
                )

        if template_hits:
            matches.append(
                SimilarityEvidence(
                    section_index=section["section_index"],
                    matched_source="template_phrase_bank",
                    matched_title="通用学术模板表达",
                    matched_snippet="；".join(template_hits[:3]),
                    similarity_score=round(
                        min(0.95, 0.34 + len(template_hits) * 0.11), 4
                    ),
                    overlap_chars=sum(len(item) for item in template_hits[:3]),
                    match_type="paraphrase",
                )
            )

    # ---- 跨文档语义相似匹配 ----
    cross_doc_by_section: dict[int, list[dict[str, Any]]] = {}
    if cross_doc_matches:
        for hit in cross_doc_matches:
            idx = hit.get("section_index", -1)
            cross_doc_by_section.setdefault(idx, []).append(hit)

    for section_idx, hits in cross_doc_by_section.items():
        seen_snippets: set[str] = set()
        for hit in hits:
            distance = float(hit.get("distance", 1.0))
            similarity = max(0.0, 1.0 - distance)
            if similarity < 0.55:
                continue
            snippet = (hit.get("text_preview") or hit.get("content", ""))[:180]
            # 过滤乱码
            if _is_garbled(snippet):
                continue
            # 去重：同一 snippet 不重复展示
            dedup_key = snippet[:40]
            if dedup_key in seen_snippets:
                continue
            seen_snippets.add(dedup_key)
            matches.append(
                SimilarityEvidence(
                    section_index=section_idx,
                    matched_source="corpus_semantic",
                    matched_title=hit.get("document_title")
                    or hit.get("document_filename")
                    or "语料库文档",
                    matched_snippet=snippet,
                    similarity_score=round(similarity, 4),
                    overlap_chars=max(0, round(hit.get("char_count", 0) * similarity)),
                    match_type="semantic",
                )
            )

        # 跨文档命中也要拉高对应段落的分数
        if section_idx < len(section_scores):
            original = section_scores[section_idx]
            best_cross_sim = max(
                (max(0.0, 1.0 - float(h.get("distance", 1.0))) for h in hits),
                default=0.0,
            )
            if best_cross_sim > 0.55:
                boosted = min(1.0, original.normalized_score + best_cross_sim * 0.35)
                section_scores[section_idx] = DuplicationSectionScore(
                    section_index=original.section_index,
                    raw_score=original.raw_score,
                    normalized_score=round(boosted, 4),
                    risk_level=_risk_level(boosted),
                    reasons=original.reasons + ["跨文档语义检索发现高度相似段落"],
                    best_overlap_with=original.best_overlap_with,
                    template_hits=original.template_hits,
                    duplicate_sentence_count=original.duplicate_sentence_count,
                    quote_ratio=original.quote_ratio,
                )

    total_chars = sum(section["char_count"] for section in sections) or 1
    overall_score = (
        sum(
            section_score.normalized_score * sections[index]["char_count"]
            for index, section_score in enumerate(section_scores)
        )
        / total_chars
    )
    template_density = sum(len(score.template_hits) for score in section_scores) / max(
        len(section_scores), 1
    )
    duplicate_sentence_ratio = sum(
        score.duplicate_sentence_count for score in section_scores
    ) / max(
        sum(len(items) for items in sentences_by_section),
        1,
    )
    max_section_score = max(score.normalized_score for score in section_scores)

    matches.sort(key=lambda item: item.similarity_score, reverse=True)
    return DuplicationDocumentScore(
        overall_score=round(overall_score, 4),
        template_density=round(min(1.0, template_density / 4), 4),
        duplicate_sentence_ratio=round(min(1.0, duplicate_sentence_ratio), 4),
        max_section_score=round(max_section_score, 4),
        evidence_count=len(matches),
        section_scores=section_scores,
        matches=matches[:16],
    )


def _normalize(text: str) -> str:
    return SPACE_RE.sub("", text.strip())


def _char_shingles(text: str, size: int = 6) -> set[str]:
    if len(text) <= size:
        return {text} if text else set()
    return {text[index : index + size] for index in range(len(text) - size + 1)}


def _extract_sentences(text: str) -> list[str]:
    return [
        item.strip() for item in SENTENCE_RE.findall(text) if len(item.strip()) >= 18
    ]


def _jaccard(first: set[str], second: set[str]) -> float:
    if not first or not second:
        return 0.0
    intersection = len(first & second)
    union = len(first | second)
    return intersection / union if union else 0.0


def _quote_ratio(text: str) -> float:
    quoted = re.findall(r"[“\"]([^”\"]+)[”\"]", text)
    quoted_chars = sum(len(item) for item in quoted)
    return min(1.0, quoted_chars / max(len(text), 1))


def _build_reasons(
    best_similarity: float,
    template_hits: list[str],
    duplicate_sentences: list[str],
    quote_ratio: float,
) -> list[str]:
    reasons: list[str] = []
    if best_similarity >= 0.45:
        reasons.append("与文内其他段落存在较明显的重复表达")
    elif best_similarity >= 0.24:
        reasons.append("与文内其他段落存在一定程度的改写重合")
    if len(template_hits) >= 2:
        reasons.append("模板化学术表达偏多，容易抬高预检重复风险")
    elif template_hits:
        reasons.append("出现通用模板句式，建议替换为与你研究更贴合的表达")
    if len(duplicate_sentences) >= 2:
        reasons.append("存在重复句式，建议合并或重写重复表述")
    if quote_ratio >= 0.18:
        reasons.append("本段含较多引用内容，正式送检前请再次核对引用格式")
    if not reasons:
        reasons.append("当前段落重复风险较低，但仍建议结合真实引用规范复核")
    return reasons[:4]


def _risk_level(score: float) -> str:
    if score >= 0.58:
        return "high"
    if score >= 0.32:
        return "medium"
    return "low"
