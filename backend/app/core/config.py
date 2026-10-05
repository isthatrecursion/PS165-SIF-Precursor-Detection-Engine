"""
Application configuration — loaded from .env
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite+aiosqlite:///./sih165.db"

    # Auth
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # Model paths
    stage1_tfidf_path: str = "../ml/models/stage1_tfidf.pkl"
    stage1_logreg_path: str = "../ml/models/stage1_logreg.pkl"
    stage2_transformer_path: str = "../ml/models/stage2_transformer"
    stage2_xgb_path: str = "../ml/models/stage2_xgb.pkl"
    stage2_scaler_path: str = "../ml/models/stage2_scaler.pkl"
    stage2_calibration_path: str = "../ml/models/stage2_platt.pkl"
    stage2_ood_path: str = "../ml/models/stage2_ood.pkl"

    # Pipeline thresholds
    ocr_confidence_threshold: float = 0.6
    ood_threshold: float = 3.5
    recall_floor: float = 0.90

    # Environment
    environment: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
