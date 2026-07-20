from pydantic_settings import BaseSettings
from pydantic import Field  
class Settings(BaseSettings):
    model_config = {
        "extra": "ignore",
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }
    APP_NAME: str = "SPRIDS Agent Platform"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"          
    LOG_DIR: str = "logs"             
    # 已有，⽇志级别
    # ⽇志⽬录（相对于 backend/）
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 单⽂件最⼤ 10MB
    LOG_BACKUP_COUNT: int = 5         
    # 保留 5 份历史⽇志
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "SPRIDS_agent"
    DB_USER: str = Field(..., description="数据库用户名")          # 无默认值，必须从 .env 读取
    DB_PASSWORD: str = Field(..., description="数据库密码")        # 无默认值，必须从 .env 读取


    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "sprids-agent-images"
    MINIO_SECURE: bool = False

    JWT_SECRET_KEY: str = Field(..., description="JWT 加密密钥")   # 无默认值，必须从 .env 读取
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    ALLOWED_ORIGINS: str = (
        "http://localhost:3000,http://localhost:5173,http://localhost:8080"
    )

    @property
    def cors_origins_list(self) -> list:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"

    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.siliconflow.cn/v1"
    DEEPSEEK_MODEL: str = "deepseek-ai/DeepSeek-V3.2"

    @property
    def effective_llm_api_key(self) -> str:
        return self.LLM_API_KEY or self.DEEPSEEK_API_KEY or self.QWEN_API_KEY or self.OPENAI_API_KEY

    @property
    def effective_llm_base_url(self) -> str:
        if self.LLM_API_KEY:
            return self.LLM_BASE_URL
        if self.DEEPSEEK_API_KEY:
            return self.DEEPSEEK_BASE_URL
        if self.QWEN_API_KEY:
            return self.QWEN_BASE_URL
        return self.OPENAI_BASE_URL

    @property
    def effective_llm_model(self) -> str:
        if self.LLM_API_KEY:
            return self.LLM_MODEL_NAME
        if self.DEEPSEEK_API_KEY:
            return self.DEEPSEEK_MODEL
        if self.QWEN_API_KEY:
            return self.QWEN_MODEL
        return self.OPENAI_MODEL

    LLM_MODEL_NAME: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096
    LLM_TIMEOUT: int = 60

    LLM_PROVIDER: str = "qwen"
    USE_LOCAL_LLM: bool = False

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen-plus"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL_NAME: str = "llama3.2:3b"
    OLLAMA_MODEL: str = "llama3.2:3b"

    AGENT_TOOL_ENABLED: bool = True
    AGENT_MAX_HISTORY_LENGTH: int = 20

    CHAT_PERSONA: str = "phrolova"

settings = Settings()