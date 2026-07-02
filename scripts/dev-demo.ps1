$ErrorActionPreference = "Stop"
Set-StrictMode -Version 3.0

$repoRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $repoRoot "compose.dev.yml"
$apiBaseUrl = if ($env:AGCP_DEMO_API_BASE_URL) {
    $env:AGCP_DEMO_API_BASE_URL.TrimEnd("/")
} else {
    "http://localhost:8000"
}
$webBaseUrl = if ($env:AGCP_DEMO_WEB_BASE_URL) {
    $env:AGCP_DEMO_WEB_BASE_URL.TrimEnd("/")
} else {
    "http://localhost:3000"
}

function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

function Stop-Demo {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

function Invoke-Compose {
    param([Parameter(Mandatory = $true)][string[]]$ComposeArgs)
    & docker compose -f $composeFile @ComposeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose command failed: docker compose -f compose.dev.yml $($ComposeArgs -join ' ')"
    }
}

Set-Location $repoRoot

Write-Step "Checking Docker Compose dev stack"
$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& docker version *> $null
$dockerVersionExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorActionPreference
if ($dockerVersionExitCode -ne 0) {
    Stop-Demo "Docker is not available. Start Docker Desktop, then run .\scripts\dev-up.ps1."
}

$runningServices = @()
try {
    $runningServices = @(Invoke-Compose @("ps", "--services", "--status", "running"))
} catch {
    Stop-Demo "Could not inspect the Compose stack. Start it with .\scripts\dev-up.ps1."
}

$requiredServices = @("db", "api", "web")
$missingServices = @($requiredServices | Where-Object { $_ -notin $runningServices })
if ($missingServices.Count -gt 0) {
    Stop-Demo "Docker Compose dev stack is not fully running. Missing: $($missingServices -join ', '). Start it with .\scripts\dev-up.ps1 or docker compose -f compose.dev.yml up --build."
}

Write-Step "Checking API health"
try {
    $health = Invoke-RestMethod -Method Get -Uri "$apiBaseUrl/health" -TimeoutSec 10
} catch {
    Stop-Demo "API health check failed at $apiBaseUrl/health. Check docker compose -f compose.dev.yml logs api."
}
if ($health.status -ne "ok") {
    Stop-Demo "API health check did not return status=ok."
}
Write-Host "API health: $($health.status)"

Write-Step "Checking Local Admin actor"
try {
    $me = Invoke-RestMethod -Method Get -Uri "$apiBaseUrl/me" -TimeoutSec 10
} catch {
    Stop-Demo "GET /me failed. Check API logs and local dev actor settings."
}
$roles = @($me.roles)
$requiredRoles = @("platform_admin", "reviewer", "auditor")
$missingRoles = @($requiredRoles | Where-Object { $_ -notin $roles })
if ($me.actor_id -ne "local-admin" -or $me.display_name -ne "Local Admin" -or $missingRoles.Count -gt 0) {
    Stop-Demo "Expected GET /me to return Local Admin with platform_admin, reviewer, auditor. Current actor_id=$($me.actor_id), display_name=$($me.display_name), roles=$($roles -join ', ')."
}
Write-Host "Current actor: $($me.display_name) <$($me.actor_id)> roles=$($roles -join ', ')"

Write-Step "Checking metadata pre-check feature flag in API container"
$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$preCheckFlagOutput = & docker compose -f $composeFile exec -T api printenv AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED 2>$null
$preCheckFlagExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousErrorActionPreference
$preCheckFlag = if ($preCheckFlagExitCode -eq 0) {
    (@($preCheckFlagOutput) | Select-Object -Last 1).Trim()
} else {
    ""
}
if ($preCheckFlag.ToLowerInvariant() -ne "true") {
    Stop-Demo "AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED is not true in the running API container. Restart the stack with .\scripts\dev-down.ps1 then .\scripts\dev-up.ps1."
}
Write-Host "AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED=$preCheckFlag"

Write-Step "Applying Alembic migrations"
Invoke-Compose @("exec", "-T", "api", "uv", "run", "alembic", "upgrade", "head") | Out-Host

