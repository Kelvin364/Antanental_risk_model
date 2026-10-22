# Performance evidence

Measured by `scripts/benchmark_api.py` on 2026-10-22T09:59:33+00:00. The script started
its own server (one uvicorn worker, a temporary SQLite file), waited for `/health`,
sent one warm up request, then 500 sequential and 50 concurrent
`POST /api/predict` requests from the same machine. The raw numbers are in
`performance.json`.

## Machine

| Item | Value |
| --- | --- |
| CPU | Apple M3 |
| Logical cores | 8 |
| RAM | 8.0 GB |
| Operating system | macOS-15.5-arm64-arm-64bit |
| Python | 3.12.13 |

## Results

| Measure | Value |
| --- | --- |
| Start up, launch to first `/health` answer | 1.75 seconds |
| Peak resident memory of the server | 209.5 MB |
| Sequential, p50 latency | 2.6 ms |
| Sequential, p95 latency | 2.9 ms |
| Sequential, slowest request | 6.9 ms |
| Concurrent, p50 latency | 102.0 ms |
| Concurrent, p95 latency | 138.3 ms |
| Concurrent, slowest request | 139.0 ms |
| Concurrent, wall time for all requests | 0.14 seconds |

The server runs one worker, which handles the concurrent requests one after another,
so concurrent latency includes the time each request waits for the ones ahead of it.
These numbers describe one laptop with client and server on the same machine. They
are not a measure of performance on a health worker's phone or over a network.
