# Performance evidence

Measured by `scripts/benchmark_api.py` on 2026-10-22T21:44:34+00:00. The script started
its own server (one uvicorn worker, a temporary SQLite file), waited for `/health`,
sent one warm up request, then 500 sequential and 50 concurrent
`POST /api/predict` requests from the same machine. The raw numbers are in
`performance.json`.

## Machine

| Item | Value |
| --- | --- |
| CPU | 12th Gen Intel(R) Core(TM) i5-1235U |
| Logical cores | 12 |
| RAM | 7.6 GB |
| Operating system | Linux-6.18.54.1-microsoft-standard-WSL2-x86_64-with-glibc2.35 |
| Python | 3.12.15 |

## Results

| Measure | Value |
| --- | --- |
| Start up, launch to first `/health` answer | 2.11 seconds |
| Peak resident memory of the server | 267.7 MB |
| Sequential, p50 latency | 11.9 ms |
| Sequential, p95 latency | 24.1 ms |
| Sequential, slowest request | 51.1 ms |
| Concurrent, p50 latency | 789.7 ms |
| Concurrent, p95 latency | 1056.7 ms |
| Concurrent, slowest request | 1065.2 ms |
| Concurrent, wall time for all requests | 1.1 seconds |

The server runs one worker, which handles the concurrent requests one after another,
so concurrent latency includes the time each request waits for the ones ahead of it.
These numbers describe one laptop with client and server on the same machine. They
are not a measure of performance on a health worker's phone or over a network.
