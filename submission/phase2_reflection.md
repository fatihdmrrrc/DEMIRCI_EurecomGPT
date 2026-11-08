# Phase 2 — Reflection: where does parallelism stop helping?

Copy this file to `submission/phase2_reflection.md`, fill in every answer slot, and commit it:

```bash
cp phase-2-tiny-gpt/reflection_template.md submission/phase2_reflection.md
```

**How to fill it in.** Each answer sits between a pair of `<!--answer:...-->` markers. Replace
the `TODO` line with your answer — **leave the markers themselves untouched**, they are how the
grader finds your answers. Anything you write outside the markers is ignored, so add extra
prose, tables or your threading plot freely.

Numbers in section 1 must **match `submission/phase2_report.json`** — copy them across, do not
retype from memory; they are checked against it.

---

## 1. Your measurements

| | Value |
|---|---|
| Naive attention, ms (`attention.naive_ms`) | <!--answer:attn_naive_ms-->267.64<!--/answer--> |
| Vectorized attention, ms (`attention.vectorized_ms`) | <!--answer:attn_vectorized_ms-->1.13<!--/answer--> |
| CPU training, ms for 100 steps (`devices.cpu_ms`) | <!--answer:cpu_ms-->448178.0<!--/answer--> |
| GPU training, ms for 100 steps (`devices.gpu_ms`) | <!--answer:gpu_ms-->14798.0<!--/answer--> |
| Final training loss (`training.final_loss`) | <!--answer:final_loss-->1.477<!--/answer--> |

**The thread sweep.** Give your four timings from `threads` — 1, 2, 4 and 8 threads — and say
which count was fastest. (verbatim: the numbers, in order)

<!--answer:thread_sweep-->
1 thread: 2651.81 ms
2 threads: 2200.63 ms
4 threads: 2325.58 ms
8 threads: 2302.07 ms
Fastest count: 2 threads
<!--/answer-->

---

## 2. Intra-node parallelism, three ways

**Why vectorizing wins.** Both attention implementations do the same arithmetic and produce the
same result (the unit test checks that). Explain where the naive version's time actually goes,
and what the vectorized one does differently — in terms of the machine, not the Python.
(~70 words)

<!--answer:vectorization_why-->
The naive attention spends most execution cycles stalled on sequential memory fetches, non-contiguous cache line traversals, and scalar CPU instructions processing one element per clock cycle. The vectorized BLAS implementation reorganizes memory into continuous cache-friendly blocks and executes SIMD instructions (such as AVX/AVX2). This enables 256-bit or 512-bit registers to compute 8 to 16 floating-point multiply-accumulate operations simultaneously in parallel hardware execution pipelines.
<!--/answer-->

**Where the thread curve flattens, and why.** Using your sweep: more threads stopped helping —
or started hurting — at some point. Say where, and give the reason. Your Colab runtime's vCPU
count is part of the answer; so is what the threads have to coordinate on. (~80 words)

<!--answer:threading_plateau-->
Scaling stopped helping at 2 threads (2200.63 ms), regressing at 4 threads (2325.58 ms). The standard Google Colab instance allocates exactly 2 virtual CPU cores. Spawning 4 or 8 threads introduces software oversubscription, triggering heavy OS context-switching overhead and cache thrashing. Furthermore, threads repeatedly synchronize on global reduction barriers, OpenMP mutex locks, and parameter gradient accumulations, creating memory contention on the shared L3 cache that quickly outweighs any algorithmic parallel benefit.
<!--/answer-->

**What made the GPU faster.** The model, the data and the step count were identical; only the
device changed. Say what about a transformer training step suits a GPU, and name one workload
that would *not* see this speed-up. (~70 words)

<!--answer:gpu_why-->
Transformer steps consist predominantly of dense General Matrix Multiplications (GEMM) in multi-head projections and feed-forward layers, parallelized across thousands of CUDA streaming multiprocessors. A workload that would not see this speed-up is autoregressive token decoding with a batch size of 1 without KV caching or recurrent state transitions, which is severely memory-bandwidth bound and serialized, leaving GPU compute cores largely idle due to latency-sensitive single-token data dependencies.
<!--/answer-->

---

## 3. The question

**Where does parallelism stop helping, and why?** Pull the three experiments together. Your
answer should distinguish the *kinds* of limit you met — work that cannot be divided, hardware
you do not have, coordination that costs more than it saves, data that has to move — and say
which one bound each experiment. One concrete number from section 1 per claim. (~150 words)

<!--answer:parallelism_limit-->
Parallelism stops helping when constrained by physical execution bottlenecks rather than raw computational throughput. First, hardware availability bounds CPU multi-threading: performance improved from 2651.81 ms (1T) to 2200.63 ms (2T), but exceeding the physical 2 vCPUs caused coordination and scheduling contention, regressing to 2325.58 ms at 4T. Second, memory access patterns bound intra-core execution: naive attention took 267.64 ms due to scalar memory latency, whereas SIMD vectorization eliminated memory transfer stalls, achieving 1.13 ms (a 236.85x speedup). Third, architectural suitability bounds device parallelism: CPU training required 448178.0 ms (448.18 s) because sequential architectures cannot parallelize massive matrix tiles, whereas GPU hardware parallelization reduced it to 14798.0 ms (14.80 s, a 30.29x speedup). Ultimately, parallelism fails when Amdahl's serialized fraction dominates, when memory bandwidth starves compute units, or when thread synchronization overhead exceeds divide-and-conquer gains.
<!--/answer-->

**What you would measure next.** One experiment this phase did not run that would sharpen the
answer, and what result would change your mind. (~50 words)

<!--answer:next_experiment-->
I would profile batch size scaling (1 to 128) against GPU memory bandwidth and compute utilization. Observing execution time scale sub-linearly would confirm compute saturation, whereas a linear scaling would disprove compute limits and reveal memory bandwidth as the true bottleneck.
<!--/answer-->