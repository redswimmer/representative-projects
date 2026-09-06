"""Run the two agents over job listings:
extract the problems a listing encodes, then propose ranked representative
projects aimed at them. Results land in output/<listing>/.
"""

import argparse
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stems", nargs="*", help="listing stems to run (default: all)")
    parser.add_argument("--projects", type=int, default=3,
                        help="how many ranked projects to propose per listing (default: 3)")
    args = parser.parse_args()

    listing_paths = sorted((REPO / "job_listings").glob("*.txt"))
    if args.stems:
        listing_paths = [p for p in listing_paths if p.stem in set(args.stems)]
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
            "num_projects": str(args.projects),
        }))
        (out_dir / "projects.json").write_text(proposal + "\n", encoding="utf-8")
        print(f"   projects → output/{listing_id}/projects.json")

    print("\nDone. Quality checks live in the eval suites — see README.")


if __name__ == "__main__":
    main()
