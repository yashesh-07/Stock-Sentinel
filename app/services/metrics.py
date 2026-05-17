from prometheus_client import Counter, Gauge, Histogram

# 1. API Gateway Telemetry
HTTP_REQUESTS_TOTAL = Counter(
    "sentinel_http_requests_total",
    "Total number of HTTP requests received by the gateway",
    ["method", "endpoint", "http_status"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "sentinel_http_request_duration_seconds",
    "HTTP request latency breakdown in seconds",
    ["method", "endpoint"]
)

RATE_LIMIT_BLOCKED_TOTAL = Counter(
    "sentinel_rate_limit_blocked_total",
    "Total number of notification requests intercepted by the sliding window limiter",
    ["user_id"]
)

# 2. Asynchronous Queue Worker Telemetry
NOTIFICATION_TASKS_TOTAL = Counter(
    "sentinel_notification_tasks_total",
    "Total count of background notification tasks processed",
    ["channel", "status"]
)

NOTIFICATION_RETRY_TOTAL = Counter(
    "sentinel_notification_retries_total",
    "Total number of network transmission retries executed",
    ["channel"]
)

ACTIVE_WORKER_TASKS = Gauge(
    "sentinel_active_worker_tasks",
    "Number of notification tasks currently being processed by workers concurrently"
)