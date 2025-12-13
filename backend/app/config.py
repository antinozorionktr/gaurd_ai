from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://priyanshu:priyanshu@localhost:5432/smart_gate_db"
    
    # Application
    SECRET_KEY: str = "your-super-secret-key"
    DEBUG: bool = True
    API_HOST: str = "localhost"
    API_PORT: int = 8000
    
    # Face Recognition Settings (DeepFace with FaceNet512)
    FACE_STORAGE_PATH: str = "./face_data"  # Local storage for face embeddings
    FACE_MATCH_THRESHOLD: float = 0.40  # Cosine distance threshold (lower = stricter)
    WATCHLIST_ALERT_THRESHOLD: float = 0.35  # Stricter threshold for watchlist
    FACE_QUALITY_THRESHOLD: float = 0.70  # Minimum face detection confidence
    
    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
