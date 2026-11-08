# Phase 1 — Deployment & Architecture Comparison Report

## 1. Latency & Performance Comparison

| Deployment Target | Paradigm | Cold Start Latency | Warm Median Latency |
| :--- | :--- | :--- | :--- |
| **Compute Engine (`echo-vm`)** | IaaS | 251.5 ms | 211.6 ms |
| **Cloud Run (`echo-bot`)** | PaaS (Containers) | 1926.8 ms | 634.6 ms |
| **Cloud Functions (`echo`)** | FaaS (Serverless) | 661.3 ms | 638.0 ms |

### Analysis of Latency Profiles
- **Compute Engine (VM):** Shows virtually no cold-start overhead (~251 ms vs ~211 ms warm). Because the VM and its Docker daemon remain continuously running, the application process is permanently in memory. The baseline latency is dominated by network round-trip time between the client and `us-central1`.
- **Cloud Run:** Demonstrates a distinct cold-start latency (~1927 ms). Configured with `--min-instances=0`, Cloud Run must provision a container sandbox, pull/unpack the image, launch the Gunicorn server, and bind to port 8080 before serving the initial request. Once warm, latency drops to ~635 ms.
- **Cloud Functions (gen 2):** Shows a moderate cold start (~661 ms) very close to its warm baseline (~638 ms). Under Cloud Functions gen 2, the underlying containerized runtime and Python environment are bootstrapped with minimal overhead for simple single-purpose entry points.

---

## 2. Artifacts & Deployment Characteristics

- **Docker Image Size:** The multi-stage build (`python:3.11-slim`) cleanly separates the build stage from the runner environment, producing an image size under 200 MB, well within the 400 MB target limit.
- **Image Deployment vs. Source Deployment:**
  - **VM & Cloud Run** consume the pre-built, immutable container image hosted on Google Artifact Registry (`us-central1-docker.pkg.dev/.../eurecomgpt/echo-bot:v1`), ensuring strict parity across local and cloud environments.
  - **Cloud Functions (gen 2)** deploys directly from raw source code (`phase-1-echo-bot/`), leveraging Google Cloud Build and Buildpacks under the hood to compile and generate the underlying container automatically.

---

## 3. Operational Overhead, Autoscaling & Cost Trade-Offs

### Infrastructure as a Service (Compute Engine)
- **Operational Burden:** High. Requires manual VPC/subnet configuration, firewall ingress rules (ports 22 and 8080), OS patching, Docker daemon installation, and credentials configuration.
- **Autoscaling:** Manual or requiring Managed Instance Groups (MIG) configured with health checks and load balancers. Cannot scale to zero natively.
- **Cost Structure:** Billed for continuous uptime (vCPU, memory, persistent disk) regardless of incoming HTTP traffic.

### Platform as a Service (Cloud Run)
- **Operational Burden:** Low. Fully managed serverless container runtime. Infrastructure provisioning, TLS termination, routing, and log ingestion are handled transparently.
- **Autoscaling:** Automatic and rapid (`--min-instances=0` to `--max-instances=3`). Scales down to zero idle instances during periods of inactivity.
- **Cost Structure:** Pure pay-per-use billing based on exact vCPU and memory allocation during request execution, making it the most cost-effective option for spiky or low-volume microservices.

### Function as a Service (Cloud Functions gen 2)
- **Operational Burden:** Minimal. Focused exclusively on application code and the entry point function (`echo`). Network configuration, container lifecycle, and HTTP servers are abstracted.
- **Autoscaling:** Concurrency-driven autoscaling managed entirely by the platform (`--min-instances=0` to `--max-instances=3`).
- **Cost Structure:** Granular pay-per-invocation billing based on execution duration and allocated resources, fitting event-driven workloads.
