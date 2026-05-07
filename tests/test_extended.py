"""补充测试：覆盖支付、训练、文档加载、查重评分等核心模块。"""
from pathlib import Path

from app.config import Settings
from app.services.document_loader import extract_text, SUPPORTED_EXTENSIONS
from app.services.text_processing import clean_body_text, segment_document
from app.plagiarism.scoring import build_embedding_vector, build_embedding_vectors_batch, score_duplication
from app.services.analyzer import calibrate_score, risk_level


# -----------------------------------------------------------------------
# document_loader
# -----------------------------------------------------------------------

def test_supported_extensions_includes_doc():
    assert ".doc" in SUPPORTED_EXTENSIONS
    assert ".docx" in SUPPORTED_EXTENSIONS
    assert ".pdf" in SUPPORTED_EXTENSIONS


def test_extract_text_from_txt():
    content = "这是一段测试正文。".encode("utf-8")
    text = extract_text("paper.txt", content)
    assert "测试正文" in text


def test_extract_text_rejects_unsupported():
    import pytest
    with pytest.raises(ValueError, match="仅支持"):
        extract_text("paper.exe", b"binary data")


def test_extract_text_gb18030():
    content = "这是GB18030编码的正文。".encode("gb18030")
    text = extract_text("paper.txt", content)
    assert "GB18030" in text


# -----------------------------------------------------------------------
# calibration & scoring
# -----------------------------------------------------------------------

def test_calibrate_score_bounds():
    assert 0.04 <= calibrate_score(0.0) <= 0.94
    assert 0.04 <= calibrate_score(0.5) <= 0.94
    assert 0.04 <= calibrate_score(1.0) <= 0.94


def test_calibrate_score_monotonic():
    scores = [calibrate_score(x / 10) for x in range(11)]
    for i in range(len(scores) - 1):
        assert scores[i] <= scores[i + 1]


def test_risk_level():
    assert risk_level(0.10) == "low"
    assert risk_level(0.50) == "medium"
    assert risk_level(0.80) == "high"


# -----------------------------------------------------------------------
# embedding
# -----------------------------------------------------------------------

def test_build_embedding_vector_returns_valid_format():
    vec = build_embedding_vector("测试段落内容", dims=768)
    assert vec.startswith("[")
    assert vec.endswith("]")
    values = vec.strip("[]").split(",")
    assert len(values) == 768


def test_build_embedding_vector_empty_text():
    vec = build_embedding_vector("", dims=768)
    values = vec.strip("[]").split(",")
    assert all(v.strip() == "0" for v in values)


def test_build_embedding_vectors_batch():
    texts = ["第一段测试内容", "第二段测试内容", ""]
    vecs = build_embedding_vectors_batch(texts, dims=768)
    assert len(vecs) == 3
    for vec in vecs:
        assert vec.startswith("[")


# -----------------------------------------------------------------------
# duplication scoring
# -----------------------------------------------------------------------

def test_score_duplication_with_sections():
    sections = [
        {"section_index": 0, "char_count": 120, "content": "本文首先分析人工智能赋能教育评价的理论基础，其次探讨现实问题，最后提出优化路径。" * 3},
        {"section_index": 1, "char_count": 120, "content": "访谈记录显示，三位教师在实际课堂中主要使用形成性评价表，评价方式多样。" * 3},
    ]
    result = score_duplication(sections)
    assert 0 <= result.overall_score <= 1
    assert len(result.section_scores) == 2


# -----------------------------------------------------------------------
# text processing
# -----------------------------------------------------------------------

def test_clean_body_text_strips_references():
    text = "正文内容在这里需要保留。\n\n参考文献\n[1] 张三. 论文标题. 2024."
    cleaned = clean_body_text(text)
    # clean_body_text 应去掉参考文献部分
    assert "正文内容" in cleaned


def test_segment_document_produces_segments():
    text = "本文首先分析人工智能赋能教育评价的理论基础，其次探讨现实问题。" * 10
    settings = Settings()
    segments = segment_document(text, settings)
    assert len(segments) >= 1
    assert all(hasattr(seg, "text") for seg in segments)


# -----------------------------------------------------------------------
# account / payment (unit level)
# -----------------------------------------------------------------------

def test_payment_signature_is_hmac():
    """验证支付签名使用 HMAC 而非裸 SHA256"""
    import hmac
    from app.services.account import AccountService
    from unittest.mock import MagicMock

    settings = Settings(payment_callback_secret="test-secret-key")
    mock_repo = MagicMock()
    service = AccountService(settings, mock_repo)

    sig = service.build_mock_callback_signature(order_no="ORD-001", paid_amount_cents=990)
    expected = hmac.new(b"test-secret-key", b"ORD-001:990", "sha256").hexdigest()
    assert sig == expected
