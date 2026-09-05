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
2. **Propose a representative project** *(next phase)*. Suggest one small,
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
- Failures like that aren't patched away quietly. Every run is committed,
  each prompt revision is measured against the last, and new checks are
  only added when a real failure shows the need (see the results table
  below — the failure is part of the record).

Inspired by Hamel Husain's
["It's hard to eval is a product smell"](https://hamelhusain.substack.com/p/its-hard-to-eval-is-a-product-smell):
if you design the output so a human could verify it, a few lines of code
usually can too.

## Try it

Requirements: [uv](https://docs.astral.sh/uv/), Node.js, and an OpenAI API
key (or any OpenAI-compatible local server — vLLM, llama.cpp).

```bash
# 1. copy the example env and set your API key
cp .env.example .env

#    ...or serve locally and point evals/providers.yaml at it by adding
#    `apiBaseUrl: http://localhost:8000/v1` (vLLM) / :8080/v1 (llama.cpp)
#    under config: — model and endpoint live in that file, not in env vars.

# 2. run phase 1 over the corpus of job listings
uvx promptfoo eval -c evals/extract-problems/promptfooconfig.yaml --no-cache

# 3. read every analysis in the browser
uvx promptfoo view
```

To analyze your own target listings, drop them into `job_listings/` as
`.txt` files — one listing per file — and rerun. Every file in that folder
is picked up automatically.

## Results so far

| Version | Change | Result |
|---|---|---|
| v0 | baseline prompt, contract checks (valid structure + verbatim evidence) | 9/10 listings pass on gpt-5.6-luna; 1 caught fabrication (paraphrased quote) — `runs/extract-problems-v0.json` |

*Status: baseline complete on a corpus of 10 real listings; failure-mode
analysis of the traces is next, then measured prompt iterations, then the
project-proposal phase.*
