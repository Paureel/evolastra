# Performance verification

_Measured backend reducer baseline and unexecuted browser-performance gates_

---

## 📋 Evidence status

Backend reducer throughput was measured locally on 2026-07-17. Browser rendering, layout-worker latency, SSE recovery time, API ingestion throughput, database rebuild time, and end-to-end memory were not measured by this workstream. Missing measurements are recorded as gaps, never passes.

The renderer comparison remains provisional. Its fixture, protocol, and pre-registered browser thresholds are documented in [`renderer-comparison.md`](../benchmarks/renderer-comparison.md).

## 💻 Measured environment

| Component | Recorded value |
| --- | --- |
| Operating system | Windows 10 Home `10.0.19045` |
| Processor | AMD Ryzen 5 5500U, 6 cores, 12 logical processors |
| Memory | 15.4 GB visible |
| Python | 3.12.4 |
| Node.js | 20.10.0 |
| npm | 10.2.3 |
| Power/browser/GPU mode | Not recorded; browser benchmark not executed |

## 📊 Reducer baseline

Five fresh in-process runs each reduced 100,000 metric events into a bounded 500-sample projection. `tracemalloc` measured incremental Python allocations during the reducer loop; it does not represent interpreter, process, database, or browser memory.

| Run | Seconds | Events/second | Peak incremental memory |
| ---: | ---: | ---: | ---: |
| 1 | 4.058 | 24,642 | 0.19 MB |
| 2 | 4.101 | 24,387 | 0.18 MB |
| 3 | 4.166 | 24,002 | 0.18 MB |
| 4 | 3.910 | 25,575 | 0.18 MB |
| 5 | 4.596 | 21,758 | 0.18 MB |
| **Median / maximum** | **4.101 median** | **24,387 median** | **0.19 MB maximum** |

All five diagnostic runs ended at sequence 100,000, reported event count 100,000, and retained exactly 500 projected metric samples. This demonstrates the reducer's bounded metric projection on the recorded machine; it does not establish API, database, SSE, React, or Canvas throughput.

The final release command reran the same 100,000-event correctness workload once after all fixes: **3.530 seconds, 28,326 events/second, 0.19 MB peak incremental allocation**, 500 retained metrics, and terminal sequence 100,000. The repeated five-run median above remains the more conservative performance claim.

An earlier pre-registry baseline measured a 3.875-second median and 25,809 events/second. An intermediate implementation constructed the supported-action registry on every call and regressed to 6.834 seconds median. Profiling isolated that allocation; hoisting the immutable registry to module scope restored the fresh result above to within roughly 6% of the original median throughput.

## 🎯 Regression gates

The current hard correctness gates are:

- Terminal sequence equals submitted event count
- Projection event count equals submitted event count
- Projected metric samples never exceed 500
- Final projected metric is the final ordered sample

The earlier reducer baseline established a proposed machine-specific regression alert at a five-run median above 5.0 seconds or any run above 6.0 seconds. The fresh optimized result passes both alerts. The threshold was set after the original baseline and is therefore a regression guard, not a pre-registered product-performance claim.

Browser gates remain those in the renderer comparison: cold first useful render, frame-time percentiles, long tasks, pick latency, update-to-paint latency, count correctness, retained memory, browser support, accessibility, and reduced motion. None received a pass from this backend measurement.

## ⚙️ Reproduction command

The repository benchmark command is:

```powershell
npm run benchmark
```

It runs `scripts/benchmark.py` and writes `output/benchmarks/event-reducer.json`. The quality workstream used an equivalent inline five-run loop to avoid writing benchmark artifacts outside its owned paths. Any release benchmark should retain the raw JSON, exact environment, commit, and command output.

## 🔍 Required future measurements

| Area | Scenario | Status |
| --- | --- | --- |
| API ingestion | 100,000 durable events with SQLite and PostgreSQL profiles | Not measured |
| Projection rebuild | Full replay and snapshot-assisted replay | Correctness tested; latency not measured |
| SSE recovery | Disconnect, backlog catch-up, and heartbeat behavior | Functional cursor test only |
| Browser renderer | 1,000 systems, 5,000 objects, 20,000 edges, 50 agents | Not measured |
| Metric pressure | 1,000 samples/second with visual coalescing | Reducer bound tested; browser not measured |
| Search | Large-run typed queries and highlighting | Not measured |
| Artifact preview | Bounded JSON, chart, table, and Parquet samples | Not measured |
| Memory | API process, JS heap, browser working set, GPU where available | Not measured |
| Accessibility performance | Text-tree navigation and reduced-motion scenario | Not measured |

## 📌 Interpretation rules

- Report median and tail behavior from repeated runs, not one average
- Separate correctness failures from latency failures
- Do not compare browser candidates across different machines or power modes
- Mark unavailable GPU or memory metrics as not measurable
- Keep layout timing separate from renderer timing
- Preserve raw outputs before changing thresholds or implementations

## 🔗 References

- [Renderer comparison protocol](../benchmarks/renderer-comparison.md)
- [Renderer recommendation](../benchmarks/renderer-recommendation.md)
- [Quality report](../audit/quality-report.md)
