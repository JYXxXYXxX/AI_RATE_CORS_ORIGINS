from functools import lru_cache
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "AI Rate Detector Service"
    service_version: str = "0.3.0"
    service_env: Literal["dev", "prod", "test"] = "dev"
    max_text_chars: int = Field(default=250_000, ge=1_000)
    max_upload_bytes: int = Field(default=50 * 1024 * 1024, ge=1024)
    min_segment_chars: int = Field(default=80, ge=20)
    target_segment_chars: int = Field(default=420, ge=120)
    sliding_window_chars: int = Field(default=560, ge=180)
    sliding_window_overlap_chars: int = Field(default=120, ge=0)
    max_jobs: int = Field(default=200, ge=10)
    calibration_store_path: str = "data/calibration_samples.jsonl"
    calibration_min_samples: int = Field(default=12, ge=1)
    database_url: str = (
        "postgresql://postgres:postgres@localhost:5432/paper_risk_platform"
    )
    database_pool_min: int = Field(default=1, ge=1)
    database_pool_max: int = Field(default=10, ge=1)
    upload_storage_dir: str = "data/uploads"
    cleaned_storage_dir: str = "data/cleaned"
    feedback_storage_dir: str = "data/feedback"
    feedback_learning_store_path: str = "data/feedback_learning_samples.jsonl"
    feedback_private_learning_dir: str = "data/feedback_private_learning"
    feedback_learning_skill_path: str = "data/feedback_learning_skill/SKILL.md"
    model_artifact_dir: str = "data/models"
    local_dup_model_version: str = "local-dup-0.1.0"
    unified_proxy_model_version: str = "cnki-proxy-mvp-0.1.0"
    proxy_training_min_samples: int = Field(default=6, ge=1)
    proxy_feature_version: str = "proxy-features-0.1.0"
    provider_configs_json: str = "{}"
    provider_registry_path: str = "data/provider_configs.json"
    provider_request_timeout_seconds: int = Field(default=30, ge=1)
    provider_files_base_path: str = "data/provider_results"
    auto_train_enabled: bool = False
    auto_train_every_feedbacks: int = Field(default=5, ge=1)
    auth_session_ttl_hours: int = Field(default=24 * 14, ge=1)
    starter_credits: int = Field(default=2, ge=0)
    analysis_credit_cost: int = Field(default=1, ge=1)
    async_queue_backend: Literal["local", "celery"] = "local"
    celery_broker_url: str = "redis://127.0.0.1:6379/0"
    celery_result_backend: str | None = None
    celery_queue_name: str = "analysis"
    payment_callback_secret: str | None = None
    payment_public_base_url: str = "http://127.0.0.1:8010"
    alipay_app_id: str | None = None
    alipay_gateway_url: str = "https://openapi.alipay.com/gateway.do"
    alipay_notify_url: str | None = None
    alipay_private_key_path: str | None = None
    alipay_public_key_path: str | None = None
    alipay_sandbox_enabled: bool = False
    mock_payment_enabled: bool = False
    wechat_mchid: str | None = None
    wechat_appid: str | None = None
    wechat_notify_url: str | None = None
    wechat_api_v3_key: str | None = None
    wechat_private_key_path: str | None = None
    wechat_serial_no: str | None = None
    cors_origins: str = ""
    cookie_secure: bool = False
    cookie_max_age_seconds: int = Field(default=60 * 60 * 24 * 14, ge=3600)
    llm_provider: Literal["kimi", "openai", "yunwu", "codex", "none"] = "none"
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.moonshot.cn/v1"
    llm_model: str = "moonshot-v1-32k"
    llm_max_tokens: int = Field(default=4096, ge=512)
    llm_temperature: float = Field(default=0.5, ge=0.0, le=2.0)
    llm_timeout_seconds: int = Field(default=30, ge=5)
    llm_max_retries: int = Field(default=2, ge=1, le=6)
    llm_rewrite_enabled: bool = False
    onlyoffice_enabled: bool = False
    onlyoffice_document_server_url: str | None = None
    onlyoffice_jwt_secret: str | None = None
    onlyoffice_backend_base_url: str = "http://host.docker.internal:8010"

    data_retention_days: int = Field(default=90, ge=1)

    model_config = {
        "env_prefix": "AI_RATE_",
        "env_file": ".env",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
