# Phase 1 — Deployment & Architecture Comparison Report

## 1. Latency & Performance Comparison

| Deployment Target | Paradigm | Cold Start Latency | Warm Median Latency |
| :--- | :--- | :--- | :--- |
| **Compute Engine (`echo-vm`)** | IaaS | 251.5 ms | 211.6 ms |
| **Cloud Run (`echo-bot`)** | PaaS (Containers) | 1926.8 ms | 634.6 ms |
| **Cloud Functions (`echo`)** | FaaS (Serverless) | 661.3 ms | 638.0 ms |

### Analysis of Latency Profiles
- **Compute Engine (VM):** Shows virtually no cold-start overhead (~251.5 ms vs ~211.6 ms warm). Because the VM and its Docker daemon remain continuously active in memory, no container initialization or sandbox bootstrap occurs upon request arrival. The recorded latency is predominantly dominated by the physical network round-trip time between the client and the `us-central1` datacenter.
- **Cloud Run:** Demonstrates a pronounced cold-start penalty (~1926.8 ms). Configured with `--min-instances=0`, Cloud Run scales to zero idle workers during periods of inactivity. An incoming request triggers infrastructure provisioning, gVisor micro-VM sandbox initialization, image layer pulling/unpacking, and Gunicorn/Uvicorn process binding to port 8080. Once the container is warm, latency stabilizes at ~634.6 ms.
- **Cloud Functions (gen 2):** Exhibits a moderate cold start (~661.3 ms) that sits exceptionally close to its warm baseline (~638.0 ms). Under Cloud Functions 2nd Gen, the Google-managed execution runtime and Python worker bootstrap with minimal cold overhead for simple, focused entry points.

---

## 2. Artifacts & Deployment Characteristics

- **Docker Image Size:** The multi-stage build using `python:3.11-slim` separates build-time dependencies from the runtime image, resulting in a production image size well under 200 MB, well within the mandatory 400 MB constraint.
- **Image Deployment vs. Source Deployment:**
  - **Compute Engine & Cloud Run:** Deploy from a pre-built, immutable container image hosted on Google Artifact Registry (`us-central1-docker.pkg.dev/.../eurecomgpt/echo-bot:v1`). This guarantees strict environmental parity between local testing and cloud execution.
  - **Cloud Functions (gen 2):** Deploys directly from raw application source code (`phase-1-echo-bot/`), leveraging Google Cloud Build and Cloud Native Buildpacks under the hood to compile dependencies and generate the underlying container image automatically.

---

## 3. Operational Overhead, Autoscaling & Cost Trade-Offs

### Infrastructure as a Service (Compute Engine)
- **Operational Burden:** High. Requires explicit Virtual Private Cloud (VPC) network planning, firewall ingress rules (ports 22 and 8080), continuous OS security patching, manual Docker installation, and systemd daemon management.
- **Autoscaling:** Coarse-grained. Requires configuring Managed Instance Groups (MIGs), health check thresholds, and external Cloud Load Balancers. It cannot scale to zero instances natively.
- **Cost Structure:** Inefficient for variable workloads. Billed continuously per second for provisioned vCPU, RAM, and persistent disk allocations regardless of whether requests are actively being processed.

### Platform as a Service (Cloud Run)
- **Operational Burden:** Low. Serverless container execution abstracts operating system maintenance, TLS termination, horizontal routing, and Cloud Logging ingestion completely.
- **Autoscaling:** Ultra-rapid and granular (`--min-instances=0` to `--max-instances=3`). Instantly scales up on incoming HTTP concurrency and scales to zero when traffic ceases.
- **Cost Structure:** Highly cost-efficient pay-per-use billing model. Charges accumulate strictly during active request processing times down to the nearest 100 milliseconds.

### Function as a Service (Cloud Functions gen 2)
- **Operational Burden:** Minimal. Completely removes the operational concept of a web server or Dockerfile. The developer focuses purely on the single event-handling Python function (`echo`).
- **Autoscaling:** Managed seamlessly by the platform (`--min-instances=0` to `--max-instances=3`), spinning up instances dynamically on incoming HTTP invocations.
- **Cost Structure:** Granular per-invocation pricing factoring memory, CPU allocation, and execution duration, tailored for event-driven micro-tasks.

---

## 4. Deep-Dive: Why Two Numbers Look Alike (`gcloud run services list`)

### Command Output Observation
Executing the inspection command:
```bash
gcloud run services list
```
yields both targets side-by-side in the Cloud Run service registry:
- `echo-bot` (the containerized service deployed to Cloud Run)
- `echo` (the function deployed via `gcloud functions deploy`)

### Architectural Analysis: How the Function is Actually Executed
1. **Infrastructure Equivalence Under the Hood:**
   Google Cloud Functions (2nd Gen) is not a distinct virtualization stack; it is built directly on top of **Google Cloud Run** and **Knative**. When source code is deployed to Cloud Functions, Google invokes Cloud Build with Cloud Native Buildpacks to package the code and its Functions Framework wrapper into an OCI container image. That container is subsequently deployed and executed as an internal Cloud Run service.

2. **Why Cloud Run and Cloud Function Timings Align:**
   Because Cloud Functions gen 2 runs as an authentic Cloud Run service, both targets traverse identical runtime paths:
   - Identical gVisor application sandboxing.
   - Identical scale-to-zero lifecycle hooks and internal Google Front End (GFE) reverse proxy routing.
   - Identical network hops and latency characteristics once warm (~634.6 ms vs ~638.0 ms).
   The minor difference in initial cold-start latency (~1926.8 ms for Cloud Run vs ~661.3 ms for Cloud Functions) is driven by custom multi-tier container layers and WSGI server startup in Cloud Run versus the highly stripped, optimized entry point provided by the Functions Framework runtime.

3. **What Genuinely Differs Between the Two Deployment Paths:**
   - **Contract & Control:** Cloud Run provides total control over the environment contract (`Dockerfile`, custom OS system libraries, custom web servers like FastAPI/Uvicorn or Gunicorn, and tunable multi-request concurrency per container).
   - **Abstraction Level:** Cloud Functions enforces a strict FaaS contract where container construction, HTTP server wrapping, and runtime lifecycle are completely abstracted away in exchange for rapid developer iteration.
