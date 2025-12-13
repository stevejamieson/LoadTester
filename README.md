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


⚡ Quick Start

Install - Clone the repo and install dependencies:

    git clone https://github.com/stevejamieson/LoadTester.git
    cd LoadTester
    pip install -r requirements.txt

Or build/run with Docker:

    docker build -t loadtester .
    docker run loadtester --help

# Run a Basic Test
Send 100 requests to an endpoint:

    python loadtester.py  https://api.example.com --qps 100

# Control Concurrency
Run with 20 concurrent workers:

    python loadtester.py  https://api.example.com -c 20 --qps 100

# Rate Limit (QPS)
Throttle to 200 requests per second for 60 seconds:

    python loadtester.py  https://api.example.com --qps 200 --duration 60


# Rate Limit (QPS) and saving results to csv
Throttle to 100 requests per second with 5 workers for 30 seconds:

    python loadtester.py https://www.google.com -c 5 -d 30 --qps 100 --csv results.csv --print_progress

# Custom Headers & Payload

    python loadtester.py --url https://api.example.com \
    --method POST \
    --header "Authorization: Bearer TOKEN" \
    --payload '{"key":"value"}'

# Toggle TLS

    python loadtester.py --url https://api.example.com --tls false


# 📊 Metrics Output Example
After running a test, LoadTester prints clear, human‑readable metrics. Here’s a sample output:

    === Load Test Results ===
    Target URL: https://api.example.com
    Total Requests: 5000
    Successful Responses: 4975
    Failed Responses: 25

    Throughput: 198.4 requests/sec
    Average Latency: 42.7 ms

    Latency Percentiles:
    50th (median):   40 ms
    75th:            55 ms
    90th:            70 ms
    95th:            85 ms
    99th:           120 ms
    Max:            250 ms

    Error Breakdown:
    500 Internal Server Error: 20
    408 Request Timeout: 5

This makes it easy to spot:
- Tail latency issues (e.g., 99th percentile spikes).
- Throughput stability under load.
- Error distribution across response codes.



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



