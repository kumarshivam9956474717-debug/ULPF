from typing import List, Union, Optional
import os
from pydantic import field_validator

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    _has_pydantic_settings = True
except ImportError:
    from pydantic import BaseModel as BaseSettings
    SettingsConfigDict = None
    _has_pydantic_settings = False


class Settings(BaseSettings):
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Universal Log Pre-processing Framework")
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = os.getenv("API_V1_PREFIX", "/api/v1")

    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))

    # Cross-Origin Resource Sharing
    ALLOWED_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    # Authentication & RBAC Security Settings
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "omnilogix_ulpf_super_secure_jwt_secret_key_2026_sih_ntro_airgap_token_signing_key_32bytes"
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # Air-Gapped Administrator Bootstrap Settings
    ADMIN_BOOTSTRAP_USERNAME: Optional[str] = os.getenv("ADMIN_BOOTSTRAP_USERNAME", None)
    ADMIN_BOOTSTRAP_PASSWORD: Optional[str] = os.getenv("ADMIN_BOOTSTRAP_PASSWORD", None)
    ADMIN_BOOTSTRAP_EMAIL: Optional[str] = os.getenv("ADMIN_BOOTSTRAP_EMAIL", "admin@omnilogix.local")

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return [v]

    # Database
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "ulpf_db")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "ulpf_admin")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "ulpf_dev_password")
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://ulpf_admin:ulpf_dev_password@localhost:5432/ulpf_db"
    )

    # Air-Gapped / Offline Operational Flags
    AIR_GAPPED_MODE: bool = os.getenv("AIR_GAPPED_MODE", "True").lower() in ("true", "1", "t")
    ALLOW_EXTERNAL_CALLS: bool = False

    # Live Syslog Ingestion Engine Settings
    SYSLOG_ENABLED: bool = os.getenv("SYSLOG_ENABLED", "False").lower() in ("true", "1", "t")
    SYSLOG_ALLOW_API_CONTROL: bool = os.getenv("SYSLOG_ALLOW_API_CONTROL", "True").lower() in ("true", "1", "t")

    SYSLOG_UDP_ENABLED: bool = os.getenv("SYSLOG_UDP_ENABLED", "True").lower() in ("true", "1", "t")
    SYSLOG_UDP_HOST: str = os.getenv("SYSLOG_UDP_HOST", "0.0.0.0")
    SYSLOG_UDP_PORT: int = int(os.getenv("SYSLOG_UDP_PORT", "1514"))

    SYSLOG_TCP_ENABLED: bool = os.getenv("SYSLOG_TCP_ENABLED", "True").lower() in ("true", "1", "t")
    SYSLOG_TCP_HOST: str = os.getenv("SYSLOG_TCP_HOST", "0.0.0.0")
    SYSLOG_TCP_PORT: int = int(os.getenv("SYSLOG_TCP_PORT", "1514"))

    SYSLOG_TLS_ENABLED: bool = os.getenv("SYSLOG_TLS_ENABLED", "False").lower() in ("true", "1", "t")
    SYSLOG_TLS_HOST: str = os.getenv("SYSLOG_TLS_HOST", "0.0.0.0")
    SYSLOG_TLS_PORT: int = int(os.getenv("SYSLOG_TLS_PORT", "16514"))

    SYSLOG_MAX_MESSAGE_BYTES: int = int(os.getenv("SYSLOG_MAX_MESSAGE_BYTES", "65536"))
    SYSLOG_QUEUE_MAXSIZE: int = int(os.getenv("SYSLOG_QUEUE_MAXSIZE", "10000"))
    SYSLOG_WORKERS: int = int(os.getenv("SYSLOG_WORKERS", "4"))
    SYSLOG_TCP_IDLE_TIMEOUT_SECONDS: int = int(os.getenv("SYSLOG_TCP_IDLE_TIMEOUT_SECONDS", "60"))
    SYSLOG_TCP_CONNECTION_LIMIT: int = int(os.getenv("SYSLOG_TCP_CONNECTION_LIMIT", "100"))

    SYSLOG_TLS_CERTFILE: Optional[str] = os.getenv("SYSLOG_TLS_CERTFILE", None)
    SYSLOG_TLS_KEYFILE: Optional[str] = os.getenv("SYSLOG_TLS_KEYFILE", None)
    SYSLOG_TLS_CAFILE: Optional[str] = os.getenv("SYSLOG_TLS_CAFILE", None)

    # Phase 4B: Parquet Columnar Export Settings
    ULPF_PARQUET_EXPORT_DIR: str = os.getenv("ULPF_PARQUET_EXPORT_DIR", "./data/processed")
    ULPF_EXPORT_BATCH_SIZE: int = int(os.getenv("ULPF_EXPORT_BATCH_SIZE", "10000"))

    # Phase 4B: Offline Anomaly Detection Settings
    ULPF_ANOMALY_CONTAMINATION: float = float(os.getenv("ULPF_ANOMALY_CONTAMINATION", "0.01"))
    ULPF_ANOMALY_RANDOM_STATE: int = int(os.getenv("ULPF_ANOMALY_RANDOM_STATE", "42"))
    ULPF_ANOMALY_MIN_TRAIN_RECORDS: int = int(os.getenv("ULPF_ANOMALY_MIN_TRAIN_RECORDS", "20"))

    # Step 4: High-Throughput Decoupled Persistence & Scalability Settings
    PERSISTENCE_MODE: str = os.getenv("PERSISTENCE_MODE", "batch")  # "batch", "single", "parquet", "streaming"
    PERSISTENCE_BATCH_SIZE: int = int(os.getenv("PERSISTENCE_BATCH_SIZE", "500"))
    PERSISTENCE_FLUSH_INTERVAL_MS: int = int(os.getenv("PERSISTENCE_FLUSH_INTERVAL_MS", "100"))
    PERSISTENCE_QUEUE_MAX_SIZE: int = int(os.getenv("PERSISTENCE_QUEUE_MAX_SIZE", "50000"))
    PERSISTENCE_MAX_RETRIES: int = int(os.getenv("PERSISTENCE_MAX_RETRIES", "3"))

    # Database Connection Pool Settings
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "30"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))


    if _has_pydantic_settings:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=True,
            extra="ignore"
        )
    else:
        model_config = {
            "extra": "ignore"
        }



settings = Settings()

