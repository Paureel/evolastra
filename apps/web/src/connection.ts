export const AUTH_REQUIRED_EVENT = "evolastra:auth-required";
export const CONNECTION_CHANGED_EVENT = "evolastra:connection-changed";

const ENDPOINT_KEY = "evolastra.api.endpoint";
const TOKEN_KEY = "evolastra.api.session";
const EXPIRY_KEY = "evolastra.api.expiry";
const DEFAULT_ENDPOINT = "http://127.0.0.1:8000";

export interface RuntimeConnection {
  endpoint: string;
  token: string | null;
  expiresAt: string | null;
}

export function shouldStartCompanionConnection(
  token: string | null,
  developmentDemoRequested = false,
): boolean {
  return Boolean(token) || developmentDemoRequested;
}

function storage(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function safeEndpoint(value: string): string {
  const url = new URL(value.trim());
  const loopback = ["127.0.0.1", "localhost", "[::1]"].includes(url.hostname);
  if (!loopback || !["http:", "https:"].includes(url.protocol)) {
    throw new Error("Evolastra viewers connect only to a companion on this device.");
  }
  if (url.username || url.password || url.search || url.hash) {
    throw new Error("The API address cannot contain credentials, a query, or a fragment.");
  }
  if (url.pathname !== "/") {
    throw new Error("Use the local companion origin without an API path.");
  }
  return url.toString().replace(/\/$/, "");
}

export function getConnection(): RuntimeConnection {
  const session = storage();
  const endpoint = safeEndpoint(session?.getItem(ENDPOINT_KEY) ?? DEFAULT_ENDPOINT);
  const expiresAt = session?.getItem(EXPIRY_KEY) ?? null;
  const expired = expiresAt ? Date.parse(expiresAt) <= Date.now() : false;
  if (expired) {
    session?.removeItem(TOKEN_KEY);
    session?.removeItem(EXPIRY_KEY);
  }
  return {
    endpoint,
    token: expired ? null : session?.getItem(TOKEN_KEY) ?? null,
    expiresAt: expired ? null : expiresAt,
  };
}

export function saveConnection(endpoint: string, token: string, expiresAt: string): void {
  const normalized = safeEndpoint(endpoint);
  const session = storage();
  session?.setItem(ENDPOINT_KEY, normalized);
  session?.setItem(TOKEN_KEY, token);
  session?.setItem(EXPIRY_KEY, expiresAt);
  window.dispatchEvent(new Event(CONNECTION_CHANGED_EVENT));
}

export function forgetConnection(): void {
  const session = storage();
  session?.removeItem(TOKEN_KEY);
  session?.removeItem(EXPIRY_KEY);
  window.dispatchEvent(new Event(CONNECTION_CHANGED_EVENT));
}

export function signalAuthenticationRequired(): void {
  window.dispatchEvent(new Event(AUTH_REQUIRED_EVENT));
}

export function apiAddress(path: string, endpoint = getConnection().endpoint): string {
  return `${endpoint}${path}`;
}

export function authorizationHeaders(): HeadersInit {
  const token = getConnection().token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}
