LoadTester
A lightweight, flexible Python CLI load testing tool you can run locally or deploy as a container on Azure. Designed for developers who want quick, clear insights into API performance without the overhead of complex frameworks.
🚀 Why LoadTester?
- Run Anywhere: Use it on your laptop for fast feedback or scale it in Azure as a container.
- Full Control: Shape traffic with concurrency, QPS (rate limiting), fixed request counts, or test duration.
- Flexible Requests: Configure HTTP methods, headers, payloads, and toggle TLS with ease.
- Actionable Metrics: Get clean output with latency percentiles, throughput, and error rates — no guesswork.

🎯 Perfect For
- Developers validating API performance before release.
- Teams adding lightweight load checks into CI/CD pipelines.
- Cloud-native setups where containerized testing fits right in






Features of LoadTester
- Async engine: Efficient aiohttp + asyncio for high concurrency.
- Rate limiting: Token-bucket QPS control to avoid accidental overloads.
- Flexible requests: Methods, headers, payload from file or inline, timeouts, TLS verify off.
- Metrics: Success/failure counts, status breakdown, throughput, mean/median/p95/p99 latency.
- Outputs: Human-readable summary and optional JSON file.
- CSV per-request logs for deeper analysis.
- Open-loop vs. closed-loop modes (strict QPS scheduling vs. fire-on-completion).
- Scenario scripting for multiple endpoints and weighted mixes.


# ------------ Metrics ------------
    start_time
    end_time
    total_requests
    successful
    failed
    status_counts
    latencies_ms
    bytes_received
# ------------ Rate Limiter ------------
    rate
    capacity = int(burst if burst is not None else max(1, int(rate_per_sec)))
# ------------ Usage examples ------------
- Run a 60s GET test at 200 RPS with 50 workers:

   `` python loadtester.py https://example.com -c 50 --qps 200 -d 60``
    
- Run a 30s GET test at 200 RPS with 5 workers saving results to a results.csv and showing the live progress of the live test:


    ``python loadtester.py https://www.google.com -c 5 -d 30 --qps 200 --csv results.csv --print_progress``

    
    



Tips for accurate tests if hosted on Azure
- Warm up: Run a short warm-up (e.g., 30s) to stabilize TLS/session setup.
- Avoid local bottlenecks: Increase --cpu/--memory for the container if latency is inflated.
- Distribute load: For higher RPS, deploy multiple containers and aggregate their JSON outputs.
- Network constraints: ACI egress may throttle at high rates; consider Azure VMs or Container Apps for very large tests.
- Target backoff: Use --qps to respect service limits and avoid triggering rate limits on the target.



