# Representative Projects — an eval-first pipeline for decoding job listings

A job listing is a disguised list of problems a company is trying to solve by
hiring. This repo evaluates an LLM pipeline that (1) extracts those problems
with verbatim evidence from the listing and (2, upcoming) proposes a
*representative project* an applicant should build to demonstrate they can
solve them — framing and roadmap only, never code, so the applicant still does
the work.

**The deliverable here is the evaluation, not the pipeline.** The "agent" is
deliberately a single auditable prompt (see the
[design spec](docs/superpowers/specs/2026-09-05-representative-projects-eval-design.md)
and Hamel Husain's
["It's hard to eval is a product smell"](https://hamelhusain.substack.com/p/its-hard-to-eval-is-a-product-smell)):
outputs are structured for verifiability, so most checks are deterministic
code, not LLM judges.

## Quickstart

Requirements: [uv](https://docs.astral.sh/uv/), Node.js (the promptfoo PyPI
wrapper shells out to it), and any OpenAI-compatible endpoint — a local server (vLLM, llama.cpp) or the OpenAI API itself.

```bash
# 1. put your key in .env (promptfoo loads it automatically)
echo 'OPENAI_API_KEY=sk-...' > .env

#    ...or serve locally and point shared/provider.yaml at it by adding
#    `apiBaseUrl: http://localhost:8000/v1` (vLLM) / :8080/v1 (llama.cpp)
#    under config: — model and endpoint live in that file, not in env vars.

# 2. run phase 1 over the corpus
uvx promptfoo@0.1.4 eval -c evals/extract-problems/promptfooconfig.yaml --no-cache --no-share

# 3. read traces in the browser
uvx promptfoo@0.1.4 view

# unit tests (assertion logic)
uv sync && uv run pytest
```

## Layout

| Path | What it is |
|---|---|
| `job_listings/` | Real job listings, one `.txt` per listing — the corpus |
| `evals/extract-problems/` | Phase 1 suite: prompt (the agent), schema, grounding assertion (pure matching logic + promptfoo adapter, one file) |
| `tests/unit/` | pytest, behavior-level, assertion logic only — never harness glue |
| `runs/` | Committed eval snapshots per iteration (`extract-problems-v0.json`, …) |
| `docs/error-analysis/` | Failure taxonomy and labels, built by reading traces (created during round 1) |
| `docs/superpowers/specs/` | The design spec this repo implements |

## Method

1. **v0** ships with *contract* assertions only: schema validity plus a
   zero-LLM grounding check — every evidence quote must appear verbatim in
   the listing (whitespace/punctuation/case-normalized substring match).
2. **Error analysis before evals:** every v0 trace gets read by a human;
   failures are open-coded, then grouped into a failure taxonomy
   (axial coding — the same method the pipeline applies to listings).
3. **Assertions are earned:** each later assertion traces to an observed
   failure mode. Deterministic checks first; an LLM judge only where
   interpretation is irreducible, and only after calibration against hand
   labels.
4. **Iterations are committed:** each prompt revision gets a fresh run in
   `runs/`; the table below tracks what failed → what changed → the delta.

Reading results: an assertion FAILURE is data — the pipeline measurably
misbehaved and feeds error analysis. A pipeline ERROR (provider down, harness
exception) is a bug; runs containing errors are never committed as baselines.

## Iterations

| Version | Change | Result |
|---|---|---|
| v0 | baseline prompt, contract assertions | 9/10 pass on gpt-5.6-luna; 1 grounding failure (paraphrased quote) — `runs/extract-problems-v0.json` |

*Status: phase-1 v0 baseline complete; error analysis round 1 is next.*
