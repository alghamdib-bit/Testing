#!/usr/bin/env node

/**
 * Home Assistant MCP Server
 *
 * Exposes Home Assistant functionality as MCP tools for Claude.
 *
 * Environment variables:
 *   HASS_URL   - Home Assistant base URL (e.g. http://homeassistant.local:8123)
 *   HASS_TOKEN - Long-lived access token
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { HomeAssistantClient } from "./homeassistant-client.js";

const ha = new HomeAssistantClient();

const server = new McpServer({
  name: "homeassistant",
  version: "1.0.0",
});

// ---------------------------------------------------------------------------
// Tools
// ---------------------------------------------------------------------------

server.tool(
  "get_entity_state",
  "Get the current state and attributes of a Home Assistant entity",
  {
    entity_id: z
      .string()
      .describe("Entity ID, e.g. light.living_room, sensor.temperature"),
  },
  async ({ entity_id }) => {
    const state = await ha.getState(entity_id);
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(state, null, 2),
        },
      ],
    };
  }
);

server.tool(
  "list_entities",
  "List all entities, optionally filtered by domain (light, switch, sensor, etc.)",
  {
    domain: z
      .string()
      .optional()
      .describe(
        "Filter by domain, e.g. 'light', 'switch', 'sensor', 'climate', 'cover'"
      ),
  },
  async ({ domain }) => {
    const states = domain
      ? await ha.getStatesByDomain(domain)
      : await ha.getStates();

    const summary = states.map((s) => ({
      entity_id: s.entity_id,
      state: s.state,
      friendly_name: s.attributes.friendly_name ?? s.entity_id,
    }));

    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(summary, null, 2),
        },
      ],
    };
  }
);

server.tool(
  "call_service",
  "Call a Home Assistant service (e.g. turn on a light, lock a door, set climate temperature)",
  {
    domain: z.string().describe("Service domain, e.g. 'light', 'switch', 'climate', 'cover'"),
    service: z
      .string()
      .describe("Service name, e.g. 'turn_on', 'turn_off', 'toggle', 'set_temperature'"),
    entity_id: z
      .string()
      .optional()
      .describe("Target entity ID, e.g. 'light.living_room'"),
    data: z
      .record(z.string(), z.unknown())
      .optional()
      .describe(
        "Additional service data as key-value pairs, e.g. { \"brightness\": 255, \"color_name\": \"blue\" }"
      ),
  },
  async ({ domain, service, entity_id, data }) => {
    const serviceData: Record<string, unknown> = { ...data };
    if (entity_id) {
      serviceData.entity_id = entity_id;
    }
    const result = await ha.callService(domain, service, serviceData);
    return {
      content: [
        {
          type: "text" as const,
          text: `Service ${domain}.${service} called successfully.\n\n${JSON.stringify(result, null, 2)}`,
        },
      ],
    };
  }
);

server.tool(
  "list_services",
  "List available services, optionally filtered by domain",
  {
    domain: z
      .string()
      .optional()
      .describe("Filter by domain, e.g. 'light', 'automation'"),
  },
  async ({ domain }) => {
    const services = await ha.getServices();
    const filtered = domain
      ? services.filter((s) => s.domain === domain)
      : services;

    const summary = filtered.map((s) => ({
      domain: s.domain,
      services: Object.keys(s.services),
    }));

    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(summary, null, 2),
        },
      ],
    };
  }
);

server.tool(
  "get_history",
  "Get state history for an entity over a time period",
  {
    entity_id: z.string().describe("Entity ID to get history for"),
    start_time: z
      .string()
      .optional()
      .describe("ISO 8601 start time, e.g. '2024-01-01T00:00:00Z'. Defaults to 1 day ago."),
    end_time: z
      .string()
      .optional()
      .describe("ISO 8601 end time. Defaults to now."),
  },
  async ({ entity_id, start_time, end_time }) => {
    const history = await ha.getHistory(entity_id, start_time, end_time);
    const entries = history.flat();
    return {
      content: [
        {
          type: "text" as const,
          text: `History for ${entity_id} (${entries.length} entries):\n\n${JSON.stringify(entries, null, 2)}`,
        },
      ],
    };
  }
);

server.tool(
  "fire_event",
  "Fire a custom event on the Home Assistant event bus",
  {
    event_type: z.string().describe("Event type name"),
    event_data: z
      .record(z.string(), z.unknown())
      .optional()
      .describe("Event data payload"),
  },
  async ({ event_type, event_data }) => {
    const result = await ha.fireEvent(event_type, event_data ?? {});
    return {
      content: [
        {
          type: "text" as const,
          text: result.message,
        },
      ],
    };
  }
);

server.tool(
  "render_template",
  "Render a Home Assistant Jinja2 template (useful for complex state queries)",
  {
    template: z
      .string()
      .describe(
        "Jinja2 template string, e.g. '{{ states(\"sensor.temperature\") }}'"
      ),
  },
  async ({ template }) => {
    const result = await ha.renderTemplate(template);
    return {
      content: [
        {
          type: "text" as const,
          text: result,
        },
      ],
    };
  }
);

server.tool(
  "get_config",
  "Get Home Assistant server configuration (location, version, units, etc.)",
  {},
  async () => {
    const config = await ha.getConfig();
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(config, null, 2),
        },
      ],
    };
  }
);

server.tool(
  "get_logbook",
  "Get logbook entries for recent activity",
  {
    entity_id: z
      .string()
      .optional()
      .describe("Filter by entity ID"),
    start_time: z
      .string()
      .optional()
      .describe("ISO 8601 start time. Defaults to today."),
  },
  async ({ entity_id, start_time }) => {
    const entries = await ha.getLogbook(start_time, entity_id);
    return {
      content: [
        {
          type: "text" as const,
          text: `Logbook (${entries.length} entries):\n\n${JSON.stringify(entries, null, 2)}`,
        },
      ],
    };
  }
);

server.tool(
  "get_error_log",
  "Get the Home Assistant error log for debugging",
  {},
  async () => {
    const log = await ha.getErrorLog();
    return {
      content: [
        {
          type: "text" as const,
          text: log.slice(0, 10000), // Truncate to avoid overwhelming context
        },
      ],
    };
  }
);

// ---------------------------------------------------------------------------
// Resources — expose dashboards & areas as browsable resources
// ---------------------------------------------------------------------------

server.resource(
  "ha-overview",
  "homeassistant://overview",
  async () => {
    const [config, states] = await Promise.all([
      ha.getConfig(),
      ha.getStates(),
    ]);

    const domains = new Map<string, number>();
    for (const s of states) {
      const domain = s.entity_id.split(".")[0];
      domains.set(domain, (domains.get(domain) ?? 0) + 1);
    }

    const overview = {
      name: config.location_name,
      version: config.version,
      time_zone: config.time_zone,
      total_entities: states.length,
      entities_by_domain: Object.fromEntries(
        [...domains.entries()].sort((a, b) => b[1] - a[1])
      ),
    };

    return {
      contents: [
        {
          uri: "homeassistant://overview",
          mimeType: "application/json",
          text: JSON.stringify(overview, null, 2),
        },
      ],
    };
  }
);

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
