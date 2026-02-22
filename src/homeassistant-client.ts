/**
 * Home Assistant REST API client.
 *
 * Requires HASS_URL and HASS_TOKEN environment variables.
 */

export interface HAState {
  entity_id: string;
  state: string;
  attributes: Record<string, unknown>;
  last_changed: string;
  last_updated: string;
}

export interface HAService {
  domain: string;
  services: Record<
    string,
    {
      name: string;
      description: string;
      fields: Record<string, unknown>;
    }
  >;
}

export interface HAAutomation {
  id: string;
  alias: string;
  description?: string;
  mode?: string;
  last_triggered?: string;
}

export interface HALogEntry {
  name: string;
  message: string;
  entity_id?: string;
  when: string;
}

export interface HAConfig {
  location_name: string;
  latitude: number;
  longitude: number;
  elevation: number;
  unit_system: Record<string, string>;
  time_zone: string;
  version: string;
}

export class HomeAssistantClient {
  private baseUrl: string;
  private token: string;

  constructor() {
    const url = process.env.HASS_URL;
    const token = process.env.HASS_TOKEN;

    if (!url) {
      throw new Error(
        "HASS_URL environment variable is required (e.g. http://homeassistant.local:8123)"
      );
    }
    if (!token) {
      throw new Error(
        "HASS_TOKEN environment variable is required (long-lived access token from HA)"
      );
    }

    this.baseUrl = url.replace(/\/+$/, "");
    this.token = token;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}/api${path}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        Authorization: `Bearer ${this.token}`,
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const body = await response.text().catch(() => "");
      throw new Error(
        `Home Assistant API error ${response.status}: ${response.statusText}${body ? ` - ${body}` : ""}`
      );
    }

    return response.json() as Promise<T>;
  }

  /** Check API connectivity. */
  async checkApi(): Promise<{ message: string }> {
    return this.request<{ message: string }>("/");
  }

  /** Get HA configuration. */
  async getConfig(): Promise<HAConfig> {
    return this.request<HAConfig>("/config");
  }

  /** Get all entity states. */
  async getStates(): Promise<HAState[]> {
    return this.request<HAState[]>("/states");
  }

  /** Get state of a single entity. */
  async getState(entityId: string): Promise<HAState> {
    return this.request<HAState>(`/states/${entityId}`);
  }

  /** Get states filtered by domain (e.g. "light", "sensor", "switch"). */
  async getStatesByDomain(domain: string): Promise<HAState[]> {
    const states = await this.getStates();
    return states.filter((s) => s.entity_id.startsWith(`${domain}.`));
  }

  /** Get available services. */
  async getServices(): Promise<HAService[]> {
    return this.request<HAService[]>("/services");
  }

  /** Call a Home Assistant service. */
  async callService(
    domain: string,
    service: string,
    data: Record<string, unknown> = {}
  ): Promise<HAState[]> {
    return this.request<HAState[]>(`/services/${domain}/${service}`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  /** Fire an event. */
  async fireEvent(
    eventType: string,
    eventData: Record<string, unknown> = {}
  ): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/events/${eventType}`, {
      method: "POST",
      body: JSON.stringify(eventData),
    });
  }

  /** Get logbook entries. */
  async getLogbook(
    startTime?: string,
    entityId?: string
  ): Promise<HALogEntry[]> {
    let path = "/logbook";
    if (startTime) path += `/${startTime}`;
    if (entityId) path += `?entity=${entityId}`;
    return this.request<HALogEntry[]>(path);
  }

  /** Get history for an entity. */
  async getHistory(
    entityId: string,
    startTime?: string,
    endTime?: string
  ): Promise<HAState[][]> {
    let path = "/history/period";
    if (startTime) path += `/${startTime}`;
    path += `?filter_entity_id=${entityId}`;
    if (endTime) path += `&end_time=${endTime}`;
    return this.request<HAState[][]>(path);
  }

  /** Get error log. */
  async getErrorLog(): Promise<string> {
    const url = `${this.baseUrl}/api/error_log`;
    const response = await fetch(url, {
      headers: { Authorization: `Bearer ${this.token}` },
    });
    if (!response.ok) {
      throw new Error(`Error log request failed: ${response.status}`);
    }
    return response.text();
  }

  /** Render a Jinja2 template. */
  async renderTemplate(template: string): Promise<string> {
    const url = `${this.baseUrl}/api/template`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ template }),
    });
    if (!response.ok) {
      throw new Error(`Template render failed: ${response.status}`);
    }
    return response.text();
  }
}
