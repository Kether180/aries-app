from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # env_ignore_empty: a blank `DATABASE_URL=` in .env falls back to the default below
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    database_url: str = "sqlite:///./news.db"
    gnews_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-nano"
    cors_origins: list[str] = ["http://localhost:5173"]
    news_cache_seconds: int = 600

    @property
    def sqlalchemy_url(self) -> str:
        # Render/Railway hand out "postgres://" or "postgresql://" URLs;
        # SQLAlchemy needs the driver spelled out to use psycopg 3.
        url = self.database_url
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix) :]
        return url


settings = Settings()
