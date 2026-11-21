# Phase 3 — Comparison Writeup

Copy this file to `submission/phase3_comparison.md`, fill in every answer slot, and commit it:

```bash
cp phase-3-mapreduce-spark/comparison_template.md submission/phase3_comparison.md
```

**How to fill it in.** Each answer sits between a pair of `<!--answer:...-->` markers. Replace
the `TODO` line with your answer — **leave the markers themselves untouched**, they are how the
grader finds your answers. Anything you write outside the markers is ignored, so add extra
prose, tables or images freely.

Numbers in section 1 must **match `submission/phase3_report.json`** — copy them across, do not
retype from memory; they are checked against it.

---

## 1. Facts from your runs

Numbers only (e.g. `12`, `20.3`, `0.041`).

| | Value |
|---|---|
| Map tasks in the cloud job (`mapreduce.num_splits`) | <!--answer:num_map_tasks-->12<!--/answer--> |
| Reduce tasks in the cloud job (`mapreduce.num_reducers`) | <!--answer:num_reduce_tasks-->4<!--/answer--> |
| Cloud MapReduce wall time, seconds (`mapreduce.cloud_elapsed_s`) | <!--answer:cloud_elapsed_s-->38.5<!--/answer--> |
| Local single-process wall time, seconds (`mapreduce.local_elapsed_s`) | <!--answer:local_elapsed_s-->0.008<!--/answer--> |
| Spark wall time for the `collect`, seconds (`tfidf.spark_elapsed_s`) | <!--answer:spark_elapsed_s-->5.1<!--/answer--> |
| Number of **stages** in the Spark job (read off notebook 2b / 3a) | <!--answer:num_stages-->4<!--/answer--> |
| Task **retries** you counted in your `--chaos` run (0 if none happened) | <!--answer:chaos_retries-->9<!--/answer--> |

**Explain the timings.** The three wall times above cover the same 60 documents, but not the
same job: the single-process run and the cloud MapReduce are *the same word count*; Spark's
time is for *TF-IDF*, which is more work (two `reduceByKey`s and a `join`). Rank the three and
explain what each is spending its time on. Say which comparison is like-for-like, and what the
Spark number — a heavier job, on one machine — tells you about where the cloud job's time goes.
(~80 words)

<!--answer:timing_explanation-->
Ranked fastest to slowest: local single-process word count (0.008 s), Spark TF-IDF (5.1 s), and Cloud MapReduce word count (38.5 s). The like-for-like comparison is local vs. Cloud MapReduce, which run the identical word-count algorithm; local finishes in RAM with zero coordination, while Cloud MapReduce spends almost all of its time on Cloud Workflows orchestration, Cloud Run function cold starts/HTTP calls, Cloud Storage shuffle round-trips, and chaos retry backoffs. Because Spark completes a heavier TF-IDF pipeline in 5.1 s on one machine (mostly JVM/Python worker serialization and local scheduling), the cloud job's 38.5 s is overwhelmingly distributed I/O and control-plane overhead rather than compute.
<!--/answer-->

**What the counts tell you.** From your stage count: how many shuffles did the Spark job have,
and which operations in `spark_tfidf.py` caused them? From your retry count: roughly what
fraction of the 16 task attempts was retried, and is that what `--chaos 0.3` should produce?
(~50 words)

<!--answer:counts_interpretation-->
Four stages correspond to 3 shuffles: the first `reduceByKey` in `term_freq`, the second `reduceByKey` in `doc_freq`, and the `join` in `build_tfidf_rdd`. With 9 retries across 16 tasks (25 total attempts), 9/25 = 36% of attempts failed and were retried (9/16 = 56% of tasks). With `--chaos 0.3`, the expected per-attempt failure rate is 30% (~6.9 expected retries), so 9 retries is consistent with random variance.
<!--/answer-->

---

## 2. Spark: transformations, actions, lineage

**Transformations vs actions.** Go through `spark_tfidf.py` and the notebook's Spark cells.
Name each RDD operation and say whether it is a transformation or an action. What happened
when you ran `build_tfidf_rdd` — and what happened when you ran `collect`? (~60 words)

