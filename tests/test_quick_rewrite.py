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


def test_quick_rewrite_flags_template_value_claims_without_flooding_normal_text(client: TestClient) -> None:
    response = client.post(
        "/api/quick-rewrite",
        json={
            "text": (
                "随着人工智能技术的发展，个人财务管理系统在日常生活中发挥着越来越重要的作用。"
                "该系统能够帮助用户提高财务管理效率，具有较强的现实意义，并为相关研究提供一定参考价值。"
            ),
            "mode": "auto",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["beforeRisk"]["level"] in {"medium", "high"}
    assert payload["beforeRisk"]["score"] > payload["afterRisk"]["score"]
    assert 2 <= len(payload["riskyPhrases"]) <= 6
    assert payload["improvedPhrases"]
    assert payload["recommendedMode"] == "aigc"
    assert "越来越重要的作用" not in payload["rewrittenText"]
    assert "较强的现实意义" not in payload["rewrittenText"]


def test_quick_rewrite_does_not_penalize_concrete_technical_evidence_as_long_sentence(client: TestClient) -> None:
    response = client.post(
        "/api/quick-rewrite",
        json={
            "text": (
                "本系统使用 SpringBoot 3.1.5、Vue 3 和 MySQL 8.0 完成账单录入、预算提醒和月度统计模块，"
                "Postman 接口测试平均响应时间为 180ms。"
            ),
            "mode": "auto",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["beforeRisk"]["level"] == "normal"
    assert len(payload["riskyPhrases"]) == 0
    assert len(payload["improvedPhrases"]) == 0
    assert "SpringBoot 3.1.5" in payload["rewrittenText"]
    assert "180ms" in payload["rewrittenText"]


def test_quick_rewrite_turns_problem_chain_into_direct_rewrite(client: TestClient) -> None:
    response = client.post(
        "/api/quick-rewrite",
        json={
            "text": (
                "随着绿色生活理念的普及和“阳台经济”的兴起，家庭园艺正逐渐从一种单纯的爱好转变为一种主流的生活方式。"
                "然而，本土的绿色植物种子电商平台普遍存在产品信息不规范、专业种植知识服务碎片化、用户社区互动性弱以及库存精细化管理缺失等问题。"
                "这使得平台难以满足消费者对于透明度、系统性指导以及情感交流的深层需求。"
            ),
            "mode": "auto",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["beforeRisk"]["score"] > payload["afterRisk"]["score"]
    assert "后续可结合" not in payload["rewrittenText"]
    assert "这类平台的问题主要集中在四个环节" in payload["rewrittenText"]
    assert "核对产品信息" in payload["rewrittenText"]
    assert "查找连续的种植指导" in payload["rewrittenText"]
    assert "直接替换" not in payload["rewrittenText"]


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
