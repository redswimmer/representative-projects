# Extract-Problems Suite (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A runnable promptfoo suite that extracts evidence-grounded hiring problems from local job listings via a local OpenAI-compatible endpoint, with a committed v0 baseline run ready for error analysis.

**Architecture:** Prompt-as-agent: the entire "agent" is one chat-format prompt file evaluated by promptfoo; a Python test generator turns `job_listings/*.txt` into test cases; contract assertions (JSON schema + evidence grounding) are the only assertions at v0. Pure domain logic lives in `src/listing_evals/`; promptfoo touches it only through a thin assertion adapter.

**Tech Stack:** promptfoo CLI 0.122.2 via `uvx promptfoo@0.1.4` (PyPI wrapper; requires Node.js at runtime), Python ≥3.13 managed by uv, pytest (sole dev dependency), stdlib-only runtime code.

**Spec:** `docs/superpowers/specs/2026-09-05-representative-projects-eval-design.md`

## Global Constraints

- Run promptfoo ONLY as `uvx promptfoo@0.1.4` (never npx, never unpinned).
- Runtime eval code is stdlib-only; `pytest` is the only dev dependency.
- The corpus directory is `job_listings/` and the generator config key is `job_listings_dir`.
- Every promptfoo YAML starts with `# yaml-language-server: $schema=https://promptfoo.dev/config-schema.json` and orders fields `description, env, prompts, providers, defaultTest, scenarios, tests`. Env refs are quoted: `'{{env.VAR}}'`.
- `temperature: 0`; NO `response_format`/guided decoding at v0 (malformed output is a failure mode error analysis must observe).
- v0 assertions = output contract only (`is-json` + grounding). Do NOT add speculative assertions, and do NOT tune the prompt to make smoke tests pass — v0 failures are error-analysis data.
- Names convey intent (Uncle Bob); core logic is pure functions in `src/listing_evals/` (no promptfoo types, no IO); adapters stay logic-free; unit tests target core behavior only and never import promptfoo (cosmicpython ch. 3 & 5).
- Env vars for all eval runs: `PF_MODEL` (served model name), `PF_BASE_URL` (e.g. `http://localhost:8000/v1`), `PF_API_KEY` (dummy value fine locally).
- Eval runs use `--no-cache --no-share`.
- Every commit message ends with this trailer block (verbatim):

  ```
  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01PraDda2WTYDqQfzVAZNXhV
  ```

---

### Task 1: Repo hygiene + Python tooling

**Files:**
- Delete: `main.py`, `context.py`, `promptfooconfig.yaml` (root — stock scaffold examples)
- Modify: `pyproject.toml` (full replacement below)

**Interfaces:**
- Consumes: nothing.
- Produces: a uv project where `uv run pytest` works and discovers `tests/unit/` with `src/` on `pythonpath`. Later tasks rely on exactly these pyproject settings.

- [ ] **Step 1: Delete scaffold files**

```bash
git rm main.py context.py promptfooconfig.yaml
```

- [ ] **Step 2: Replace pyproject.toml with**

```toml
[project]
name = "representative-projects"
version = "0.1.0"
description = "Promptfoo evals for a job-listing problem-extraction pipeline"
readme = "README.md"
requires-python = ">=3.13"
dependencies = []

[dependency-groups]
dev = ["pytest>=8"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests/unit"]
```

- [ ] **Step 3: Sync and verify pytest wiring**

Run: `uv sync && uv run pytest`
Expected: sync installs pytest; pytest exits with "no tests ran" (exit code 5). That is success at this stage.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "chore: remove stock scaffold, add pytest tooling"
```

(Include the Global Constraints trailer block in this and every commit.)

---

### Task 2: Core grounding logic (TDD)

**Files:**
- Create: `src/listing_evals/__init__.py` (empty)
- Create: `src/listing_evals/grounding.py`
- Test: `tests/unit/test_grounding.py`

**Interfaces:**
- Consumes: nothing.
- Produces (Task 3 imports these exact names from `listing_evals.grounding`):
  - `normalize_text(text: str) -> str`
  - `find_ungrounded_quotes(quotes: Sequence[str], listing: str) -> list[str]` — returns the subset of `quotes` (original, unnormalized) whose normalized form is not a substring of the normalized listing; `[]` means fully grounded.

- [ ] **Step 1: Write the failing tests**

`tests/unit/test_grounding.py`:

```python
"""Behavior tests for evidence grounding: does a claimed quote actually appear in the listing?"""

