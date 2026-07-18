/** Dependency-free TypeScript event helpers. This source is intentionally not
 * coupled to a package manager or repository-wide build configuration. */

export type Json = null | boolean | number | string | Json[] | { [key: string]: Json };

export interface EventEnvelope {
  specversion: "1.0";
  id: string;
  source: string;
  type: `galaxy.${string}.v1`;
  subject: string;
  time: string;
  datacontenttype: "application/json";
  dataschema: string;
  runid: string;
  sequence?: number;
  traceid: string;
  spanid: string;
  correlationid: string;
  causationid: string;
  producerversion: string;
  privacyclass: string;
  data: Record<string, Json>;
}

export type EventSink = (event: EventEnvelope) => void | Promise<void>;
export type CanonicalEntity = Record<string, Json> & {
  id: string;
  run_id: string;
  schema_version: number;
};

export type SemanticEntityKey =
  | "run"
  | "node"
  | "agent"
  | "tool_call"
  | "artifact"
  | "claim"
  | "evidence"
  | "finding"
  | "anomaly"
  | "dataset"
  | "dataset_version"
  | "approval";

const entityKeys: Record<string, SemanticEntityKey> = {
  "analysis.run": "run",
  "analysis.node": "node",
  "analysis.agent": "agent",
  "analysis.toolcall": "tool_call",
  "analysis.artifact": "artifact",
  "analysis.claim": "claim",
  "analysis.evidence": "evidence",
  "analysis.finding": "finding",
  "analysis.anomaly": "anomaly",
  "data.dataset": "dataset",
  "data.dataset_version": "dataset_version",
  "governance.approval": "approval",
};

export function entityData(
  key: SemanticEntityKey,
  entity: CanonicalEntity,
  metadata: Record<string, Json> = {},
): Record<string, Json> {
  return { ...metadata, [key]: entity };
}

const secretKey = /(^|[_-])(api[_-]?key|authorization|cookie|credential|passwd|password|private[_-]?key|secret|token)($|[_-])/i;
const contentKey = /(^|[_-])(body|content|input|message|output|prompt|response|text|transcript)($|[_-])/i;

export function redact(value: unknown, captureContent = false, depth = 0): Json {
  if (depth >= 8) return "[TRUNCATED_DEPTH]";
  if (value === null || typeof value === "boolean" || typeof value === "number") return value;
  if (typeof value === "string") return value.slice(0, 4096).replace(/\bsk-[A-Za-z0-9_-]{12,}\b/g, "[REDACTED_SECRET]");
  if (Array.isArray(value)) return value.slice(0, 100).map((entry) => redact(entry, captureContent, depth + 1));
  if (typeof value === "object") {
    const result: Record<string, Json> = {};
    for (const [key, entry] of Object.entries(value as Record<string, unknown>).slice(0, 100)) {
      result[key] = secretKey.test(key)
        ? "[REDACTED_SECRET]"
        : contentKey.test(key) && !captureContent
          ? "[REDACTED_CONTENT]"
          : redact(entry, captureContent, depth + 1);
    }
    return result;
  }
  return String(value).slice(0, 4096);
}

export class GalaxyClient {
  constructor(
    private readonly sink: EventSink,
    private readonly captureContent = false,
  ) {}

  async emit(event: EventEnvelope): Promise<void> {
    const [, area, entityName] = event.type.split(".");
    const key = entityKeys[`${area}.${entityName}`];
    if (key) {
      const entity = event.data[key];
      if (
        entity === null ||
        Array.isArray(entity) ||
        typeof entity !== "object" ||
        typeof entity.id !== "string" ||
        (key === "run" && entity.id !== event.runid) ||
        entity.run_id !== event.runid ||
        typeof entity.schema_version !== "number" ||
        entity.schema_version < 1
      ) {
        throw new Error(
          `Semantic event ${event.type} requires data.${key} with id, run_id, and schema_version`,
        );
      }
    }
    event.data = redact(event.data, this.captureContent) as Record<string, Json>;
    await this.sink(event);
  }
}
