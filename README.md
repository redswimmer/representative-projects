# Representative Projects — decode a job listing, then build the thing that gets you hired

A job listing is a disguised list of problems. A company doesn't hire a
"Senior Data Engineer" — it hires someone to fix the nightly pipeline that
fails silently, or to bring order to metrics nobody trusts. Applicants who
can name those problems, and show up with a small working project aimed
straight at them, stop looking like résumés and start looking like solutions.

This project uses an LLM to do the decoding — and holds it to a standard of
evidence:

1. **Extract the problems.** Read a listing and identify what the company is
   actually trying to solve, where every claim is backed by *verbatim quotes
   from the listing itself*. If a quote isn't really in the listing, the
   analysis fails. You can Ctrl-F every piece of evidence.
2. **Propose a representative project.** Suggest one small,
   buildable project — what it demonstrates, how each part maps back to a
   named problem, and a roadmap. Framing and direction only, **never code**:
   the applicant still does the work. That's the point — this is AI helping
   you decide *what to build and why it matters to them*, not AI building it
   for you.

Both sides win: the applicant targets their effort instead of guessing, and
the company gets to judge real, relevant work.

## Why the evaluation is the interesting part

Anyone can prompt a model to "find the problems in this job ad." The hard
question is whether you can *trust* the answer — so this repo is built
around measuring that, cheaply and reproducibly:

- Outputs are structured so they can be checked by code, not vibes: every
  extracted problem carries its evidence quotes, and a deterministic check
  verifies each quote actually appears in the listing. No LLM judges, no
  API costs to grade — just string matching that catches fabrication cold.
- It works. On the first baseline run, the checker caught the model quoting
  "*Our* mission is to create reliable, interpretable, and steerable AI
  systems" — the listing says "*Anthropic's* mission…". A confident,
  plausible, fabricated quote, flagged automatically with the exact string.
- Failures like that aren't patched away quietly: each prompt revision is
  measured against the last, and new checks are only added when a real
  failure shows the need.

Inspired by Hamel Husain's
["It's hard to eval is a product smell"](https://hamelhusain.substack.com/p/its-hard-to-eval-is-a-product-smell):
if you design the output so a human could verify it, a few lines of code
usually can too.

## Try it

Requirements: [uv](https://docs.astral.sh/uv/), Node.js, and
[Claude Code](https://claude.com/claude-code) installed and logged in.
Both agents run on your Claude subscription — no API keys, no per-token
charges.

**Use the agents** — run the pipeline over your listings, read the results:

```bash
uv run pipeline.py                        # every listing in job_listings/
uv run pipeline.py performance_engineer   # or just one
```

Each listing gets `output/<listing>/problems.json` (the decoded problems,
with their evidence quotes) and `output/<listing>/project.json` (the
proposed project). To analyze your own target listings, drop them into
`job_listings/` as `.txt` files — one listing per file — and rerun.

**Evaluate the agents** — the point of this repo — run each agent's graded
suite and read every trace:

```bash
# one-time: install the agent SDK the eval harness runs on
npm install

# each agent, graded over its committed corpus
uvx promptfoo eval -c evals/extract-problems/promptfooconfig.yaml --no-cache
uvx promptfoo eval -c evals/propose-project/promptfooconfig.yaml --no-cache

# read every analysis in the browser
uvx promptfoo view
```

Phase 1's eval corpus is `job_listings/`; phase 2's is
`evals/propose-project/fixtures/` — verified phase-1 outputs, curated and
committed so the proposal agent is always graded against stable inputs.
When the evals catch a problem, the fix goes into the agents' prompt
files — which the pipeline shares, so using and evaluating never drift
apart.