from listing_evals.grounding import find_ungrounded_quotes

LISTING = '''Acme Corp is hiring a Senior Data Engineer.
You will take ownership of our nightly ETL
pipeline - it currently fails "silently" and finance
reports arrive LATE. Tech: Python, dbt, Airflow.'''


def test_verbatim_quote_is_grounded():
    assert find_ungrounded_quotes(['it currently fails "silently"'], LISTING) == []


def test_fabricated_quote_is_reported():
    quotes = ["experience with Kubernetes required"]
    assert find_ungrounded_quotes(quotes, LISTING) == quotes


def test_quote_spanning_a_line_wrap_is_grounded():
    assert find_ungrounded_quotes(["ownership of our nightly ETL pipeline"], LISTING) == []


def test_prettified_curly_quotes_still_ground():
    # models often emit curly quotes even when the source is ASCII
    assert find_ungrounded_quotes(["fails “silently”"], LISTING) == []


def test_em_dash_matches_source_hyphen():
    assert find_ungrounded_quotes(["pipeline — it currently fails"], LISTING) == []


def test_case_difference_still_grounds():
    assert find_ungrounded_quotes(["reports arrive late."], LISTING) == []


def test_unicode_ligature_still_grounds():
    # NFKC folds the ﬁ ligature into "fi"
    assert find_ungrounded_quotes(["ﬁnance reports"], LISTING) == []


def test_partial_overlap_is_still_fabrication():
    quotes = ["nightly ETL pipeline that never fails"]
    assert find_ungrounded_quotes(quotes, LISTING) == quotes


def test_mixed_quotes_reports_only_the_fabricated_one():
    grounded = "Tech: Python, dbt, Airflow."
    fabricated = "must mentor junior engineers"
    assert find_ungrounded_quotes([grounded, fabricated], LISTING) == [fabricated]


def test_empty_quote_list_is_vacuously_grounded():
    assert find_ungrounded_quotes([], LISTING) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_grounding.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'listing_evals'`

- [ ] **Step 3: Implement**

`src/listing_evals/__init__.py`: empty file.

`src/listing_evals/grounding.py`:

```python
"""Evidence grounding: is a quote the model attributes to a listing actually in it?

Pure functions only — no promptfoo types, no IO.
"""

import re
import unicodedata
from collections.abc import Sequence

_PUNCTUATION_TRANSLATION = str.maketrans({
    "‘": "'",  # left single curly quote
    "’": "'",  # right single curly quote
    "“": '"',  # left double curly quote
    "”": '"',  # right double curly quote
    "–": "-",  # en dash
    "—": "-",  # em dash
    "−": "-",  # minus sign
})
_WHITESPACE_RUNS = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Collapse cosmetic differences (unicode forms, curly punctuation, whitespace, case)
    so that only real wording differences distinguish two strings."""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_PUNCTUATION_TRANSLATION)
    return _WHITESPACE_RUNS.sub(" ", text).casefold().strip()


def find_ungrounded_quotes(quotes: Sequence[str], listing: str) -> list[str]:
    """Return the quotes that do NOT appear verbatim in the listing, after normalization.

    An empty result means every quote is grounded. Returned quotes keep their
    original form so callers can name the offender.
    """
    normalized_listing = normalize_text(listing)
    return [quote for quote in quotes if normalize_text(quote) not in normalized_listing]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_grounding.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add src/listing_evals tests/unit && git commit -m "feat: evidence-grounding core (normalize + find_ungrounded_quotes)"
```

---

### Task 3: Grounding assertion adapter

**Files:**
- Create: `evals/extract-problems/asserts/grounding.py`

**Interfaces:**
- Consumes: `listing_evals.grounding.find_ungrounded_quotes(quotes, listing) -> list[str]` (Task 2).
- Produces: promptfoo python assertion entrypoint `get_assert(output, context)` returning a GradingResult dict (promptfoo auto-converts `pass_`/`named_scores`/`component_results` snake_case keys to camelCase). Task 4's config references this file as `file://asserts/grounding.py`.

- [ ] **Step 1: Write the adapter**

`evals/extract-problems/asserts/grounding.py`:

```python
"""Promptfoo assertion: every evidence quote must appear verbatim in the listing.

