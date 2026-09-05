# Representative Projects — Eval Design Spec

**Date:** 2026-09-05
**Status:** Approved pending user review
**Repo:** `representative-projects` (portfolio project)

## 1. Purpose & Thesis

Job listings encode the problems a company is hiring to solve. An applicant who
surfaces those problems (axial coding with evidence) and builds a small
*representative project* targeting them presents far stronger than one who
merely claims ability. This repo evaluates an LLM pipeline that automates the
analysis — never the applicant's work itself: it outputs problems, framing, and
a roadmap, **never code**, so the applicant still has to build the project.

**The deliverable of this repo is the evaluation, not the pipeline.** It
demonstrates, as a portfolio piece: error-analysis-driven eval construction,
judge-minimal assertion design, and eval-driven prompt iteration — all in
promptfoo, all runnable against a $0 local endpoint.

Design north star (Hamel Husain, "It's hard to eval is a product smell"):
outputs are structured for verifiability from day one. Evidence quotes,
IDs, and referential links exist *so that* correctness is checkable by code.

## 2. Decisions Already Made

| Decision | Choice |
|---|---|
| Agent form | **A: Prompt-as-agent.** Pure promptfoo YAML; no agent code, no tools, no agent SDK. The prompt file is the agent. |
| Chaining | Two independent suites. Phase 2 consumes **frozen, hand-verified fixtures**, never live phase-1 output. |
| Corpus | User's **real job listings**, committed to the repo as `job_listings/*.txt`. |
| Runtime | Any OpenAI-compatible local server (vLLM or llama.cpp) via one shared provider file; endpoint is an env var. |
| Judges | Deterministic assertions first. LLM judge only for failure modes that irreducibly require interpretation, run on the same local endpoint, and calibrated against hand labels before being trusted. |
| Eval order | Contract assertions at v0; **all failure-mode assertions come after error analysis**, never speculatively. |

Explicitly rejected: OpenAI Agents SDK integration (JS-SDK-native in promptfoo;
Python needs a wrapper; adds machinery and nondeterminism, subtracts
auditability for a linear two-step pipeline), tool-loop agent (tools would only
re-implement file loading promptfoo already does deterministically).

## 3. Repository Layout

```
job_listings/                      # real listings, one .txt per listing
shared/
  provider.yaml                    # single provider definition (see §6)
evals/
  extract-problems/                # PHASE 1
    promptfooconfig.yaml
    prompts/extract.json           # chat-format messages (system + user)
    schema.json                    # phase-1 output contract
    generate_tests.py              # globs job_listings dir -> one test per file
    asserts/grounding.py           # matching logic + promptfoo adapter, one file (see §8)
  propose-project/                 # PHASE 2 (built after phase 1 iterates)
    promptfooconfig.yaml
    prompts/propose.json
    schema.json
    fixtures/*.json                # frozen, hand-verified phase-1 outputs
    asserts/integrity.py           # integrity logic + promptfoo adapter, one file
tests/
  unit/                            # pytest; tests assertion logic only (see §8)
docs/
  error-analysis/                  # round-N notes, taxonomy, labels
  superpowers/specs/               # this spec
runs/                              # committed eval result snapshots (v0.json, ...)
README.md                          # thesis, methodology, iteration table, repro
```

Scaffold files `main.py`, `context.py`, and the root helpdesk
`promptfooconfig.yaml` are deleted. Runtime eval code is stdlib-only;
`pytest` is the sole dev dependency (see §8).

Data flow is one-directional:
`job_listings/ → phase 1 → human curation → fixtures/ → phase 2`.

## 4. Phase 1 — `extract-problems`

**Task:** given one job listing, identify the problems the company is hiring to
solve, each grounded in the listing's own words.

**Prompt:** `prompts/extract.json`, chat message array (system + user with
`{{listing}}`). Instructs: 3–7 problems typical (guidance, not schema-enforced
in v0), evidence must be verbatim quotes, output JSON only, no markdown fences.

**Output contract** (`schema.json`):

```json
{
  "type": "object",
  "properties": {
    "problems": {
      "type": "array", "minItems": 1,
      "items": {
        "type": "object",
        "properties": {
          "id":        {"type": "string", "pattern": "^P[0-9]+$"},
          "problem":   {"type": "string"},
          "evidence":  {"type": "array", "minItems": 1, "items": {"type": "string"}},
          "rationale": {"type": "string"}
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

No problem-category taxonomy. Categories emerge from error analysis if at all;
pre-baking one is the anti-pattern the methodology exists to avoid.
`rationale` is the auditable stand-in for chain-of-thought: per-claim
inspectable reasoning. Free-form CoT is never graded.

**Test generation:** `generate_tests.py:generate_tests(config)` globs
`config["job_listings_dir"]` (default `../../job_listings`), returns one test
per file: `vars: {listing_id, listing}`, `description` = filename. Deliberate
IO glue — exercised by every eval run, never unit-tested (§8). Referenced as:

```yaml
tests:
  - path: file://generate_tests.py:generate_tests
    config:
      job_listings_dir: ../../job_listings
