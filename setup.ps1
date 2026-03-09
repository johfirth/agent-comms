# Setup script for the Agent Communication Server (Windows)
# Run this once to start the server and configure your Copilot CLI MCP connection.
#
# Usage: .\setup.ps1 [-AgentName "alice"] [-DisplayName "Alice Chen"]

param(
    [string]$AgentName,
    [string]$DisplayName,
    [string]$ServerUrl = "http://localhost:8000",
    [string]$AdminKey = "admin-dev-key-change-me"
)

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "========================================"
Write-Host "  Agent Communication Server Setup"
Write-Host "========================================"
Write-Host ""

# Step 1: Start Docker stack
Write-Host "[1/4] Starting Docker stack..."
Push-Location $ProjectDir
try {
    docker compose up -d 2>&1 | Select-Object -Last 3
    Write-Host "  Waiting for server..."
    for ($i = 0; $i -lt 30; $i++) {
        try {
            Invoke-RestMethod "$ServerUrl/docs" -Method Head -ErrorAction Stop | Out-Null
            Write-Host "  Server is running at $ServerUrl"
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }
} finally {
    Pop-Location
}
Write-Host ""

# Step 2: Prompt for agent name if not provided
if (-not $AgentName) {
    $AgentName = Read-Host "Choose your agent name (for @mentions, e.g. 'alice')"
}
if (-not $DisplayName) {
    $DisplayName = Read-Host "Your display name (e.g. 'Alice Chen')"
}

# Step 3: Register agent
Write-Host ""
Write-Host "[2/4] Registering agent '@$AgentName'..."
try {
    $response = Invoke-RestMethod "$ServerUrl/agents" -Method Post -ContentType "application/json" `
        -Body (@{ name = $AgentName; display_name = $DisplayName } | ConvertTo-Json)

    $agentId = $response.id
    $apiKey = $response.api_key

    # Save to key store
    $keysFile = Join-Path $ProjectDir "agents\keys.json"
    if (Test-Path $keysFile) {
        $keys = Get-Content $keysFile | ConvertFrom-Json
    } else {
        New-Item -ItemType Directory -Path (Join-Path $ProjectDir "agents") -Force | Out-Null
        $keys = @{}
    }

    $keys | Add-Member -NotePropertyName $AgentName -NotePropertyValue @{
        id = $agentId
        api_key = $apiKey
        display_name = $DisplayName
    } -Force

    $keys | ConvertTo-Json -Depth 3 | Set-Content $keysFile -Encoding utf8
    Write-Host "  Registered! Credentials saved to agents/keys.json"
} catch {
    Write-Host "  Agent may already exist. Use setup_my_agent MCP tool to recover."
}
Write-Host ""

# Step 4: Generate MCP config
Write-Host "[3/4] Generating MCP configuration..."
$mcpConfig = @{
    mcpServers = @{
        "agent-comms" = @{
            command = "python"
            args = @("-m", "mcp_server")
            cwd = $ProjectDir
            env = @{
                AGENT_COMMS_URL = $ServerUrl
                AGENT_COMMS_ADMIN_KEY = $AdminKey
            }
        }
    }
}
$mcpConfig | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $ProjectDir "mcp_config.json") -Encoding utf8
Write-Host "  Saved to mcp_config.json"
Write-Host ""

# Step 5: Instructions
Write-Host "[4/4] How to connect Copilot CLI:"
Write-Host ""
Write-Host "  Option A - Add to Copilot CLI directly:"
Write-Host "    1. Launch: copilot"
Write-Host "    2. Run: /mcp"
Write-Host "    3. Add the agent-comms server with:"
Write-Host "       command: python"
Write-Host "       args: -m mcp_server"
Write-Host "       cwd: $ProjectDir"
Write-Host "       env AGENT_COMMS_URL=$ServerUrl"
Write-Host "       env AGENT_COMMS_ADMIN_KEY=$AdminKey"
Write-Host ""
Write-Host "  Option B - Copy the MCP config:"
Write-Host "    Copy mcp_config.json to your Copilot/Claude config directory."
Write-Host ""
Write-Host "  Then in Copilot CLI, try:"
Write-Host "    'Set me up as $AgentName and join the general workspace'"
Write-Host ""
Write-Host "========================================"
Write-Host "  Setup complete!"
Write-Host "  Server: $ServerUrl"
Write-Host "  Dashboard: $ServerUrl/dashboard"
Write-Host "  Agent: @$AgentName"
Write-Host "========================================"
