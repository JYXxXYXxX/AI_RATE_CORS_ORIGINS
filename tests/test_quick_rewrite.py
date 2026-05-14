from fastapi.testclient import TestClient

from app.routes.quick_rewrite import _usage_by_day


def test_quick_rewrite_returns_structured_phrase_marks(client: TestClient) -> None:
    _usage_by_day.clear()
    response = client.post(
        "/api/quick-rewrite",
        json={
            "text": (
                "随着人工智能技术的发展，旅游企业必须不断引入创新并结合有效营销策略。"
                "该研究具有重要意义，并能够为相关实践提供参考价值。"
            ),
            "mode": "auto",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["originalText"]
    assert payload["rewrittenText"]
    assert payload["beforeRisk"]["score"] > payload["afterRisk"]["score"]
    assert payload["riskyPhrases"]
    assert payload["improvedPhrases"]
    assert payload["rewritePrinciples"]
    assert payload["disclaimer"] == "该结果为系统预估，不等同于知网检测结果。"

    first_phrase = payload["riskyPhrases"][0]
    assert {"text", "reason", "start", "end"}.issubset(first_phrase)
    assert "<" not in payload["rewrittenText"]


def test_quick_rewrite_enforces_free_limits(client: TestClient) -> None:
    _usage_by_day.clear()
    long_text = "这是一段用于测试免费短句优化字数限制的论文内容。" * 30
    response = client.post(
        "/api/quick-rewrite",
        json={"text": long_text, "mode": "polish"},
    )

    assert response.status_code == 400
    assert "免费试用每次最多 300 字" in response.json()["detail"]

    sample = "首先分析理论基础，其次讨论现实问题，最后提出优化路径。该研究具有重要意义。"
    for _ in range(3):
        ok = client.post("/api/quick-rewrite", json={"text": sample, "mode": "aigc"})
        assert ok.status_code == 200

    limited = client.post("/api/quick-rewrite", json={"text": sample, "mode": "aigc"})
    assert limited.status_code == 429