```

**Contract assertions (v0, in `defaultTest`)** — these ARE the output
contract, not speculative failure evals:

1. `is-json` against `schema.json`.
2. `python: file://asserts/grounding.py` — matching logic + adapter in one
   file: every `evidence` string must be a
   substring of `context["vars"]["listing"]` after normalization on both
   sides: Unicode NFKC, curly quotes/dashes → ASCII, whitespace runs → single
   space, casefold. Returns a GradingResult with `named_scores`
   (`evidence_grounding` = grounded/total), pass iff all grounded, and
   per-quote `component_results` naming any fabricated quote — so the viewer
   shows exactly which quote failed during error analysis.

Nothing else at v0. `options.transform: JSON.parse(output)` is applied
per-suite once outputs are reliably parseable; until then grounding.py parses
defensively and returns a failed GradingResult with a reason (never raises).

## 5. Phase 2 — `propose-project`

Built only after phase 1 has been through ≥1 full error-analysis/iteration
cycle. Same methodology, new contract.

**Task:** given a listing + its verified problems (fixture), propose ONE
representative project: what to build, how each part demonstrates capability
against specific problems, and a work roadmap. Framing and justification only —
**no code, no snippets**.

**Inputs:** `fixtures/*.json` — frozen phase-1 outputs, hand-verified during
curation. A small generator (or plain YAML tests) pairs each fixture with its
listing text.

**Output contract:** `{"project": {title, summary, components[], roadmap[]}}`
where each component has `id` (`^C[0-9]+$`), `name`, `description`,
`addresses` (array of problem IDs), `justification`; each roadmap milestone
lists component IDs.

**Contract assertions (v0):**

1. `is-json` against schema.
2. `asserts/integrity.py` — integrity logic + adapter in one
   file: every `addresses` ID exists in the
   fixture's problems; every fixture problem is addressed by ≥1 component;
   every roadmap component ID exists. Pure set arithmetic, with
   `named_scores` (`problem_coverage`, `ref_integrity`).
3. No-code check: regex — no code fences, no obvious code lines. Start
   conservative (fences only) to avoid false positives; tighten from observed
   failures.

## 6. Provider & Reproducibility

`shared/provider.yaml` (referenced from both suites as
`providers: [file://../../shared/provider.yaml]`):

```yaml
id: 'openai:chat:{{env.PF_MODEL}}'
label: local-model
config:
  apiBaseUrl: '{{env.PF_BASE_URL}}'   # vLLM: http://localhost:8000/v1
                                       # llama.cpp: http://localhost:8080/v1
  apiKey: '{{env.PF_API_KEY}}'        # dummy value fine for local servers
  temperature: 0
```

(If env templating in the `id` field proves unsupported at implementation
time, fall back to a literal served-model-name in this one file — still a
single-file edit.)

- promptfoo runs via `uvx promptfoo@0.1.4` — the official PyPI wrapper
  (delivers CLI 0.122.2 at design time; still requires Node.js at runtime).
  The pin is recorded in README and used in all commands.
- Dev runs use `--no-cache --no-share`; snapshots via `-o runs/<tag>.json`.
- `temperature: 0` for reproducibility (noted: not bit-exact across servers).
- **Guided decoding / `response_format` json_schema is OFF at v0.** Malformed
  output is a real failure mode error analysis must observe. Turning it on is
  a *documented iteration*, expressed as a second labeled prompt variant with
  prompt-level `config.response_format` (per `config-structured-outputs`
  example) so v0 vs v1 render side-by-side in one eval run. Server support
  (vLLM guided decoding / llama.cpp json_schema) verified at that iteration.

Conventions throughout (from promptfoo `examples/AGENTS.md`): schema header
line, field order `description, env, prompts, providers, defaultTest,
scenarios, tests`, quoted `'{{env.VAR}}'`, chat prompts as JSON files.

## 7. Methodology (the portfolio narrative)

Per phase:

1. **v0**: prompt + contract assertions. Smoke on 2–3 listings, then full
   corpus run → `runs/<phase>-v0.json` (committed).
2. **Error analysis round 1** (`docs/error-analysis/round-1.md`): the user
   reads every trace in `promptfoo view` — pass/fail + one-line "first thing
   that went wrong" per failure. After ~30–50, group notes into a 5–10
   category failure taxonomy (open → axial coding). Label all traces against
   the taxonomy; compute failure rates. Committed artifacts: notes, taxonomy
   with definitions, labels table, rates.
