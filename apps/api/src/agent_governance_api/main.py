from fastapi import FastAPI
from pydantic import BaseModel

from agent_governance_api.access_grants import router as access_grants_router
from agent_governance_api.agents import router as agents_router
from agent_governance_api.capabilities import router as capabilities_router
from agent_governance_api.config import get_settings
from agent_governance_api.human_approvals import router as human_approvals_router
from agent_governance_api.logging_config import configure_logging
from agent_governance_api.model_assets import router as model_assets_router
from agent_governance_api.policies import router as policies_router
from agent_governance_api.policy_check_steps import (
    policy_rules_router as policy_check_steps_policy_rules_router,
)
from agent_governance_api.policy_check_steps import router as policy_check_steps_router
from agent_governance_api.policy_rules import router as policy_rules_router
from agent_governance_api.policy_versions import (
    policies_router as policy_versions_policies_router,
)
from agent_governance_api.policy_versions import router as policy_versions_router
from agent_governance_api.runtime_gateway_api import router as runtime_gateway_router
from agent_governance_api.sources import router as sources_router
from agent_governance_api.telemetry_api import router as telemetry_router

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.include_router(access_grants_router)
app.include_router(agents_router)
app.include_router(capabilities_router)
app.include_router(human_approvals_router)
app.include_router(model_assets_router)
app.include_router(policies_router)
app.include_router(policy_versions_policies_router)
app.include_router(policy_versions_router)
app.include_router(policy_check_steps_router)
app.include_router(policy_check_steps_policy_rules_router)
app.include_router(policy_rules_router)
app.include_router(runtime_gateway_router)
app.include_router(sources_router)
app.include_router(telemetry_router)


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
