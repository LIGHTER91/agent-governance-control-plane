from fastapi import FastAPI
from pydantic import BaseModel

from agent_governance_api.agents import router as agents_router
from agent_governance_api.config import get_settings
from agent_governance_api.logging_config import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.include_router(agents_router)


class HealthResponse(BaseModel):
    status: str
    service: str
    environment: str


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
    )