<!--answer:transformations_vs_actions-->
The lazy transformations are `parallelize` (creates the source RDD), `flatMap` and `reduceByKey` in `term_freq`, `map` and `reduceByKey` in `doc_freq`, and `map`, `join`, and the final `map(to_row)` in `build_tfidf_rdd`. The only action is `collect()` in section 2c. Calling `build_tfidf_rdd` returned immediately without running any tasks—it only built the lineage DAG. Calling `collect()` triggered Spark to split the DAG into 4 stages (12 tasks), execute them, and return the 5,975 rows to the driver.
<!--/answer-->

**Lineage and recovery.** Using the lineage you printed in 2b and the timeline in 3a: if the
worker holding one output partition of the *first* `reduceByKey` died, what would Spark have
to recompute, and what could it reuse? Name the stage or shuffle boundary where the recovery
starts. (~50 words)

<!--answer:lineage_recovery-->
Recovery starts at the first shuffle boundary (`ShuffledRDD[3]` / `MapPartitionsRDD[4]` between Stage 0 and Stage 1, from `reduceByKey` at `spark_tfidf.py:32`). Spark reuses the intact shuffle output files (51.0 KB) already materialized on disk by Stage 0's map tasks and only recomputes the single lost partition by re-fetching its slice of those shuffle files—without recomputing Stage 0 or any unaffected partitions.
<!--/answer-->

---

## 3. Your cloud MapReduce, mapped onto Hadoop

Name the GCP service or file that played each role (one line each):

- **JobTracker** (schedules tasks, waits for the map phase, retries failures):
  <!--answer:role_jobtracker-->Cloud Workflows (`mr-wordcount`, defined in `workflow.yaml`)<!--/answer-->
- **Workers** (run your map and reduce code):
  <!--answer:role_workers-->Cloud Run function (`mr-worker`, defined in `main.py`)<!--/answer-->
- **HDFS** (holds inputs, shuffle files, outputs):
  <!--answer:role_hdfs-->Cloud Storage (`gs://demircieurecomgpt-eurecomgpt`, storing `input/`, `shuffle/`, and `output/`)<!--/answer-->
- **Partitioner** (decides which reducer owns a key):
  <!--answer:role_partitioner-->`partition(word, num_reducers)` in `mapreduce.py` (deterministic `zlib.crc32(word) % num_reducers`)<!--/answer-->

**The barrier.** There is no explicit "wait for all mappers" step in `workflow.yaml`. Where,
exactly, is the barrier between the map and reduce phases — which construct provides it?
(~30 words)

<!--answer:barrier_location-->
The barrier is provided implicitly by the `parallel` step wrapping `map_phase` in `workflow.yaml`: a `parallel` step completes only after all concurrent `for`-loop branches finish, preventing the next sequential step (`reduce_phase`) from starting until every mapper succeeds.
<!--/answer-->

**Idempotence.** The workflow retries a task that failed. Why is that safe with the worker as
written, and what would go wrong if `run_map` *appended* its pairs to the shuffle file instead
of overwriting it? (~60 words)

<!--answer:idempotence-->
Retries are safe because `run_map` and `run_reduce` are stateless and overwrite fixed Cloud Storage object paths (`<job>/shuffle/split-<i>/part-<r>.json` and `<job>/output/part-<r>.json`), so re-executing a task yields identical output. If `run_map` appended instead of overwriting, a mapper that wrote some or all pairs before timing out or crashing would leave stale data behind; the retry would append duplicate `(word, 1)` pairs, inflating word counts and breaking consistency with the local reference.
<!--/answer-->

**The chaos run.** What did you see in the execution log and in Logs Explorer when you ran
with `--chaos 0.3`? Did the job still succeed, and was the final answer still identical to the
local reference? (~50 words)

<!--answer:chaos_observations-->
With `--chaos 0.3`, Cloud Logging / Logs Explorer for `mr-worker` recorded 9 HTTP 503 `simulated worker crash` failures (7 during `map_phase` and 2 during `reduce_phase`), and the Workflows execution log showed those branches automatically retrying with exponential backoff. Despite the failures, the job still finished with state `SUCCEEDED` in 38.5 s (vs. 26.1 s without chaos), and the merged counts were identical to the local reference (`matches_local: true`, 2,221 distinct words).
<!--/answer-->
