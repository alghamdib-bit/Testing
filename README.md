# Home Assistant MCP Server

An MCP (Model Context Protocol) server that connects Claude to your Home Assistant instance. Control lights, read sensors, manage automations, and more — all through natural language.

## Features

| Tool | Description |
|------|-------------|
| `get_entity_state` | Get current state and attributes of any entity |
| `list_entities` | List all entities, optionally filtered by domain |
| `call_service` | Call any HA service (turn on/off lights, set climate, etc.) |
| `list_services` | List available services by domain |
| `get_history` | Get state history for an entity over a time period |
| `fire_event` | Fire custom events on the HA event bus |
| `render_template` | Render Jinja2 templates for complex queries |
| `get_config` | Get HA server configuration |
| `get_logbook` | Get recent activity log entries |
| `get_error_log` | Get the HA error log for debugging |

## Prerequisites

1. A running Home Assistant instance
2. A **long-lived access token** from Home Assistant:
   - Go to your HA profile page → **Security** → **Long-Lived Access Tokens**
   - Click **Create Token**, give it a name, and copy the token

## Setup

### 1. Build the server

```bash
npm install
npm run build
```

### 2. Configure Claude Code

Add this to your Claude Code MCP settings (`~/.claude/claude_code_config.json`):

```json
{
  "mcpServers": {
    "homeassistant": {
      "command": "node",
      "args": ["/absolute/path/to/Testing/dist/index.js"],
      "env": {
        "HASS_URL": "http://homeassistant.local:8123",
        "HASS_TOKEN": "your-long-lived-access-token"
      }
    }
  }
}
```

Replace:
- `/absolute/path/to/Testing/dist/index.js` with the actual path to the built server
- `HASS_URL` with your Home Assistant URL
- `HASS_TOKEN` with your long-lived access token

### 3. Configure Claude Desktop (alternative)

Add the same configuration to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or the equivalent config file on your platform.

## Usage Examples

Once configured, you can ask Claude things like:

- "What's the temperature in the living room?"
- "Turn off all the lights"
- "Set the thermostat to 72 degrees"
- "What happened in the house in the last hour?"
- "Is the garage door open?"
- "Turn on the porch light at 50% brightness"
- "List all my automations"
- "What's the energy usage today?"

## Development

```bash
npm run dev    # Watch mode — rebuilds on changes
npm run build  # One-time build
npm start      # Run the server directly
```
