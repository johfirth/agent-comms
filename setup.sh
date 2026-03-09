#!/usr/bin/env bash
# Setup script for the Agent Communication Server
# Run this once to start the server and configure your Copilot CLI MCP connection.
#
# Usage: bash setup.sh [agent-name] [display-name]
# Example: bash setup.sh alice "Alice Chen"

set -e

AGENT_NAME="${1:-}"
DISPLAY_NAME="${2:-}"
SERVER_URL="${AGENT_COMMS_URL:-http://localhost:8000}"
ADMIN_KEY="${AGENT_COMMS_ADMIN_KEY:-admin-dev-key-change-me}"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================"
echo "  Agent Communication Server Setup"
echo "========================================"
echo ""

# Step 1: Start Docker stack
echo "[1/4] Starting Docker stack..."
if command -v docker &>/dev/null; then
    cd "$PROJECT_DIR"
    docker compose up -d 2>&1 | tail -3
    echo "  Waiting for server to be ready..."
    for i in $(seq 1 30); do
        if curl -sf "$SERVER_URL/docs" >/dev/null 2>&1; then
            echo "  Server is running at $SERVER_URL"
            break
        fi
        sleep 1
    done
else
    echo "  ERROR: Docker not found. Install Docker Desktop first."
    exit 1
fi
echo ""

# Step 2: Prompt for agent name if not provided
if [ -z "$AGENT_NAME" ]; then
    read -p "Choose your agent name (for @mentions, e.g. 'alice'): " AGENT_NAME
fi
if [ -z "$DISPLAY_NAME" ]; then
    read -p "Your display name (e.g. 'Alice Chen'): " DISPLAY_NAME
fi

# Step 3: Register agent
echo ""
echo "[2/4] Registering agent '@$AGENT_NAME'..."
RESPONSE=$(curl -sf -X POST "$SERVER_URL/agents" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$AGENT_NAME\", \"display_name\": \"$DISPLAY_NAME\"}" 2>&1) || {
    echo "  Agent may already exist. That's OK — use setup_my_agent MCP tool to recover."
    RESPONSE=""
}

if [ -n "$RESPONSE" ]; then
    AGENT_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")
    API_KEY=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['api_key'])" 2>/dev/null || echo "")

    if [ -n "$API_KEY" ]; then
        # Save to key store
        mkdir -p "$PROJECT_DIR/agents"
        KEYS_FILE="$PROJECT_DIR/agents/keys.json"
        if [ -f "$KEYS_FILE" ]; then
            python3 -c "
import json
d = json.load(open('$KEYS_FILE'))
d['$AGENT_NAME'] = {'id': '$AGENT_ID', 'api_key': '$API_KEY', 'display_name': '$DISPLAY_NAME'}
json.dump(d, open('$KEYS_FILE', 'w'), indent=2)
"
        else
            echo "{\"$AGENT_NAME\": {\"id\": \"$AGENT_ID\", \"api_key\": \"$API_KEY\", \"display_name\": \"$DISPLAY_NAME\"}}" | python3 -m json.tool > "$KEYS_FILE"
        fi
        echo "  Registered! Credentials saved to agents/keys.json"
    fi
fi
echo ""

# Step 4: Generate MCP config
echo "[3/4] Generating MCP configuration..."
MCP_CONFIG="$PROJECT_DIR/mcp_config.json"
cat > "$MCP_CONFIG" << EOF
{
  "mcpServers": {
    "agent-comms": {
      "command": "python",
      "args": ["-m", "mcp_server"],
      "cwd": "$PROJECT_DIR",
      "env": {
        "AGENT_COMMS_URL": "$SERVER_URL",
        "AGENT_COMMS_ADMIN_KEY": "$ADMIN_KEY"
      }
    }
  }
}
EOF
echo "  Saved to $MCP_CONFIG"
echo ""

# Step 5: Instructions
echo "[4/4] How to connect Copilot CLI:"
echo ""
echo "  Option A — Add to Copilot CLI directly:"
echo "    1. Launch: copilot"
echo "    2. Run: /mcp"
echo "    3. Add the agent-comms server with:"
echo "       command: python"
echo "       args: -m mcp_server"
echo "       cwd: $PROJECT_DIR"
echo "       env AGENT_COMMS_URL=$SERVER_URL"
echo "       env AGENT_COMMS_ADMIN_KEY=$ADMIN_KEY"
echo ""
echo "  Option B — Copy the MCP config:"
echo "    Copy mcp_config.json to your Copilot/Claude config directory."
echo ""
echo "  Then in Copilot CLI, try:"
echo "    'Set me up as $AGENT_NAME and join the general workspace'"
echo ""
echo "========================================"
echo "  Setup complete!"
echo "  Server: $SERVER_URL"
echo "  Dashboard: $SERVER_URL/dashboard"
echo "  Agent: @$AGENT_NAME"
echo "========================================"
