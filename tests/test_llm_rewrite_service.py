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
