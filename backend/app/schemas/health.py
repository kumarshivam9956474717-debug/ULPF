from typing import Dict
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok")
    service: str = Field(default="ULPF")
    version: str = Field(default="1.0.0")
    readiness_components: Dict[str, str] = Field(default_factory=dict)

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "ok",
                "service": "ULPF",
                "version": "1.0.0",
                "readiness_components": {
                    "api": "HEALTHY",
                    "database": "HEALTHY",
                    "parser_registry": "HEALTHY",
                    "ingestion": "HEALTHY",
                    "analytics": "HEALTHY",
                    "anomaly_engine": "HEALTHY",
                    "supervisory_engine": "HEALTHY"
                }
            }
        }
    }


