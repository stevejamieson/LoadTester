Features at a glance
- Async engine: Efficient aiohttp + asyncio for high concurrency.
- Rate limiting: Token-bucket QPS control to avoid accidental overloads.
- Flexible requests: Methods, headers, payload from file or inline, timeouts, TLS verify off.
- Metrics: Success/failure counts, status breakdown, throughput, mean/median/p95/p99 latency.
- Outputs: Human-readable summary and optional JSON file.
- CSV per-request logs for deeper analysis.
- Open-loop vs. closed-loop modes (strict QPS scheduling vs. fire-on-completion).
- Scenario scripting for multiple endpoints and weighted mixes.



# ------------ Metrics ------------
    start_time: float
    end_time: float = 0.0
    total_requests: int = 0
    successful: int = 0
    failed: int = 0
    status_counts: Dict[int, int] = None
    latencies_ms: list = None
    bytes_received: int = 0
# ------------ Rate Limiter ------------
    self.rate = float(rate_per_sec)
    self.capacity = int(burst if burst is not None else max(1, int(rate_per_sec)))
    self.tokens = self.capacity
    self.updated = time.monotonic()
    self._lock = asyncio.Lock()
# ------------ Worker ------------


# ------------ Usage examples ------------
- Run a 60s GET test at 200 RPS with 50 workers:
    python loadtester.py https://example.com -c 50 --qps 200 -d 60
    
- POST JSON from file with headers, fixed 10,000 requests:
    python load_tester.py https://api.example.com/resource \
      -m POST --headers "Content-Type:application/json" "Authorization:Bearer XYZ" \
      --data @payload.json -c 100 --requests 10000 --timeout 20 --allow-redirects
- Disable TLS verification (for test endpoints) and save JSON metrics:
    python loadtester.py https://self-signed.local -c 20 -d 30 --no-verify --json-out results.json
- Show per-second progress:
    python loadtester.py https://example.com -d 30 -c 100 --qps 500 --print_progress






Tips for accurate tests if hosted on Azure
- Warm up: Run a short warm-up (e.g., 30s) to stabilize TLS/session setup.
- Avoid local bottlenecks: Increase --cpu/--memory for the container if latency is inflated.
- Distribute load: For higher RPS, deploy multiple containers and aggregate their JSON outputs.
- Network constraints: ACI egress may throttle at high rates; consider Azure VMs or Container Apps for very large tests.
- Target backoff: Use --qps to respect service limits and avoid triggering rate limits on the target.



