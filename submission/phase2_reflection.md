# Phase 2 Reflection - Tiny-GPT

## 1. Attention Optimization & SIMD
- **Naive Attention**: 267.64 ms
- **Vectorized Attention**: 1.13 ms
- **Speedup**: 236.85x
Vectorization with OpenBLAS leverages SIMD operations (AVX/AVX2) and memory cache alignment, eliminating the severe Python interpreter overhead and nested loops present in the naive implementation.

## 2. Multi-Threading & Contention
- **Thread Sweep**: 1T: 2651.81 ms | 2T: 2200.63 ms | 4T: 2325.58 ms | 8T: 2302.07 ms
Performance peaks at 2 threads. Scaling past 2 threads causes contention, cache thrashing, and thread management overhead because the Colab instance provides only 2 physical/vCPU cores.

## 3. Hardware Acceleration (CPU vs. GPU)
- **CPU (100 steps)**: 448.18 s
- **GPU T4 (100 steps)**: 14.80 s
- **Speedup**: 30.29x
The GPU delivers massive parallel throughput tailored for dense matrix multiplications (GEMM) inside multi-head attention and feed-forward layers.

## 4. Final Training
- **Steps**: 2000
- **Final Loss**: 1.477 (converged below target 3.0)
- **Model URL**: https://storage.googleapis.com/demircieurecomgpt-eurecomgpt/model.safetensors
