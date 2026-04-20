"""配置加载 - 对应 Java 版的 @Value + application.yml"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """应用配置。自动从 .env 读取，环境变量名即字段名大写。"""

    # ===== DeepSeek =====
    deepseek_api_key: str = Field(default="", description="DeepSeek API Key")
    deepseek_base_url: str = Field(default="https://api.deepseek.com")
    deepseek_model: str = Field(default="deepseek-chat")

    # ===== Anthropic(留口) =====
    anthropic_api_key: str = Field(default="")
    anthropic_base_url: str = Field(default="https://api.anthropic.com")
    anthropic_model: str = Field(default="claude-sonnet-4-5")

    # ===== 运行配置 =====
    default_provider: str = Field(default="deepseek")
    app_port: int = Field(default=8100)
    app_host: str = Field(default="0.0.0.0")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # DEEPSEEK_API_KEY 和 deepseek_api_key 都识别
        extra="ignore",          # .env 里多余字段不报错
    )


# 全局单例。FastAPI 的依赖注入会用到它
settings = Settings()
