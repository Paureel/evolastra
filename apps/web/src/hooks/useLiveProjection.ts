import { useEffect, useRef, useState } from "react";
import { fetchState, openEventStream } from "../api";
import type { GraphState } from "../types";

type ConnectionState = "connecting" | "live" | "reconnecting" | "offline";

export function useLiveProjection(runId: string | null, connectionRevision = 0) {
  const [state, setState] = useState<GraphState | null>(null);
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [error, setError] = useState<string | null>(null);
  const cursor = useRef(0);

  useEffect(() => {
    if (!runId) {
      setState(null);
      return;
    }
    setState(null);
    setConnection("connecting");
    cursor.current = 0;
    let disposed = false;
    const controller = new AbortController();
    let flushTimer: number | null = null;

    const refresh = async () => {
      try {
        const next = await fetchState(runId);
        if (!disposed) {
          cursor.current = next.last_sequence;
          setState(next);
          setError(null);
        }
      } catch (reason) {
        if (!disposed) setError(reason instanceof Error ? reason.message : "Projection refresh failed");
      }
    };

    const scheduleRefresh = () => {
      if (flushTimer !== null) return;
      flushTimer = window.setTimeout(() => {
        flushTimer = null;
        void refresh();
      }, 180);
    };

    const readStream = async () => {
      while (!disposed) {
        try {
          const response = await openEventStream(runId, cursor.current, controller.signal);
          const reader = response.body?.getReader();
          if (!reader) throw new Error("Live stream is unavailable");
          setConnection("live");
          setError(null);
          const decoder = new TextDecoder();
          let buffer = "";
          while (!disposed) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true }).replaceAll("\r\n", "\n");
            let boundary = buffer.indexOf("\n\n");
            while (boundary >= 0) {
              const frame = buffer.slice(0, boundary);
              buffer = buffer.slice(boundary + 2);
              const eventName = frame.split("\n").find((line) => line.startsWith("event:"))?.slice(6).trim();
              const data = frame.split("\n").filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim()).join("\n");
              if (eventName === "semantic" && data) {
                try {
                  const envelope = JSON.parse(data) as { sequence?: number };
                  cursor.current = Math.max(cursor.current, envelope.sequence ?? 0);
                } catch {
                  // A state refresh remains authoritative if one transport frame is malformed.
                }
                scheduleRefresh();
              } else if (eventName === "heartbeat") setConnection("live");
              boundary = buffer.indexOf("\n\n");
            }
          }
          if (!disposed) setConnection("reconnecting");
        } catch (reason) {
          if (disposed || controller.signal.aborted) return;
          setConnection("reconnecting");
          setError(reason instanceof Error ? reason.message : "Live stream disconnected");
        }
        await new Promise((resolve) => window.setTimeout(resolve, 900));
      }
    };

    void refresh().then(() => { if (!disposed) void readStream(); });

    return () => {
      disposed = true;
      controller.abort();
      if (flushTimer !== null) window.clearTimeout(flushTimer);
    };
  }, [runId, connectionRevision]);

  return { state, connection, error, refresh: () => runId ? fetchState(runId).then(setState) : Promise.resolve() };
}
