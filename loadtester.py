#!/usr/bin/env python3
import asyncio
import aiohttp
import argparse
import json
import signal
import sys
import time
from collections import Counter, deque
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any,List
import csv


# ------------ Metrics ------------

@dataclass
class Metrics:
    start_time: float
    end_time: float = 0.0
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    status_counts: Dict[int, int] = field(default_factory=Counter)
    latencies_ms: List[float] = field(default_factory=list)
    bytes_received: int = 0
    csv_path: Optional[str] = None
    _csv_writer: Optional[csv.DictWriter] = field(init=False, default=None)
    _csv_file: Optional[object] = field(init=False, default=None)

    def __post_init__(self):
        if self.status_counts is None:
            self.status_counts = Counter()
        if self.latencies_ms is None:
            self.latencies_ms = []
        if self.csv_path:
            self._csv_file = open(self.csv_path, "w", newline="", encoding="utf-8")
            self._csv_writer = csv.DictWriter(
                self._csv_file,
                fieldnames=["timestamp", "status", "latency_ms", "bytes_received"]
            )
            self._csv_writer.writeheader()

    def record(self, status: Optional[int], latency_ms: float, bytes_received: int):
        self.total_requests += 1
        if status is not None and 200 <= status < 400:
            self.successful += 1
        else:
            self.failed += 1
        if status is not None:
            self.status_counts[status] += 1
        self.latencies_ms.append(latency_ms)
        self.bytes_received += bytes_received

        if self._csv_writer:
            self._csv_writer.writerow({
                "timestamp": time.time(),
                "status": status,
                "latency_ms": latency_ms,
                "bytes_received": bytes_received
            })
            self._csv_file.flush()  # ensure data is written to disk

    def finalize(self):
        self.end_time = time.time()
        if self._csv_file:
            self._csv_file.close()

    def summary(self) -> Dict[str, Any]:
        elapsed = max(1e-9, self.end_time - self.start_time)
        lat = sorted(self.latencies_ms)
        def pct(p):
            if not lat:
                return None
            idx = int(max(0, min(len(lat)-1, round(p * (len(lat)-1)))))
            return lat[idx]
        return {
            "elapsed_seconds": elapsed,
            "total_requests": self.total_requests,
            "successful": self.successful,
            "failed": self.failed,
            "throughput_rps": self.total_requests / elapsed if elapsed > 0 else 0.0,
            "mean_latency_ms": (sum(lat) / len(lat)) if lat else None,
            "median_latency_ms": pct(0.5),
            "p95_latency_ms": pct(0.95),
            "p99_latency_ms": pct(0.99),
            "status_counts": dict(self.status_counts),
            "bytes_received": self.bytes_received,
            "avg_bytes_per_response": (self.bytes_received / self.total_requests) if self.total_requests else 0,
        }

# ------------ Rate Limiter ------------

class TokenBucket:
    def __init__(self, rate_per_sec: float, burst: Optional[int] = None):
        self.rate = float(rate_per_sec)
        self.capacity = int(burst if burst is not None else max(1, int(rate_per_sec)))
        self.tokens = self.capacity
        self.updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            while self.tokens < 1:
                now = time.monotonic()
                delta = now - self.updated
                # Refill tokens
                refill = delta * self.rate
                if refill >= 1:
                    self.tokens = min(self.capacity, self.tokens + int(refill))
                    self.updated = now
                else:
                    # Sleep until at least 1 token is available
                    sleep_for = (1 - self.tokens) / self.rate if self.rate > 0 else 0.01
                    await asyncio.sleep(max(0.001, sleep_for))
            self.tokens -= 1

# ------------ Worker ------------

async def worker(name: int,
                 session: aiohttp.ClientSession,
                 args,
                 metrics: Metrics,
                 bucket: Optional[TokenBucket],
                 stop_at: Optional[float],
                 remaining_counter: Optional[asyncio.Semaphore]):

    while True:
        # End conditions: duration or fixed requests
        if stop_at is not None and time.time() >= stop_at:
            return
        if remaining_counter is not None:
            try:
                # Try to consume one request unit
                await asyncio.wait_for(remaining_counter.acquire(), timeout=0.01)
            except asyncio.TimeoutError:
                return
        # Rate limit if needed
        if bucket:
            await bucket.acquire()

        started = time.time()
        status = None
        bytes_rcv = 0
        try:
            async with session.request(
                args.method,
                args.url,
                headers=args.headers,
                data=args.data,
                timeout=aiohttp.ClientTimeout(total=args.timeout),
                allow_redirects=args.allow_redirects
            ) as resp:
                status = resp.status
                body = await resp.read()
                bytes_rcv = len(body)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Keep status None to count as failed
            pass
        finally:
            latency_ms = (time.time() - started) * 1000.0
            metrics.record(status, latency_ms, bytes_rcv)

        # If we were doing fixed-request mode and couldn't acquire a token, we should quit.
        if remaining_counter is not None and remaining_counter._value <= 0:
            # Let other workers observe depletion via acquire failure; we continue until semaphore says no.
            pass

