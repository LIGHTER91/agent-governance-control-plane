[CmdletBinding()]
param(
    [switch]$KeepRunning,
    [ValidateRange(1, 65535)]
    [int]$DatabasePort = 55432,
    [ValidateRange(1, 65535)]
    [int]$ApiPort = 58000,
    [ValidateRange(1, 65535)]
    [int]$WebPort = 53000
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 3.0

$projectName = "agcp-clean-validation"
$repoRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $repoRoot "compose.dev.yml"
$databaseName = "agent_governance_control_plane_validation"
$apiBaseUrl = "http://localhost:$ApiPort"
$webBaseUrl = "http://localhost:$WebPort"
$environmentConfigured = $false
$composeStarted = $false
$validationSucceeded = $false
$originalEnvironment = @{}

function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

function Test-TcpPortAvailable {
    param([Parameter(Mandatory = $true)][int]$Port)

    $listener = [System.Net.Sockets.TcpListener]::new(
        [System.Net.IPAddress]::Any,
        $Port
    )
    try {
        $listener.Start()
        return $true
    } catch [System.Net.Sockets.SocketException] {
        return $false
    } finally {
        $listener.Stop()
    }
}

function Set-ValidationEnvironment {
    $overrides = [ordered]@{
        AGCP_DB_CONTAINER_NAME = "$projectName-db"
        AGCP_API_CONTAINER_NAME = "$projectName-api"
        AGCP_WEB_CONTAINER_NAME = "$projectName-web"
        AGCP_API_PORT = [string]$ApiPort
        AGCP_WEB_PORT = [string]$WebPort
        POSTGRES_DB = $databaseName
        POSTGRES_USER = "postgres"
        POSTGRES_PASSWORD = "postgres"
        POSTGRES_PORT = [string]$DatabasePort
        AGCP_DATABASE_URL = "postgresql+psycopg://postgres:postgres@db:5432/$databaseName`?connect_timeout=5"
        DATABASE_URL = "postgresql+psycopg://postgres:postgres@db:5432/$databaseName`?connect_timeout=5"
        NEXT_PUBLIC_AGCP_API_BASE_URL = $apiBaseUrl
        AGCP_CORS_ALLOWED_ORIGINS = "$webBaseUrl,http://127.0.0.1:$WebPort"
        AGCP_DEV_ACTOR_ID = "local-admin"
        AGCP_DEV_ACTOR_ROLES = "platform_admin,reviewer,auditor"
        AGCP_DEV_ACTOR_DISPLAY_NAME = "Local Admin"
        AGCP_RUNTIME_METADATA_PRE_CHECKS_ENABLED = "true"
    }

    foreach ($entry in $overrides.GetEnumerator()) {
        $existing = Get-Item -LiteralPath "Env:$($entry.Key)" -ErrorAction SilentlyContinue
        $originalEnvironment[$entry.Key] = if ($null -eq $existing) {
            $null
        } else {
            [string]$existing.Value
        }
        Set-Item -LiteralPath "Env:$($entry.Key)" -Value $entry.Value
    }
}

function Restore-ValidationEnvironment {
    foreach ($entry in $originalEnvironment.GetEnumerator()) {
        if ($null -eq $entry.Value) {
            Remove-Item -LiteralPath "Env:$($entry.Key)" -ErrorAction SilentlyContinue
        } else {
            Set-Item -LiteralPath "Env:$($entry.Key)" -Value $entry.Value
        }
    }
}

function Invoke-Compose {
    param(
        [Parameter(Mandatory = $true)][string[]]$ComposeArgs,
        [switch]$Capture
    )

    $output = @(
        & docker compose -p $projectName -f $composeFile @ComposeArgs 2>&1
    )
    if ($LASTEXITCODE -ne 0) {
        $details = ($output | ForEach-Object { [string]$_ }) -join [Environment]::NewLine
        throw "docker compose failed: $($ComposeArgs -join ' ')$([Environment]::NewLine)$details"
    }
    if ($Capture) {
        return $output
    }
    $output | Out-Host
}

function Test-ComposeProbe {
    param([Parameter(Mandatory = $true)][string[]]$ComposeArgs)

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & docker compose -p $projectName -f $composeFile @ComposeArgs *> $null
    $exitCode = $LASTEXITCODE
    $ErrorActionPreference = $previousPreference
    return $exitCode -eq 0
}

function Wait-ForDatabase {
    for ($attempt = 1; $attempt -le 60; $attempt++) {
        if (
            Test-ComposeProbe @(
                "exec",
                "-T",
                "db",
                "pg_isready",
                "-U",
                "postgres",
                "-d",
                $databaseName
            )
        ) {
            return
        }
        Start-Sleep -Seconds 2
    }
    throw "PostgreSQL did not become ready in the isolated validation project."
}

function Wait-ForJsonEndpoint {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$Description
    )

    for ($attempt = 1; $attempt -le 60; $attempt++) {
        try {
            return Invoke-RestMethod -Method Get -Uri $Uri -TimeoutSec 5
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    throw "$Description did not become ready at $Uri."
}

function Wait-ForWeb {
    for ($attempt = 1; $attempt -le 60; $attempt++) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $webBaseUrl -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                return
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }
    throw "Frontend did not become ready at $webBaseUrl."
}

Set-Location $repoRoot

Write-Step "Checking isolated validation prerequisites"
$requestedPorts = [ordered]@{
    PostgreSQL = $DatabasePort
    API = $ApiPort
    Frontend = $WebPort
}
if (@($requestedPorts.Values | Select-Object -Unique).Count -ne $requestedPorts.Count) {
    throw "DatabasePort, ApiPort, and WebPort must be distinct. No containers or volumes were changed."
}
$occupiedPorts = @(
    $requestedPorts.GetEnumerator() |
        Where-Object { -not (Test-TcpPortAvailable -Port $_.Value) } |
        ForEach-Object { "$($_.Key)=$($_.Value)" }
)
if ($occupiedPorts.Count -gt 0) {
    throw (
        "Isolated validation did not start because required host ports are occupied: " +
        "$($occupiedPorts -join ', '). Re-run with free -DatabasePort, -ApiPort, " +
        "and -WebPort values. No existing containers or volumes were changed."
    )
}

$previousPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& docker version *> $null
$dockerExitCode = $LASTEXITCODE
$ErrorActionPreference = $previousPreference
if ($dockerExitCode -ne 0) {
    throw "Docker is unavailable. Start Docker Desktop and rerun scripts/validate-clean.ps1."
}

Set-ValidationEnvironment
$environmentConfigured = $true

try {
    Write-Step "Removing only prior $projectName resources"
    Invoke-Compose @("down", "--volumes", "--remove-orphans")

    Write-Step "Building isolated API and frontend images"
    Invoke-Compose @("build", "api", "web")

    Write-Step "Starting a clean PostgreSQL volume"
    Invoke-Compose @("up", "-d", "db")
    $composeStarted = $true
    Wait-ForDatabase

    Write-Step "Applying every Alembic migration to the empty PostgreSQL database"
    Invoke-Compose @(
        "run",
        "--rm",
        "--no-deps",
        "api",
        "uv",
        "run",
        "alembic",
        "upgrade",
        "head"
    )
    $migrationState = @(
        Invoke-Compose -Capture @(
            "run",
            "--rm",
            "--no-deps",
            "api",
            "uv",
            "run",
            "alembic",
            "current"
        )
    )
    if (-not ($migrationState -match "\(head\)")) {
        throw "Alembic current did not report the head revision."
    }

    Write-Step "Starting the isolated API and frontend"
    Invoke-Compose @("up", "-d", "api", "web")
    $health = Wait-ForJsonEndpoint -Uri "$apiBaseUrl/health" -Description "API health"
    if ($health.status -ne "ok") {
        throw "GET /health did not return status=ok."
    }
    $me = Wait-ForJsonEndpoint -Uri "$apiBaseUrl/me" -Description "Current actor endpoint"
    $roles = @($me.roles)
    $missingRoles = @(
        @("platform_admin", "reviewer", "auditor") |
            Where-Object { $_ -notin $roles }
    )
    if (
        $me.actor_id -ne "local-admin" -or
        $me.display_name -ne "Local Admin" -or
        $missingRoles.Count -gt 0
    ) {
        throw "GET /me did not return the expected isolated Local Admin actor."
    }

    Write-Step "Applying the deterministic full-stack seed"
    Invoke-Compose @(
        "exec",
        "-T",
        "api",
        "uv",
        "run",
        "python",
        "scripts/seed_full_stack_demo.py",
        "--apply"
    )

    Write-Step "Loading the first-class metadata pre-check payload"
    $payloadOutput = @(
        Invoke-Compose -Capture @(
            "exec",
            "-T",
            "api",
            "uv",
            "run",
            "python",
            "scripts/seed_full_stack_demo.py",
            "--print-runtime-payload"
        )
    )
    $payloadJson = @(
        $payloadOutput |
            ForEach-Object { [string]$_ } |
            Where-Object { $_.Trim().StartsWith("{") } |
            Select-Object -Last 1
    )
    if ($payloadJson.Count -ne 1) {
        throw "The metadata pre-check helper did not emit one JSON payload."
    }
    $payload = $payloadJson[0] | ConvertFrom-Json
    $uniqueRunId = [guid]::NewGuid().ToString()
    $payload.run_id = $uniqueRunId
    $payload.request_id = "clean-validation-$($uniqueRunId.Substring(0, 8))"

    Write-Step "Calling Runtime Gateway and checking the governance result"
    $decisionResponse = Invoke-RestMethod `
        -Method Post `
        -Uri "$apiBaseUrl/runtime/tool-calls/decision" `
        -ContentType "application/json" `
        -Body ($payload | ConvertTo-Json -Depth 20) `
        -TimeoutSec 30
    if ($decisionResponse.decision -ne "require_human_review") {
        throw "Expected decision=require_human_review; received $($decisionResponse.decision)."
    }
    if ([bool]$decisionResponse.proceed) {
        throw "Expected proceed=false for the metadata pre-check scenario."
    }
    if ([string]::IsNullOrWhiteSpace([string]$decisionResponse.human_approval_id)) {
        throw "Runtime Gateway did not return a HumanApproval identifier."
    }

    Write-Step "Confirming CheckResult evidence"
    $evidenceBundle = Invoke-RestMethod `
        -Method Get `
        -Uri "$apiBaseUrl/agents/$($payload.agent_id)/evidence-bundle" `
        -TimeoutSec 30
    $policyDecisionId = [string]$decisionResponse.policy_decision_id
    $checkResults = @(
        $evidenceBundle.check_results |
            Where-Object { [string]$_.policy_decision_id -eq $policyDecisionId }
    )
    if ($checkResults.Count -le 0) {
        throw "No CheckResults were linked to PolicyDecision $policyDecisionId."
    }

    Write-Step "Running frontend static smoke and HTTP readiness checks"
    Invoke-Compose @("exec", "-T", "web", "npm", "run", "smoke")
    Wait-ForWeb
    $validationSucceeded = $true
} finally {
    if ($environmentConfigured) {
        $cleanupFailure = $null
        if ($KeepRunning -and $composeStarted) {
            Write-Host ""
            Write-Host "KeepRunning supplied; isolated validation services remain available:"
            Write-Host "Frontend: $webBaseUrl"
            Write-Host "API:      $apiBaseUrl"
            Write-Host (
                "Cleanup:  docker compose -p $projectName -f compose.dev.yml " +
                "down --volumes --remove-orphans"
            )
        } else {
            Write-Step "Cleaning only the isolated $projectName project"
            try {
                Invoke-Compose @("down", "--volumes", "--remove-orphans")
            } catch {
                $cleanupFailure = $_.Exception.Message
                Write-Warning "Isolated validation cleanup failed: $cleanupFailure"
            }
        }
        Restore-ValidationEnvironment
        if ($validationSucceeded -and $null -ne $cleanupFailure) {
            throw "Governance checks passed, but isolated validation cleanup failed: $cleanupFailure"
        }
    }
}

if ($validationSucceeded) {
    Write-Host ""
    Write-Host "Clean validation passed"
    Write-Host "Compose project:    $projectName"
    Write-Host "Alembic:            head"
    Write-Host "Health:             $($health.status)"
    Write-Host "Current actor:       $($me.display_name) <$($me.actor_id)>"
    Write-Host "Decision:            $($decisionResponse.decision)"
    Write-Host "Proceed:             $(([string]$decisionResponse.proceed).ToLowerInvariant())"
    Write-Host "PolicyDecision id:   $policyDecisionId"
    Write-Host "CheckResults count:  $($checkResults.Count)"
    Write-Host "HumanApproval id:    $($decisionResponse.human_approval_id)"
    Write-Host "Frontend:            $webBaseUrl"
    Write-Host "API:                 $apiBaseUrl"
}
