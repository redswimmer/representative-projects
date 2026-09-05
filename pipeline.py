"""Run the two agents over job listings, the way an applicant would:
extract the problems a listing encodes, then propose one representative
project aimed at them. Results land in output/<listing>/.

This runner has no quality machinery on purpose — it just runs the agents
(one Claude Code call each, using your existing login). Quality control
lives in the eval suites under evals/; issues found there are fixed in the
agents' prompt files, which this runner shares.
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
EXTRACT_PROMPT = REPO / "evals" / "extract-problems" / "prompts" / "extract.txt"
PROPOSE_PROMPT = REPO / "evals" / "propose-project" / "prompts" / "propose.txt"
OUTPUT_DIR = REPO / "output"


def fill_prompt(template: str, variables: dict) -> str:
    """Fill {{name}} slots — the same slot syntax the eval prompts use.
    Unknown slots are left intact so a template/vars mismatch stays visible."""
    for name, value in variables.items():
        template = template.replace("{{" + name + "}}", value)
    return template


# --- runner glue: exercised by every pipeline run, no unit tests (spec §8) ---


def run_agent(prompt: str) -> str:
    result = subprocess.run(
        ["claude", "-p", prompt], capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        sys.exit(f"claude call failed:\n{result.stderr.strip()}")
    return result.stdout.strip()


def main():
    requested_stems = set(sys.argv[1:])
    listing_paths = sorted((REPO / "job_listings").glob("*.txt"))
    if requested_stems:
        listing_paths = [p for p in listing_paths if p.stem in requested_stems]
    if not listing_paths:
        sys.exit("no matching listings in job_listings/")

    extract_template = EXTRACT_PROMPT.read_text(encoding="utf-8")
    propose_template = PROPOSE_PROMPT.read_text(encoding="utf-8")

    for listing_path in listing_paths:
        listing_id = listing_path.stem
        listing = listing_path.read_text(encoding="utf-8")
        out_dir = OUTPUT_DIR / listing_id
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"── {listing_id}")

        problems = run_agent(fill_prompt(extract_template, {"listing": listing}))
        (out_dir / "problems.json").write_text(problems + "\n", encoding="utf-8")
        print(f"   problems → output/{listing_id}/problems.json")

        proposal = run_agent(fill_prompt(propose_template, {
            "listing_id": listing_id,
            "listing": listing,
            "problems": problems,
        }))
        (out_dir / "project.json").write_text(proposal + "\n", encoding="utf-8")
        print(f"   project  → output/{listing_id}/project.json")

    print("\nDone. Quality checks live in the eval suites — see README.")


if __name__ == "__main__":
    main()