Write-Step "Seeding deterministic local demo data"
Invoke-Compose @("exec", "-T", "api", "uv", "run", "python", "scripts/seed_full_stack_demo.py", "--apply") | Out-Host

Write-Step "Loading Runtime Gateway demo payload from backend helper"
$payloadOutput = Invoke-Compose @("exec", "-T", "api", "uv", "run", "python", "scripts/seed_full_stack_demo.py", "--print-runtime-payload")
$payloadJson = @($payloadOutput | Where-Object { $_.Trim().StartsWith("{") } | Select-Object -Last 1)
if (-not $payloadJson) {
    Stop-Demo "Could not load metadata pre-check demo payload JSON from scripts/seed_full_stack_demo.py. Check docker compose -f compose.dev.yml logs api."
}
try {
    $payload = $payloadJson | ConvertFrom-Json
} catch {
    Stop-Demo "Metadata pre-check demo payload was not valid JSON. Re-run scripts/seed_full_stack_demo.py --print-runtime-payload inside the API container."
}
$uniqueRunId = [guid]::NewGuid().ToString()
$requestSuffix = $uniqueRunId.Substring(0, 8)
$payload.run_id = $uniqueRunId
$payload.request_id = "metadata-precheck-demo-$requestSuffix"

Write-Step "Calling Runtime Gateway metadata-only pre-check scenario"
try {
    $decisionResponse = Invoke-RestMethod `
        -Method Post `
        -Uri "$apiBaseUrl/runtime/tool-calls/decision" `
        -ContentType "application/json" `
        -Body ($payload | ConvertTo-Json -Depth 20) `
        -TimeoutSec 30
} catch {
    Stop-Demo "Runtime Gateway demo call failed. Check API logs and ensure the demo seed completed."
}

Write-Step "Reading Evidence Bundle for real CheckResult evidence"
try {
    $evidenceBundle = Invoke-RestMethod `
        -Method Get `
        -Uri "$apiBaseUrl/agents/$($payload.agent_id)/evidence-bundle" `
        -TimeoutSec 30
} catch {
    Stop-Demo "Evidence Bundle read failed. Local Admin should include auditor role; check /me and API logs."
}

$policyDecisionId = [string]$decisionResponse.policy_decision_id
$policyDecision = @($evidenceBundle.policy_decisions) |
    Where-Object { [string]$_.id -eq $policyDecisionId } |
    Select-Object -First 1
$policyVersionId = if ($policyDecision) {
    [string]$policyDecision.policy_version_id
} else {
    "unavailable"
}
$checkResults = @($evidenceBundle.check_results) |
    Where-Object { [string]$_.policy_decision_id -eq $policyDecisionId }
$checkResultTypes = @($checkResults | ForEach-Object { $_.check_type } | Sort-Object -Unique)

if ($checkResults.Count -eq 0) {
    Stop-Demo "Runtime Gateway completed, but no CheckResults were linked to policy_decision_id=$policyDecisionId. Check the metadata pre-check flag and PolicyCheckStep seed."
}

Write-Host ""
Write-Host "Metadata-only pre-check demo complete"
Write-Host "Decision:           $($decisionResponse.decision)"
$proceedValue = ([string]$decisionResponse.proceed).ToLowerInvariant()
Write-Host "Proceed:            $proceedValue"
Write-Host "PolicyDecision id:  $policyDecisionId"
Write-Host "PolicyVersion id:   $policyVersionId"
Write-Host "CheckResults count: $($checkResults.Count)"
Write-Host "CheckResult types:  $($checkResultTypes -join ', ')"
Write-Host "HumanApproval id:   $($decisionResponse.human_approval_id)"

Write-Host ""
Write-Host "Open these local product surfaces:"
Write-Host "Policy Studio:      $webBaseUrl/policies"
Write-Host "Runtime Decisions:  $webBaseUrl/runtime-gateway"
Write-Host "Review Inbox:       $webBaseUrl/human-approvals"
Write-Host "Evidence Bundle:    $webBaseUrl/evidence"
Write-Host "API docs:           $apiBaseUrl/docs"