# ------------ Main ------------

def parse_args():
    p = argparse.ArgumentParser(description="Simple async load tester for a given URL.")
    p.add_argument("--csv", help="Write per-request details to CSV file.")
    p.add_argument("url", help="Target URL.")
    p.add_argument("-m", "--method", default="GET", help="HTTP method (GET, POST, PUT, DELETE, etc.).")
    p.add_argument("-c", "--concurrency", type=int, default=50, help="Number of concurrent workers.")
    p.add_argument("--qps", type=float, default=0.0, help="Global requests-per-second limit (0 = unlimited).")
    p.add_argument("-d", "--duration", type=float, default=0.0, help="Test duration in seconds (0 = use --requests).")
    p.add_argument("-r", "--requests", type=int, default=0, help="Total number of requests (used when --duration=0).")
    p.add_argument("--timeout", type=float, default=30.0, help="Total request timeout in seconds.")
    p.add_argument("--headers", nargs="*", default=[], help="Headers as key:value pairs, e.g., Authorization:Bearer X")
    p.add_argument("--data", help="Inline payload string. Use @file.json to load from file.")
    p.add_argument("--no-verify", action="store_true", help="Disable TLS verification.")
    p.add_argument("--allow-redirects", action="store_true", help="Follow redirects.")
    p.add_argument("--json-out", help="Write metrics summary to JSON file.")
    p.add_argument("--print_progress", action="store_true", help="Print progress every second.")
    return p.parse_args()

def parse_headers(header_list):
    headers = {}
    for h in header_list:
        if ":" not in h:
            print(f"Invalid header (missing colon): {h}", file=sys.stderr)
            continue
        k, v = h.split(":", 1)
        headers[k.strip()] = v.strip()
    return headers

def load_data(arg):
    if not arg:
        return None
    if arg.startswith("@"):
        path = arg[1:]
        with open(path, "rb") as f:
            return f.read()
    return arg.encode()

async def progress_task(metrics: Metrics):
    last = 0
    while True:
        await asyncio.sleep(1)
        current = metrics.total_requests
        print(f"[progress] total={current} +{current - last}")
        last = current

async def run(args):
    metrics = Metrics(start_time=time.time())

    # Prepare rate limiter and termination conditions
    bucket = TokenBucket(args.qps, burst=args.concurrency) if args.qps and args.qps > 0 else None
    stop_at = time.time() + args.duration if args.duration and args.duration > 0 else None
    remaining_counter = asyncio.Semaphore(args.requests) if (not stop_at and args.requests > 0) else None

    # Build session
    connector = aiohttp.TCPConnector(ssl=not args.no_verify, limit=0)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Progress printer
        progress = None
        if args.print_progress:
            progress = asyncio.create_task(progress_task(metrics))

        # Graceful shutdown on CTRL+C
        shutdown_event = asyncio.Event()
        def _handle_sig():
            shutdown_event.set()
        loop = asyncio.get_event_loop()
        try:
            loop.add_signal_handler(signal.SIGINT, _handle_sig)
            loop.add_signal_handler(signal.SIGTERM, _handle_sig)
        except NotImplementedError:
            # Windows may not support add_signal_handler in Proactor loop; ignore.
            pass

        workers = []
        for i in range(args.concurrency):
            workers.append(asyncio.create_task(worker(
                i, session, args, metrics, bucket, stop_at, remaining_counter
            )))

        # Stop conditions
        if stop_at:
            try:
                await asyncio.wait(
                    workers,
                    timeout=max(0.0, stop_at - time.time())
                )
            except asyncio.CancelledError:
                pass
        else:
            # Fixed request mode: wait until semaphore is exhausted and workers finish
            await asyncio.gather(*workers, return_exceptions=True)

        # Early shutdown
        if shutdown_event.is_set():
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

        metrics.finalize()
        if progress:
            progress.cancel()

    # Print summary
    summary = metrics.summary()
    print("\n=== Load test summary ===")
    for k, v in summary.items():
        print(f"{k}: {v}")

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"Saved JSON summary to {args.json_out}")

def main():
    args = parse_args()
    args.headers = parse_headers(args.headers)
    args.data = load_data(args.data)

    if args.duration <= 0 and args.requests <= 0:
        print("Error: specify either --duration > 0 or --requests > 0", file=sys.stderr)
        sys.exit(1)
    if args.concurrency <= 0:
        print("Error: --concurrency must be >= 1", file=sys.stderr)
        sys.exit(1)

    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("Interrupted.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()