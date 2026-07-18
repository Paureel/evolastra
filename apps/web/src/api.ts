import type { Entity, GraphState, MissionReceipt, RunSummary, ShipyardState } from "./types";
import { apiAddress, authorizationHeaders, getConnection, safeEndpoint, saveConnection, signalAuthenticationRequired } from "./connection";

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiAddress(path), {
    ...init,
    headers: { "Content-Type": "application/json", ...authorizationHeaders(), ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    const problem = (await response.json().catch(() => ({ detail: response.statusText }))) as { detail?: string };
    if (response.status === 401) signalAuthenticationRequired();
    throw new ApiError(problem.detail ?? `Request failed (${response.status})`, response.status);
  }
  return response.json() as Promise<T>;
}

export async function pairCompanion(endpoint: string, code: string): Promise<{ profile: string; local_data: boolean }> {
  const normalized = safeEndpoint(endpoint);
  const response = await fetch(`${normalized}/api/v1/pairing/exchange`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code: code.trim() }),
  });
  const payload = await response.json().catch(() => ({})) as { access_token?: string; expires_at?: string; profile?: string; local_data?: boolean; detail?: string };
  if (!response.ok || !payload.access_token || !payload.expires_at) {
    throw new ApiError(payload.detail ?? `Pairing failed (${response.status})`, response.status);
  }
  saveConnection(normalized, payload.access_token, payload.expires_at);
  return { profile: payload.profile ?? "local-private", local_data: payload.local_data ?? true };
}

export async function pairingInfo(): Promise<{ authentication_required: boolean; pairing_supported: boolean; profile: string; local_data: boolean }> {
  const response = await fetch(apiAddress("/api/v1/pairing/info"), { cache: "no-store" });
  if (!response.ok) throw new ApiError(`Companion probe failed (${response.status})`, response.status);
  return response.json() as Promise<{ authentication_required: boolean; pairing_supported: boolean; profile: string; local_data: boolean }>;
}

export function connectionInfo(): Promise<{ profile: string; local_data: boolean; instance_id: string }> {
  return request("/api/v1/connection");
}

export async function openEventStream(runId: string, after: number, signal: AbortSignal): Promise<Response> {
  const response = await fetch(apiAddress(`/api/v1/runs/${encodeURIComponent(runId)}/events/stream?after=${after}`), {
    signal,
    headers: { Accept: "text/event-stream", "Last-Event-ID": String(after), ...authorizationHeaders() },
    cache: "no-store",
  });
  if (response.status === 401) signalAuthenticationRequired();
  if (!response.ok) throw new ApiError(`Live stream failed (${response.status})`, response.status);
  return response;
}

export async function listRuns(): Promise<RunSummary[]> {
  const response = await request<{ items: RunSummary[] }>("/api/v1/runs");
  return response.items;
}

export function fetchState(runId: string, at?: number): Promise<GraphState> {
  const query = at === undefined ? "" : `?at=${encodeURIComponent(at)}`;
  return request<GraphState>(`/api/v1/runs/${encodeURIComponent(runId)}/state${query}`);
}

export function startDemo(speed = 6): Promise<{ run_id: string; event_total: number }> {
  return request(`/api/v1/demo/start?speed=${speed}`, { method: "POST", body: "{}" });
}

export function sendCommand(runId: string, command: string, value?: string | number | boolean): Promise<Record<string, unknown>> {
  return request(`/api/v1/runs/${encodeURIComponent(runId)}/commands`, {
    method: "POST",
    body: JSON.stringify({ command, value: value ?? null }),
  });
}

export function fetchShipyard(runId: string): Promise<ShipyardState> {
  return request<ShipyardState>(`/api/v1/runs/${encodeURIComponent(runId)}/shipyard`);
}

export function buildShip(runId: string, blueprintId: string): Promise<{ ship: Entity }> {
  return request<{ ship: Entity }>(`/api/v1/runs/${encodeURIComponent(runId)}/shipyard/build`, {
    method: "POST",
    body: JSON.stringify({ blueprint_id: blueprintId }),
  });
}

export function dispatchShip(runId: string, shipId: string, prompt: string): Promise<MissionReceipt> {
  return request(`/api/v1/runs/${encodeURIComponent(runId)}/ships/${encodeURIComponent(shipId)}/dispatch`, {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}

export function recordApproval(runId: string, approvalId: string, decision: "approved" | "rejected"): Promise<Record<string, unknown>> {
  return request(`/api/v1/runs/${encodeURIComponent(runId)}/approvals/${encodeURIComponent(approvalId)}`, {
    method: "POST",
    body: JSON.stringify({ decision, note: decision === "approved" ? "Approved in the local observatory" : "Rejected in the local observatory" }),
  });
}

export async function search(runId: string, query: string): Promise<Array<{ id: string; entity_type: string; title: string; context: string; status?: string }>> {
  const response = await request<{ items: Array<{ id: string; entity_type: string; title: string; context: string; status?: string }> }>(
    `/api/v1/search?run_id=${encodeURIComponent(runId)}&q=${encodeURIComponent(query)}`,
  );
  return response.items;
}

export async function downloadExport(runId: string, format: string): Promise<void> {
  const response = await fetch(apiAddress(`/api/v1/runs/${encodeURIComponent(runId)}/export/${encodeURIComponent(format)}`), { headers: authorizationHeaders() });
  if (response.status === 401) signalAuthenticationRequired();
  if (!response.ok) throw new ApiError(`Export failed (${response.status})`, response.status);
  const blob = await response.blob();
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = response.headers.get("content-disposition")?.match(/filename="([^"]+)"/)?.[1] ?? `${runId}.${format}`;
  anchor.click();
  URL.revokeObjectURL(href);
}

export async function importPortableAnalysis(file: File): Promise<{ run_id: string; title?: string; accepted: number; duplicates: number }> {
  const form = new FormData();
  form.append("file", file, file.name);
  const response = await fetch(apiAddress("/api/v1/imports/portable"), {
    method: "POST",
    headers: authorizationHeaders(),
    body: form,
  });
  const payload = await response.json().catch(() => ({})) as { run_id?: string; title?: string; accepted?: number; duplicates?: number; detail?: string };
  if (response.status === 401) signalAuthenticationRequired();
  if (!response.ok || !payload.run_id) throw new ApiError(payload.detail ?? `Import failed (${response.status})`, response.status);
  return {
    run_id: payload.run_id,
    title: payload.title,
    accepted: payload.accepted ?? 0,
    duplicates: payload.duplicates ?? 0,
  };
}

export const currentEndpoint = () => getConnection().endpoint;
