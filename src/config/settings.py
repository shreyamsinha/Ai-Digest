from dotenv import load_dotenv
from pydantic import BaseModel, Field
import os

load_dotenv()

def _to_bool(v: str | None, default: bool = False) -> bool:
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}

def _to_int(v: str | None, default: int) -> int:
    if v is None or not v.strip():
        return default
    return int(v.strip())

def _to_list(v: str | None) -> list[str]:
    if v is None or not v.strip():
        return []
    return [x.strip().lower() for x in v.split(",") if x.strip()]

def _to_float(v: str | None, default: float) -> float:
    if v is None or not v.strip():
        return default
    return float(v.strip())



class Settings(BaseModel):
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.1:8b")

    persona_genai_news_enabled: bool = Field(default=True)
    persona_product_ideas_enabled: bool = Field(default=True)

    time_window_hours: int = Field(default=24)
    log_level: str = Field(default="INFO")

    database_url: str = Field(default="sqlite:///data/digest.db")
    
    eval_max_items: int = Field(default=10)
    ollama_temperature: float = Field(default=0.1)

    telegram_enabled: bool = Field(default=False)
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")
    log_file: str = Field(default="logs/run.log")

    ollama_embed_model: str = Field(default="nomic-embed-text")
    dedup_sim_threshold: float = Field(default=0.86)

    genai_news_min_score: int = Field(default=65)
    product_ideas_min_score: int = Field(default=60)

    telegram_parse_mode: str = Field(default="MarkdownV2")
    telegram_max_items: int = Field(default=6)




    @property
    def personas_enabled(self) -> list[str]:
        personas = []
        if self.persona_genai_news_enabled:
            personas.append("GENAI_NEWS")
        if self.persona_product_ideas_enabled:
            personas.append("PRODUCT_IDEAS")
        return personas
    
    hn_min_score: int = Field(default=30)
    hn_require_keywords: bool = Field(default=False)
    hn_keywords: list[str] = Field(default_factory=list)
    hn_blocklist: list[str] = Field(default_factory=list)


_settings: Settings | None = None

def get_settings() -> Settings:
    global _settings
    if _settings is not None:
        return _settings

    _settings = Settings(
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
        persona_genai_news_enabled=_to_bool(os.getenv("PERSONA_GENAI_NEWS_ENABLED"), True),
        persona_product_ideas_enabled=_to_bool(os.getenv("PERSONA_PRODUCT_IDEAS_ENABLED"), True),
        time_window_hours=int(os.getenv("TIME_WINDOW_HOURS", "24")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        database_url=os.getenv("DATABASE_URL", "sqlite:///data/digest.db"),
        hn_min_score=_to_int(os.getenv("HN_MIN_SCORE"), 30),
        hn_require_keywords=_to_bool(os.getenv("HN_REQUIRE_KEYWORDS"), False),
        hn_keywords=_to_list(os.getenv("HN_KEYWORDS")),
        hn_blocklist=_to_list(os.getenv("HN_BLOCKLIST")),
        eval_max_items=_to_int(os.getenv("EVAL_MAX_ITEMS"), 10),
        ollama_temperature=_to_float(os.getenv("OLLAMA_TEMPERATURE"), 0.1),
        telegram_enabled=_to_bool(os.getenv("TELEGRAM_ENABLED"), False),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        log_file=os.getenv("LOG_FILE", "logs/run.log"),
        ollama_embed_model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"),
        dedup_sim_threshold=float(os.getenv("DEDUP_SIM_THRESHOLD", "0.86")),

        genai_news_min_score=int(os.getenv("GENAI_NEWS_MIN_SCORE", "65")),
        product_ideas_min_score=int(os.getenv("PRODUCT_IDEAS_MIN_SCORE", "60")),

        telegram_parse_mode=os.getenv("TELEGRAM_PARSE_MODE", "MarkdownV2"),
        telegram_max_items=int(os.getenv("TELEGRAM_MAX_ITEMS", "6")),



    )
    return _settings
