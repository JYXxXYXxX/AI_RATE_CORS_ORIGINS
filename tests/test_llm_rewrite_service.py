from app.config import Settings
from app.services.llm_rewrite import LLMRewriteService


def test_codex_provider_uses_responses_api() -> None:
    service = LLMRewriteService(
        Settings(
            llm_provider="codex",
            llm_api_key="test-key",
            llm_base_url="https://jmrai.net",
            llm_model="gpt-5.5",
            llm_rewrite_enabled=True,
        )
    )

    payload = service._request_payload("system", "user")

    assert service._request_url() == "https://jmrai.net/v1/responses"
    assert payload["model"] == "gpt-5.5"
    assert payload["max_output_tokens"] == 4096
    assert payload["input"][0]["content"][0]["type"] == "input_text"
    assert payload["input"][1]["content"][0]["text"] == "user"


def test_codex_response_text_is_extracted_from_output() -> None:
    service = LLMRewriteService(
        Settings(
            llm_provider="codex",
            llm_api_key="test-key",
            llm_base_url="https://jmrai.net",
            llm_model="gpt-5.5",
            llm_rewrite_enabled=True,
        )
    )
    data = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": '{"diagnosis":"ok","sentences":[]}',
                    }
                ],
            }
        ]
    }

    assert service._extract_llm_content(data) == '{"diagnosis":"ok","sentences":[]}'


def test_llm_parser_accepts_json_wrapped_in_code_fences() -> None:
    service = LLMRewriteService(
        Settings(
            llm_provider="codex",
            llm_api_key="test-key",
            llm_base_url="https://jmrai.net",
            llm_model="gpt-5.5",
            llm_rewrite_enabled=True,
        )
    )

    parsed = service._parse_json_result(
        """```json
{"diagnosis":"ok","sentences":[],"rewritten_paragraph":"重写后"}
```"""
    )

    assert parsed is not None
    assert parsed["rewritten_paragraph"] == "重写后"


def test_normalize_rewrite_result_falls_back_when_model_returns_original_text() -> None:
    service = LLMRewriteService(
        Settings(
            llm_provider="codex",
            llm_api_key="test-key",
            llm_base_url="https://jmrai.net",
            llm_model="gpt-5.5",
            llm_rewrite_enabled=True,
        )
    )
    text = (
        "针对上述痛点，本研究设计并实现了一个专注于家庭园艺场景的垂直电商平台。"
        "该平台的核心业务功能体系由五大模块构成。"
    )

    normalized = service._normalize_rewrite_result(
        raw_result={
            "diagnosis": "ok",
            "sentences": [],
            "rewritten_paragraph": text,
            "overall_advice": "",
        },
        text=text,
        risk_type="duplication",
        reasons=["句式重复"],
        cnki_dup_percent=None,
        cnki_aigc_percent=None,
    )

    assert normalized["rewritten_paragraph"]
    assert normalized["rewritten_paragraph"] != text
    assert normalized["sentences"]


def test_normalize_rewrite_result_rejects_expansive_paragraph_rewrite() -> None:
    service = LLMRewriteService(
        Settings(
            llm_provider="codex",
            llm_api_key="test-key",
            llm_base_url="https://jmrai.net",
            llm_model="gpt-5.5",
            llm_rewrite_enabled=True,
        )
    )
    text = (
        "针对上述痛点，本研究设计并实现了一个专注于家庭园艺场景的垂直电商平台。"
        "该平台的核心业务功能体系由五大模块构成，分别是用户权限管理、产品信息管理、订单处理、社区运营与服务以及供应链库存控制。"
    )

    normalized = service._normalize_rewrite_result(
        raw_result={
            "diagnosis": "ok",
            "sentences": [
                {
                    "original": "该平台的核心业务功能体系由五大模块构成，分别是用户权限管理、产品信息管理、订单处理、社区运营与服务以及供应链库存控制。",
                    "rewritten": "平台的主要功能分为五部分：用户权限管理、产品信息管理、订单处理、社区运营与服务，以及供应链库存控制。",
                    "risk": "high",
                    "explanation": "保留原有列举内容，只压缩套话表达。",
                }
            ],
            "rewritten_paragraph": "为回应前文提到的实际需求，本文将家庭园艺作为主要应用场景，完成了一个垂直类电商平台的设计与开发。在功能划分上，平台没有只停留在商品展示和交易环节，而是进一步拆分为五个部分。",
            "overall_advice": "",
        },
        text=text,
        risk_type="duplication",
        reasons=["句式过于工整"],
        cnki_dup_percent=None,
        cnki_aigc_percent=None,
    )

    assert "为回应前文提到的实际需求" not in normalized["rewritten_paragraph"]
    assert "平台的主要功能分为五部分" in normalized["rewritten_paragraph"]
    assert "家庭园艺场景的垂直电商平台" in normalized["rewritten_paragraph"]
