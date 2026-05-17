# Stock-Sentinel 📈🔔

Stock-Sentinel is a scalable, highly available notification delivery engine designed for processing high volumes of stock price alerts and user notifications. Built with modern distributed system principles, it reliably orchestrates message dispatching across various channels (Email, SMS, Push) while providing comprehensive telemetry, rate limiting, and automated retries for transient network failures.

## 🏗️ High-Level Design (HLD)

Stock-Sentinel is architected around a decoupled flow using a robust backend stack, ensuring maximum availability and durability for time-sensitive notifications.

### 🛠️ Architecture Stack
* **API Gateway (FastAPI):** High-performance, asynchronous REST API for ingesting, validating, and rate-limiting notification payloads.
* **Persistent Storage (PostgreSQL & SQLAlchemy):** 
  * `user_settings`: Maintains opt-in/opt-out preferences and device configurations for each user. (Auto-initialized to reduce integration friction)
  * `notification_logs`: Highly auditable ledger holding the state and lifecycle history of every notification dispatched.
* **Message Broker (Redis):** Acts as a fast, in-memory queue to safely decouple incoming API request bursts from the slow execution paths of external network providers.
* **Asynchronous Workers (Celery):** Distributed worker pool that pulls jobs from Redis, executes the payload transmission (simulated network requests), and updates the PostgreSSQL audit logs. Handles exponential backoff and retries.
* **Observability (Prometheus & Grafana):** Built-in middleware exposes extensive telemetry (`/metrics`). Prometheus aggressively polls these metrics, which Grafana then visualizes for active industrial monitoring.
* **Containerization:** The entire infrastructure is orchestrated via Docker Compose.

### 🚦 Core Workflows
1. **Request Ingestion & Validation:** 
    * A `POST /api/v1/notifications/dispatch` is received. 
    * The API verifies X-Sentinel-API-Key authorization.
    * User preferences are fetched from PostgreSQL (or auto-initialized). If the targeted channel (e.g., `SMS`) is disabled by the user, the payload is safely dropped.
2. **Defensive Rate-Limiting:** 
    * The sliding-window rate limiter ensures a user is not bombarded (Max 5 hits per 60 seconds).
3. **Data Transformation:** 
    * Payload is sanitized. SMS alerts are cleanly truncated to 160 characters.
4. **Decoupled Handoff:**
    * A `PENDING` log is written to PostgreSQL.
    * The dispatch task is injected into the Redis queue immediately so the API can return a 202 Accepted.
5. **Background Execution & Retry Engine:**
    * A Celery worker takes the job from Redis.
    * Interacts with external providers (simulated).
    * Can dynamically enforce backpressure. If the provider rejects the payload or times out, the worker re-queues it with exponential backoff up to a max retry limit.
    * Emits success/failure telemetry hooks to Prometheus during the lifecycle.

## 🚀 Getting Started

### Prerequisites
* Docker & Docker Compose
* Git

### Installation & Execution

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yashesh-07/Stock-Sentinel.git
   cd Stock-Sentinel
   ```

2. **Environment Configuration:**
   Ensure your `.env` file is complete with your desired configurations (e.g., `POSTGRES_USER`, `API_SECRET_KEY`, etc.).

3. **Deploy the Cluster:**
   Spin up all 6 microservice containers simultaneously using Docker Compose.
   ```bash
   docker-compose up --build -d
   ```
   **This provisions:**
   * PostgreSQL (`localhost:5432`)
   * Redis Broker (`localhost:6379`)
   * FastAPI Application (`http://localhost:8000`)
   * Celery Workers (Running detached)
   * Prometheus (`http://localhost:9090`)
   * Grafana (`http://localhost:3000`)

### Verification & Testing
The system contains a simulated integration tester out-of-the-box. Run the integration test suite locally to verify text truncation, structural config parsing, rate limiting, and channel restrictions:
```bash
docker exec -it sentinel_api python app/run_integration_tests.py
```

## 📊 Telemetry & Monitoring

Stock-Sentinel comes fully equipped for enterprise observability.
* **Prometheus Targets:** The scrapers automatically collect payload latency, request sizes, worker concurrency gauges, and task retry counts. Available on `http://localhost:9090`.
* **Grafana Dashboards:** Log in at `http://localhost:3000` (Default credentials specified in your Compose file) and connect Prometheus to visualize system health, active rate-throttle bumps, and Celery queue latencies in real-time.

## 🔐 Security Standards
* **Authentication:** Mandates `X-Sentinel-API-Key` headers on dispatch corridors.
* **Query Safety:** Uses SQLAlchemy ORM to completely mitigate SQL injection vectors.
* **Graceful Degradation:** Foreign key race conditions automatically initialize default user schemas, and workers seamlessly handle DB connection losses using built-in session lifecycles.