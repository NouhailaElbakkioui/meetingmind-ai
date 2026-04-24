from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "MeetingMind AI"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://meetingmind:secret@localhost:5432/meetingmind"

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "meetings"

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = "meetingmind-audio"
    aws_region: str = "eu-west-1"

    # MLflow
    mlflow_tracking_uri: str = "http://localhost:5000"
    mlflow_experiment: str = "meetingmind-nlp"

    # Whisper
    whisper_model: str = "base"  # tiny | base | small | medium | large

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