3. **Fix-first**: failures caused by prompt gaps get prompt fixes, not
   evaluators. Only persistent, frequent, or high-impact failure modes earn
   assertions.
4. **Assertions from observed failures**: deterministic wherever possible
   (regex/set/parse checks; each carries a `metric:` name for dashboards). An
   LLM judge only where interpretation is irreducible — narrow rubric, local
   endpoint as grader, calibrated against the user's labels (TPR/TNR) before
   its verdicts count.
5. **Iterate**: each prompt revision = new labeled variant + full run
   committed to `runs/`. README iteration table: what failed → what changed →
   metric delta.
6. Repeat 1–5 for phase 2.

**Optional, deferred (build only if wanted after both phases stabilize):**
- `evals/e2e/` suite chaining phase 1 → phase 2 natively via
  `options.storeOutputAs` (zero code; verify sequential execution semantics
  when built).
- Tool-loop agent variant (approach B) if the portfolio story ever needs
  tool-use evals.
- Gold-label recall/precision suite over a hand-labeled listing subset
  (f-score pattern) if error analysis shows coverage failures matter.

## 8. Code Quality & Testing

Guiding references: Clean Code (intent-revealing names) and cosmicpython
chapters 3 ("On Coupling and Abstractions") and 5 ("TDD in High Gear and Low
Gear").

**Names convey intent.** Modules, functions, and variables are named for their
domain meaning (`find_ungrounded_quotes`, `job_listings_dir`,
`unaddressed_problems`), never for their mechanics.

**Core/adapter separation (ch. 3) — a boundary inside one file.** (Amended
2026-09-05: an earlier revision put the logic in a `src/listing_evals/`
package; with a single consumer per module and nothing actually shared, that
was collapsed — files that change together live together.) Each suite's
`asserts/*.py` is layered: pure functions on top (plain data in, plain data
out; no promptfoo types, no IO) and the `get_assert` GradingResult adapter at
the bottom. `tests/unit/conftest.py` puts the asserts directory on `sys.path`
so tests import the same file promptfoo executes. Extract a shared package
only if two suites ever genuinely share logic.

**High gear / low gear (ch. 5).** Unit tests live in `tests/unit/` (pytest)
and target the pure functions plus the adapter's *contract* (malformed model
output returns a failed GradingResult, never raises — see §9): normalization
edge cases (curly quotes, whitespace, unicode), grounding semantics (verbatim
vs. fabricated vs. partially-overlapping quotes), integrity set logic
(dangling refs, unaddressed problems), graceful-failure shapes. What is
deliberately NOT unit-tested: YAML configs, the test generator, GradingResult
field marshaling — that glue is exercised edge-to-edge by every eval run, and
tests coupled to it would be the brittle kind that punish refactoring without
catching real defects.

**Tooling.** `uv run pytest` runs the suite. `pyproject.toml` gains:

```toml
[dependency-groups]
dev = ["pytest"]

[tool.pytest.ini_options]
testpaths = ["tests/unit"]
```

Runtime eval code remains stdlib-only.

## 9. Error Handling

- Server down / provider error → surfaces as promptfoo ERROR (distinct from
  FAIL); README notes the distinction.
- Unparseable output → `is-json` fails with reason; python assertions parse
  defensively and return failed GradingResults, never raise.
- Assertion bugs: the core functions behind every assertion are covered by
  `tests/unit/` (§8) — the checkers themselves are verified before their
  verdicts are trusted.

## 10. Success Criteria

1. `git clone` → start any OpenAI-compatible local server → export 3 env vars
   → `uvx promptfoo@0.1.4 eval -c evals/extract-problems/promptfooconfig.yaml`
   works, and `uv run pytest` passes.
2. Every assertion in the final repo traces to a documented failure mode in
   `docs/error-analysis/`, or to the output contract. Zero speculative
   assertions.
3. ≥1 full documented iteration per phase with before/after committed runs.
4. LLM-judge count: 0 unless a failure mode demonstrably requires one; if
   present, its calibration numbers are committed.
5. Unit tests cover every core function behind an assertion, at the behavior
   level; no test imports promptfoo or touches harness glue.
6. README tells the full story: thesis → contract → error analysis → evals →
   iterations, with the axial-coding symmetry (method applied to listings AND
   to traces) stated explicitly.

## 11. Out of Scope

Agent frameworks/SDKs, RAG, multi-turn conversation, cloud providers or paid
judges, CI gating (may be added later; trivial with `runs/` snapshots),
resume/cover-letter generation, scraping infrastructure, web UI beyond
`promptfoo view`.
