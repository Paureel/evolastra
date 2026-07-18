from __future__ import annotations

import json
import time
import tracemalloc
from pathlib import Path

from asterism_api.reducer import initial_state, reduce_event

EVENTS = 100_000


def main() -> None:
    state = initial_state(
        {
            "id": "run_benchmark0000",
            "title": "Benchmark",
            "objective": "Measure reducer",
            "run_seed": 7,
        }
    )
    tracemalloc.start()
    started = time.perf_counter()
    for index in range(1, EVENTS + 1):
        state = reduce_event(
            state,
            {
                "id": f"evt_{index:032x}",
                "runid": "run_benchmark0000",
                "sequence": index,
                "type": "galaxy.analysis.metric.recorded.v1",
                "data": {
                    "metric": {"id": f"metr_{index:032x}", "name": "tokens.total", "value": index}
                },
            },
        )
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result = {
        "events": EVENTS,
        "seconds": round(elapsed, 3),
        "events_per_second": round(EVENTS / elapsed),
        "peak_memory_mb": round(peak / 1024 / 1024, 2),
        "projected_metrics": len(state["metrics"]),
        "last_sequence": state["last_sequence"],
        "environment": "local Python reducer; browser renderer measured separately",
    }
    Path("output/benchmarks").mkdir(parents=True, exist_ok=True)
    Path("output/benchmarks/event-reducer.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    if state["last_sequence"] != EVENTS or len(state["metrics"]) > 500:
        raise SystemExit("Benchmark integrity assertion failed")


if __name__ == "__main__":
    main()
