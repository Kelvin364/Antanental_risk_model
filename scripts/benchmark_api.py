"""Measure the prototype API: start up time, latency and memory.

Usage: ``python scripts/benchmark_api.py``. The script starts its own server
on a free local port with a temporary database, waits for ``/health``, sends
500 sequential and then 50 concurrent ``POST /api/predict`` requests, samples
the server's resident memory throughout, stops the server and writes
``docs/evidence/performance.md`` and ``docs/evidence/performance.json``.
It uses the standard library plus psutil only.
"""

from __future__ import annotations

import json
import os
import platform
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_account import create_account  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SEQUENTIAL, CONCURRENT = 500, 50
PAYLOAD = json.dumps(
    {
        "case": {
            "synthetic": True,
            "age": 24,
            "gravidity": 2,
            "prior_deliveries": 1,
            "height_cm": 156,
            "registration_weight": 58,
        },
        "visit_one": {
            "gestational_week": 16,
            "systolic": 110,
            "diastolic": 70,
            "weight_kg": 56,
            "pulse": 80,
            "haemoglobin": 11.2,
        },
        "visit_two": {
            "gestational_week": 22,
            "systolic": 118,
            "diastolic": 76,
            "weight_kg": 58,
            "pulse": 88,
            "haemoglobin": None,
        },
    }
).encode()


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class MemorySampler(threading.Thread):
    """Samples the resident memory of a process and its children every 50 ms."""

    def __init__(self, pid: int) -> None:
        super().__init__(daemon=True)
        self._process = psutil.Process(pid)
        self.peak_bytes = 0
        self._stop = threading.Event()

    def run(self) -> None:
        while not self._stop.is_set():
            try:
                members = [self._process, *self._process.children(recursive=True)]
                self.peak_bytes = max(self.peak_bytes, sum(p.memory_info().rss for p in members))
            except psutil.NoSuchProcess:
                return
            time.sleep(0.05)

    def stop(self) -> None:
        self._stop.set()


def predict_once(base: str, headers: dict[str, str]) -> float:
    """One signed in POST /api/predict; returns the latency in milliseconds."""
    request = urllib.request.Request(f"{base}/api/predict", data=PAYLOAD, headers=headers)
    start = time.perf_counter()
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()
        if response.status != 200:
            raise RuntimeError(f"status {response.status}")
    return (time.perf_counter() - start) * 1000


def percentile(values: list[float], q: float) -> float:
    """Percentile by linear interpolation, q between 0 and 100."""
    return statistics.quantiles(values, n=100, method="inclusive")[round(q) - 1]


def start_server(port: int, database: Path) -> tuple[subprocess.Popen, float]:
    """Start uvicorn and return the process and seconds until /health answers."""
    env = {**os.environ, "ANTENATAL_DATABASE_URL": f"sqlite:///{database}"}
    command = [sys.executable, "-m", "uvicorn", "webapp.app.main:app", "--port", str(port)]
    start = time.perf_counter()
    server = subprocess.Popen(
        command, cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    while time.perf_counter() - start < 120:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1):
                return server, time.perf_counter() - start
        except OSError:
            time.sleep(0.05)
    server.kill()
    raise RuntimeError("server did not start within 120 seconds")


def machine() -> dict[str, object]:
    """CPU, memory, operating system and Python version of this machine."""
    cpu = platform.processor() or platform.machine()
    if sys.platform == "darwin":
        brand = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True
        )
        cpu = brand.stdout.strip() or cpu
    elif sys.platform == "linux":
        info = Path("/proc/cpuinfo").read_text(errors="ignore").splitlines()
        names = [line.split(":", 1)[1].strip() for line in info if line.startswith("model name")]
        cpu = names[0] if names else cpu
    return {
        "cpu": cpu,
        "logical_cores": psutil.cpu_count(logical=True),
        "ram_gb": round(psutil.virtual_memory().total / 1024**3, 1),
        "os": platform.platform(),
        "python": platform.python_version(),
    }


def summarise(latencies: list[float]) -> dict[str, float]:
    return {
        "requests": len(latencies),
        "p50_ms": round(percentile(latencies, 50), 1),
        "p95_ms": round(percentile(latencies, 95), 1),
        "max_ms": round(max(latencies), 1),
    }


def run() -> dict[str, object]:
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory() as tmp:
        database = Path(tmp) / "bench.sqlite3"
        server, startup = start_server(port, database)
        sampler = MemorySampler(server.pid)
        sampler.start()
        try:
            headers = create_account(f"sqlite:///{database}", base).headers()
            predict_once(base, headers)
            sequential = [predict_once(base, headers) for _ in range(SEQUENTIAL)]
            with ThreadPoolExecutor(max_workers=CONCURRENT) as pool:
                start = time.perf_counter()
                concurrent = list(
                    pool.map(lambda _: predict_once(base, headers), range(CONCURRENT))
                )
                wall = time.perf_counter() - start
        finally:
            sampler.stop()
            server.terminate()
            server.wait(timeout=30)
    return {
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "machine": machine(),
        "startup_seconds": round(startup, 2),
        "peak_rss_mb": round(sampler.peak_bytes / 1024**2, 1),
        "sequential": summarise(sequential),
        "concurrent": {**summarise(concurrent), "wall_seconds": round(wall, 2)},
        "warm_up_requests": 1,
    }


def write(result: dict[str, object]) -> None:
    out = ROOT / "docs" / "evidence"
    out.mkdir(parents=True, exist_ok=True)
    (out / "performance.json").write_text(json.dumps(result, indent=2))
    m, s, c = result["machine"], result["sequential"], result["concurrent"]
    text = f"""# Performance evidence

Measured by `scripts/benchmark_api.py` on {result["recorded_at"]}. The script started
its own server (one uvicorn worker, a temporary SQLite file), waited for `/health`,
sent one warm up request, then {s["requests"]} sequential and {c["requests"]} concurrent
`POST /api/predict` requests from the same machine. The raw numbers are in
`performance.json`.

## Machine

| Item | Value |
| --- | --- |
| CPU | {m["cpu"]} |
| Logical cores | {m["logical_cores"]} |
| RAM | {m["ram_gb"]} GB |
| Operating system | {m["os"]} |
| Python | {m["python"]} |

## Results

| Measure | Value |
| --- | --- |
| Start up, launch to first `/health` answer | {result["startup_seconds"]} seconds |
| Peak resident memory of the server | {result["peak_rss_mb"]} MB |
| Sequential, p50 latency | {s["p50_ms"]} ms |
| Sequential, p95 latency | {s["p95_ms"]} ms |
| Sequential, slowest request | {s["max_ms"]} ms |
| Concurrent, p50 latency | {c["p50_ms"]} ms |
| Concurrent, p95 latency | {c["p95_ms"]} ms |
| Concurrent, slowest request | {c["max_ms"]} ms |
| Concurrent, wall time for all requests | {c["wall_seconds"]} seconds |

The server runs one worker, which handles the concurrent requests one after another,
so concurrent latency includes the time each request waits for the ones ahead of it.
These numbers describe one laptop with client and server on the same machine. They
are not a measure of performance on a health worker's phone or over a network.
"""
    (out / "performance.md").write_text(text)


if __name__ == "__main__":
    outcome = run()
    write(outcome)
    print(json.dumps(outcome, indent=2))
