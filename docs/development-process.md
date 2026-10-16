# Development Process

This page records how the project was built, who decided what, and which problems came up along the way. It is based on the original conversation logs and the project's git history. Times are Malaysia time (UTC+8).

## Roles

| Who | What they did |
|---|---|
| Me (project owner) | Defined the workflow and the storage design, chose the models, wrote and revised requirements for each step, reviewed outputs, decided when to stop, rerun or change direction, and validated results against the assignment workflow. |
| Claude (claude.ai and Claude Code) | Explained concepts, drafted the prompts on request, wrote most of the Python code, ran the jobs, and analysed results. |
| OpenAI Codex CLI | Second-opinion reviewer from a different model family. It reviewed diffs and the prompt v2 draft, looking for bugs and counter-examples. It also translated the code to English for this release. |
| DeepSeek (`deepseek-flash`, `deepseek-v4-pro`) | The models being used to classify requirements. They are what the pipeline runs on, not development tools. |

## Timeline

### 2026-09-29: Workflow design

The assignment: use AI to classify a shared dataset of crowd-sourced requirements into FR or NFR. AI outputs must be saved before any human review and must never be overwritten. Requirement IDs must not change. Run times and results must not be made up.

Design decisions I made in this phase:

- **Two independent classifiers.** Classifier A uses the cheaper `deepseek-flash`; classifier B uses `deepseek-v4-pro`. Both use the same API key, read from a data file, and need no interactive input.
- **Separate storage per classifier.** Each has its own SQLite database holding only `id`, `label` and `time`. Full answers go into JSON files.
- **Keep run time and date** for every run.

I asked whether 3,000+ calls on the same API key could "leak" context between requests. Each request is stateless, so they cannot, but this question is why the code sends every requirement as a separate request with no chat history.

### 2026-09-30: Prompts

At my request, Claude drafted the shared definitions, the boundary rules (R1–R5) and both task prompts. I asked for each part to be explained before I accepted it. During integration, three changes were made and confirmed:

- A and B must not see each other's answer. An earlier plan to pass A's result to B was dropped.
- Each classifier stores its own label, so A and B can be compared row by row by ID.
- The requirement ID is sent with the text, and the model must copy it back unchanged. The script checks this.

### 2026-10-01 to 10-02: Understanding the code, then report layout

- I went through `classify.py` (then `sad_asg.py`) line by line with Claude, so that I could explain it to my teammates.
- **Decision:** the main script should only classify. I asked for the agreement-rate calculation to be removed from it, because a separate script would compute statistics. That script later became `merge_runs.py`.
- **Decision:** I dropped the `nfr_category` and `confidence` fields from the output to keep the task focused on FR/NFR.
- Several rounds of Excel layout changes followed: A/B side by side, a model-name row, a blank separator column, frozen ID and requirement columns, one font. The goal was a sheet that teammates could read without help.

### 2026-10-16: Real data and the full run

| Time | What happened |
|---|---|
| 10:13 | Received the frozen survey dataset (243 respondents × 22 questions). Wrote `prepare_data.py` to turn the wide sheet into one requirement per row with IDs like `001-01`. **The IDs deliberately do not contain "FR" or "NFR"**, so they do not hint at the answer. Added 8-way concurrency. |
| 10:16 | Codex reviewed the diff and reported 6 issues. One was real: on a fatal API error, finished results still in flight could be lost. It was fixed. The other 5 were judged not to need changes. |
| 10:17 | Full v1 run started. |
| ~10:40 | The API balance ran out. B received 71 rate-limit errors (HTTP 429), then HTTP 402. **I noticed the run had stopped and topped up the balance.** |
| 10:43 | The script was hanging after the 402. Cause: cancelled futures never wake up `as_completed`. The process was stopped with SIGINT; all 2,140 finished rows were saved. The fix: `shutdown(wait=True)`, then collect every finished future. |
| 10:46 | Added `--skip-done`, which reruns only rows where A or B did not finish. Old results are never overwritten. |
| 10:50 | Codex reviewed the resume code and found a real bug: it matched rows by ID only and did not check that the requirement text was unchanged. Fixed in both the resume code and the merge step. |
| 10:54 | **Decision:** finish the full dataset instead of stopping at a partial sample, even though `deepseek-v4-pro` is the expensive part. |
| 11:02 | **I asked for the prompt to be audited** against the results so far. Four problems were found (see [prompt-design.md](prompt-design.md)). |
| 11:04 | **Decision:** keep v1 as the official raw AI output, and test a v2 prompt only on the disputed rows after the full run finishes. Codex looked for counter-examples in the v2 draft and reported 10; 7 were accepted, which led to changes in R6, R7 and R10. |
| 11:31 | The v1 resume run finished with 0 errors. Results were merged into the final Task 1 workbook. |
| 11:31–11:38 | v2 was tested on the 244 disputed rows, with 0 errors. |
| 14:02–14:11 | The working folder was reorganised (data / results / logs / final). The merge script now refuses to overwrite human-review columns that already contain data. Human-review columns got drop-down lists. |

### 2026-10-16: Portfolio release

- Comments, docstrings, CLI messages, Excel headers and documentation were translated from Chinese to English. Program logic was not changed (see the table in the README).
- The survey data was left out. Only a 40-row anonymised sample is published.

## Problems found and how they were handled

| # | Problem | Found by | Fix |
|---|---|---|---|
| 1 | A fatal API error during a concurrent run could lose results that had already finished | Codex review | Wait for in-flight work and record every finished future before stopping |
| 2 | The script hung forever after HTTP 402 | Noticed by me (the run had stopped); diagnosed by Claude | `shutdown(wait=True, cancel_futures=True)`, then check each future |
| 3 | No way to continue a partial run without paying again for finished rows | Raised by the balance problem | `--skip-done RUN_JSON...` |
| 4 | Resume matched rows by ID only, so edited requirement text could be skipped | Codex review | Resume and merge both require the same ID **and** the same text |
| 5 | B's step 2 leaned towards FR: "the system does something" counted as FR, even for encryption | Prompt audit I asked for | v2 Step 2 asks how a failed test would be reported |
| 6 | The NFR definition was missing accuracy, testability and reusability, so 27–33% of Accuracy items were labelled FR | Prompt audit | Added to the v2 NFR definition, plus rule R7 |
| 7 | Developer-only features (error logs, health checks, mock APIs) were labelled FR | Prompt audit | v2 rule R6 |
| 8 | Short phrases and cells containing several requirements had no rule | Prompt audit | v2 rules R9 and R10 (reason starts with `Mixed:`) |
| 9 | v2 R10 originally said "take the first one", so changing the sentence order could change the label | Codex counter-example review | R10 no longer uses order |
| 10 | Rerunning the merge could wipe teammates' human review | Found while reorganising | Merge refuses to overwrite filled human columns unless `--force` is given |

## Cost and time (v1 full run plus v2 subset)

- **Wall-clock time:** 28 min 35 s + 42 min 53 s for v1 (two runs), and 6 min 48 s for v2.
- **Sum of per-call times** is much larger (A about 79 min, B about 469 min for v1) because 8 rows are processed at once. Both numbers are reported on purpose.
- **Average time per call:** A about 0.8 s, B about 5 s.
- **Cost:** about US$7–8 in total. This is an estimate from dashboard screenshots and balance changes, and the balance was topped up mid-run. About 90% of the cost was `deepseek-v4-pro`.