Thin adapter over listing_evals.grounding — parsing and marshaling only,
no logic worth unit-testing (the eval run itself exercises this file).
"""

import json
import sys
from pathlib import Path

REPO_SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(REPO_SRC))

from listing_evals.grounding import find_ungrounded_quotes  # noqa: E402


def _quote_label(quote: str, limit: int = 60) -> str:
    return quote if len(quote) <= limit else quote[: limit - 1] + "…"


def get_assert(output, context):
    try:
        data = output if isinstance(output, dict) else json.loads(output)
        problems = data["problems"]
    except (TypeError, ValueError, KeyError) as parse_error:
        return {
            "pass_": False,
            "score": 0.0,
            "reason": f"output is not contract JSON: {parse_error!r}",
        }

    listing = context["vars"]["listing"]
    component_results = []
    total_quotes = 0
    fabricated_quotes = 0

    for problem in problems:
        problem_id = problem.get("id", "?")
        quotes = problem.get("evidence", [])
        ungrounded = set(find_ungrounded_quotes(quotes, listing))
        for quote in quotes:
            total_quotes += 1
            is_grounded = quote not in ungrounded
            if not is_grounded:
                fabricated_quotes += 1
            component_results.append({
                "pass_": is_grounded,
                "score": 1.0 if is_grounded else 0.0,
                "reason": (
                    f"{problem_id}: "
                    f"{'grounded' if is_grounded else 'NOT IN LISTING'}"
                    f' — "{_quote_label(quote)}"'
                ),
            })

    if total_quotes == 0:
        return {"pass_": False, "score": 0.0, "reason": "no evidence quotes in output"}

    grounded_fraction = (total_quotes - fabricated_quotes) / total_quotes
    return {
        "pass_": fabricated_quotes == 0,
        "score": grounded_fraction,
        "reason": (
            "all evidence grounded"
            if fabricated_quotes == 0
            else f"{fabricated_quotes}/{total_quotes} evidence quotes not found in listing"
        ),
        "named_scores": {"evidence_grounding": grounded_fraction},
        "component_results": component_results,
    }
```

- [ ] **Step 2: Sanity-run the adapter once (throwaway, not a committed test)**

Run:

```bash
uv run python -c "
import sys; sys.path.insert(0, 'evals/extract-problems/asserts')
from grounding import get_assert
out = '{\"problems\": [{\"id\": \"P1\", \"problem\": \"x\", \"evidence\": [\"we ship nightly\", \"made-up quote\"], \"rationale\": \"r\"}]}'
result = get_assert(out, {'vars': {'listing': 'We ship nightly to prod.'}})
print(result['pass_'], result['score'], result['reason'])
assert result['pass_'] is False and result['score'] == 0.5
print('adapter OK')
"
```

Expected: `False 0.5 1/2 evidence quotes not found in listing` then `adapter OK`.

- [ ] **Step 3: Commit**

```bash
git add evals/extract-problems/asserts/grounding.py && git commit -m "feat: grounding assertion adapter for promptfoo"
```

---

### Task 4: Suite definition — provider, prompt, schema, generator, config

**Files:**
- Create: `shared/provider.yaml`
- Create: `evals/extract-problems/prompts/extract.json`
- Create: `evals/extract-problems/schema.json`
- Create: `evals/extract-problems/generate_tests.py`
- Create: `evals/extract-problems/promptfooconfig.yaml`

**Interfaces:**
- Consumes: `file://asserts/grounding.py` (Task 3).
- Produces: the runnable suite. Task 5 runs it. `generate_tests(config: dict | None) -> list[dict]` emits `{description, vars: {listing_id, listing}}` per listing file.

- [ ] **Step 1: Write shared/provider.yaml**

```yaml
id: 'openai:chat:{{env.PF_MODEL}}'
label: local-model
config:
  apiBaseUrl: '{{env.PF_BASE_URL}}'
  apiKey: '{{env.PF_API_KEY}}'
  temperature: 0
```

(Spec fallback if `{{env.PF_MODEL}}` fails to render inside `id` at validation time in Task 5: replace the `id:` line with the literal served model name, e.g. `id: 'openai:chat:qwen3-8b'`, and note the edit in the commit message. Everything else is unchanged.)

- [ ] **Step 2: Write evals/extract-problems/prompts/extract.json**

```json
[
  {
    "role": "system",
    "content": "You are an analyst helping a job applicant decode a job listing. A job listing is a disguised list of problems the company is trying to solve by hiring someone. Identify those problems.\n\nRules:\n- Every problem must be backed by evidence: one or more quotes copied VERBATIM from the listing. Never paraphrase inside evidence.\n- 3 to 7 problems is typical. Merge near-duplicates into one problem.\n- rationale: one sentence explaining why the evidence implies the problem.\n- Respond with JSON only. No markdown fences, no commentary. Use exactly this shape:\n{\"problems\": [{\"id\": \"P1\", \"problem\": \"...\", \"evidence\": [\"...\"], \"rationale\": \"...\"}]}"
  },
  {
    "role": "user",
    "content": "Job listing:\n\n{{listing}}"
  }
]
```

(Safe to inject raw listing text: promptfoo parses this file as JSON first, then Nunjucks-renders each string on the parsed object — quotes/newlines in `{{listing}}` cannot break the JSON.)

- [ ] **Step 3: Write evals/extract-problems/schema.json**

```json
{
  "type": "object",
  "properties": {
    "problems": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "string", "pattern": "^P[0-9]+$" },
          "problem": { "type": "string" },
          "evidence": { "type": "array", "minItems": 1, "items": { "type": "string" } },
          "rationale": { "type": "string" }
        },
        "required": ["id", "problem", "evidence", "rationale"],
        "additionalProperties": false
      }
    }
  },
  "required": ["problems"],
  "additionalProperties": false
}
```

- [ ] **Step 4: Write evals/extract-problems/generate_tests.py**

```python
"""One promptfoo test per job-listing file. Deliberate IO glue — exercised by
every eval run, so it carries no unit tests (see spec §8)."""

from pathlib import Path


def generate_tests(config=None):
    config = config or {}
    job_listings_dir = (
        Path(__file__).resolve().parent / config.get("job_listings_dir", "../../job_listings")
    ).resolve()
    listing_paths = sorted(job_listings_dir.glob("*.txt"))
    if not listing_paths:
        raise FileNotFoundError(f"no *.txt job listings found in {job_listings_dir}")
    return [
        {
            "description": path.stem,
            "vars": {
                "listing_id": path.stem,
                "listing": path.read_text(encoding="utf-8"),
            },
        }
        for path in listing_paths
    ]
```

- [ ] **Step 5: Write evals/extract-problems/promptfooconfig.yaml**

```yaml
# yaml-language-server: $schema=https://promptfoo.dev/config-schema.json
description: 'Phase 1: extract evidence-grounded hiring problems from job listings'

prompts:
  - file://prompts/extract.json

providers:
  - file://../../shared/provider.yaml

defaultTest:
  assert:
    - type: is-json
      value: file://schema.json
    - type: python
      value: file://asserts/grounding.py
      metric: evidence_grounding

tests:
  - path: file://generate_tests.py:generate_tests
    config:
      job_listings_dir: ../../job_listings
```

- [ ] **Step 6: Verify wiring executes (corpus is intentionally still missing)**

Run:

```bash
PF_MODEL=placeholder PF_BASE_URL=http://localhost:9/v1 PF_API_KEY=dummy \
  uvx promptfoo@0.1.4 eval -c evals/extract-problems/promptfooconfig.yaml --no-cache --no-share 2>&1 | tail -20
```

Expected: failure whose message includes `no *.txt job listings found in` and the resolved `job_listings` path — proving config, provider file, and generator all load and execute. Any OTHER error (YAML parse, unknown provider, python import) must be fixed before committing.

- [ ] **Step 7: Commit**

```bash
git add shared evals/extract-problems && git commit -m "feat: extract-problems suite (provider, prompt v0, schema, test generator)"
```

---

### Task 5: Corpus check-in + live smoke on one listing

**Files:**
- Create: `job_listings/*.txt` (user-provided real listings)

**Interfaces:**
- Consumes: the full suite (Task 4). Requires USER INPUT: real listing files, a running local server, and real values for `PF_MODEL`/`PF_BASE_URL`.
- Produces: committed corpus; verified end-to-end pipeline.

- [ ] **Step 1: USER CHECKPOINT — collect the corpus**

Pause and ask the user to place their real job listings in `job_listings/`, one listing per `.txt` file, kebab-case intent-revealing names (e.g. `acme-senior-data-engineer.txt`). Target 10+ now (30+ eventually, for error analysis). Also ask them to start their local server and provide the served model name and base URL.

- [ ] **Step 2: Validate the config with real env values**

Run (substitute real values):

```bash
export PF_MODEL=<served-model-name> PF_BASE_URL=http://localhost:8000/v1 PF_API_KEY=dummy
uvx promptfoo@0.1.4 validate config -c evals/extract-problems/promptfooconfig.yaml
```

Expected: config valid. If the provider `id` fails to render `{{env.PF_MODEL}}`, apply the fallback from Task 4 Step 1 (literal model name in `shared/provider.yaml`).

- [ ] **Step 3: Smoke-eval exactly one listing**

Run (use a real listing's file stem as the pattern):

```bash
uvx promptfoo@0.1.4 eval -c evals/extract-problems/promptfooconfig.yaml \
  --filter-pattern '<one-listing-stem>' --no-cache --no-share -o /tmp/extract-smoke.json
```

Inspect `/tmp/extract-smoke.json`: `results.stats` has 1 test and 0 errors; `response.output` contains model text; both assertions produced verdicts with reasons (`gradingResult`). **Assertions MAY legitimately fail — that is v0 data, not a bug.** Only pipeline errors (connection refused, empty output, python exceptions in the assertion) block this step.

- [ ] **Step 4: Commit the corpus**

```bash
git add job_listings && git commit -m "data: real job-listing corpus (phase 1)"
```

---

### Task 6: Full v0 baseline run

**Files:**
- Create: `runs/extract-problems-v0.json`

**Interfaces:**
- Consumes: everything above; the same env vars and running server as Task 5.
- Produces: the committed v0 baseline that error analysis (next, outside this plan) reads.

- [ ] **Step 1: Run the full corpus**

```bash
uvx promptfoo@0.1.4 eval -c evals/extract-problems/promptfooconfig.yaml \
  --no-cache --no-share -o runs/extract-problems-v0.json
```

Expected: one test per listing file; exit may be nonzero because assertions fail — that is expected v0 behavior.

- [ ] **Step 2: Sanity-check the snapshot**

Run:

```bash
uv run python -c "
import json
stats = json.load(open('runs/extract-problems-v0.json'))['results']['stats']
print(stats)
assert stats.get('errors', 0) == 0, 'pipeline errors present - investigate before committing'
"
```

Expected: printed stats; zero errors (failures are fine, errors are not). If errors exist, diagnose (server logs, `response.error` entries) and re-run; do not commit a snapshot containing pipeline errors.

- [ ] **Step 3: Commit the baseline**

```bash
git add runs/extract-problems-v0.json && git commit -m "eval: phase-1 v0 baseline over full corpus"
```

---

### Task 7: README rewrite

**Files:**
- Modify: `README.md` (full replacement below)

**Interfaces:**
- Consumes: everything above (documents it).
- Produces: the portfolio-facing front page, updated again after each error-analysis iteration.

- [ ] **Step 1: Replace README.md with**

````markdown
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
wrapper shells out to it), and any local OpenAI-compatible server (vLLM or
llama.cpp).

```bash
# 1. serve a model, e.g.:
#    vllm serve <model> --served-model-name my-model            (:8000)
#    llama-server -m model.gguf                                  (:8080)

# 2. point the eval at it
export PF_MODEL=my-model
export PF_BASE_URL=http://localhost:8000/v1
export PF_API_KEY=dummy

# 3. run phase 1 over the corpus
uvx promptfoo@0.1.4 eval -c evals/extract-problems/promptfooconfig.yaml --no-cache --no-share

# 4. read traces in the browser
uvx promptfoo@0.1.4 view

# unit tests (core logic only)
uv sync && uv run pytest
```

## Layout

| Path | What it is |
|---|---|
| `job_listings/` | Real job listings, one `.txt` per listing — the corpus |
| `evals/extract-problems/` | Phase 1 suite: prompt (the agent), schema, grounding assertion |
| `src/listing_evals/` | Pure domain logic (no promptfoo, no IO) behind every assertion |
| `tests/unit/` | pytest, behavior-level, core logic only — never harness glue |
| `runs/` | Committed eval snapshots per iteration (`extract-problems-v0.json`, …) |
| `docs/error-analysis/` | Failure taxonomy and labels, built by reading traces |
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

## Iterations

| Version | Change | Result |
|---|---|---|
| v0 | baseline prompt, contract assertions | see `runs/extract-problems-v0.json` |

*Status: phase-1 v0 baseline complete; error analysis round 1 is next.*
````

- [ ] **Step 2: Commit**

```bash
git add README.md && git commit -m "docs: portfolio README for phase 1"
```

---

## After this plan

Error analysis round 1 (interactive, with the user, per spec §7 — not a coding
task): read every trace in `uvx promptfoo@0.1.4 view`, pass/fail + first-thing-wrong
notes, taxonomy, failure rates into `docs/error-analysis/round-1.md`. Phase 2
(`propose-project`) gets its own plan after phase 1 completes an iteration cycle.
