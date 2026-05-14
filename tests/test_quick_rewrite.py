from fastapi.testclient import TestClient


def test_quick_rewrite_returns_structured_phrase_marks(client: TestClient) -> None:
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
    assert "旅游" in payload["rewrittenText"]
    assert "营销" in payload["rewrittenText"]
    assert "教学" not in payload["rewrittenText"]
    assert "系统实施" not in payload["rewrittenText"]
    assert payload["afterRisk"]["score"] >= 28

    first_phrase = payload["riskyPhrases"][0]
    assert {"text", "reason", "start", "end"}.issubset(first_phrase)
    assert "<" not in payload["rewrittenText"]


def test_quick_rewrite_allows_unlimited_trial_usage(client: TestClient) -> None:
    long_text = "这是一段用于测试短句优化不限字数策略的论文内容。" * 80
    response = client.post(
        "/api/quick-rewrite",
        json={"text": long_text, "mode": "polish"},
    )

    assert response.status_code == 200
    assert response.json()["remainingFreeUses"] is None

    sample = "首先分析理论基础，其次讨论现实问题，最后提出优化路径。该研究具有重要意义。"
    for _ in range(6):
        ok = client.post("/api/quick-rewrite", json={"text": sample, "mode": "aigc"})
        assert ok.status_code == 200
