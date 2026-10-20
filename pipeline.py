"""Run the three agents over job listings:
extract the problems a listing encodes, propose ranked representative
projects aimed at them, then ground each project in what the company itself
has published. Results land in output/<listing>/.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
EVALS = REPO / "evals"
EXTRACT_PROMPT = EVALS / "extract-problems" / "prompts" / "extract.txt"
EXTRACT_SCHEMA = EVALS / "extract-problems" / "schema.json"
PROPOSE_PROMPT = EVALS / "propose-project" / "prompts" / "propose.txt"
PROPOSE_SCHEMA = EVALS / "propose-project" / "schema.json"
RESEARCH_PROMPT = EVALS / "research-project" / "prompts" / "research.txt"
RESEARCH_SCHEMA = EVALS / "research-project" / "schema.json"
RESEARCH_TOOLS = ["WebSearch", "WebFetch"]  # mirrors the eval's custom_allowed_tools
OUTPUT_DIR = REPO / "output"

_SLOT = re.compile(r"\{\{(\w+)\}\}")


def fill_prompt(template: str, variables: dict) -> str:
    """Fill {{name}} slots — the same slot syntax the eval prompts use.
    A slot without a value is an error: a silently unfilled slot once sent the
    model a literal "{{schema}}" for weeks."""
    missing = set(_SLOT.findall(template)) - variables.keys()
    if missing:
        raise KeyError(f"prompt slots without a value: {sorted(missing)}")
    for name, value in variables.items():
        template = template.replace("{{" + name + "}}", value)
    return template


# --- runner glue: exercised by every pipeline run, no unit tests (spec §8) ---


def run_agent(prompt: str, allowed_tools: list[str] | None = None) -> str:
    command = ["claude", "-p", prompt]
    if allowed_tools:
        command += ["--allowedTools", *allowed_tools]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        sys.exit(f"claude call failed:\n{result.stderr.strip()}")
    return result.stdout.strip()


def load_schema(path: Path) -> str:
    """Render schema.json the way the evals inject it (JSON.stringify(schema, null, 2))."""
    return json.dumps(json.loads(path.read_text(encoding="utf-8")), indent=2, ensure_ascii=False)


def parse_output(text: str, what: str) -> dict:
    try:
        return json.loads(text)
    except ValueError as error:
        sys.exit(f"{what} is not JSON ({error}); the evals decode against the schema, the pipeline doesn't")


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
    research_template = RESEARCH_PROMPT.read_text(encoding="utf-8")
    extract_schema = load_schema(EXTRACT_SCHEMA)
    propose_schema = load_schema(PROPOSE_SCHEMA)
    research_schema = load_schema(RESEARCH_SCHEMA)

    for listing_path in listing_paths:
        listing_id = listing_path.stem
        listing = listing_path.read_text(encoding="utf-8")
        out_dir = OUTPUT_DIR / listing_id
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"── {listing_id}")

        problems = run_agent(fill_prompt(extract_template, {
            "listing": listing,
            "schema": extract_schema,
        }))
        (out_dir / "problems.json").write_text(problems + "\n", encoding="utf-8")
        print(f"   problems → output/{listing_id}/problems.json")

        proposal = run_agent(fill_prompt(propose_template, {
            "listing_id": listing_id,
            "listing": listing,
            "problems": problems,
            "num_projects": str(args.projects),
            "schema": propose_schema,
        }))
        (out_dir / "projects.json").write_text(proposal + "\n", encoding="utf-8")
        print(f"   projects → output/{listing_id}/projects.json")

        company = parse_output(problems, f"{listing_id} problems.json")["company"]
        if not company:
            print("   listing never names its company — no research")
            continue
        citations = run_agent(fill_prompt(research_template, {
            "listing_id": listing_id,
            "company": company,
            "problems": problems,
            "projects": json.dumps(
                {"projects": parse_output(proposal, f"{listing_id} projects.json")["projects"]},
                indent=2, ensure_ascii=False,
            ),
            "schema": research_schema,
        }), allowed_tools=RESEARCH_TOOLS)
        (out_dir / "citations.json").write_text(citations + "\n", encoding="utf-8")
        print(f"   citations → output/{listing_id}/citations.json")

    print("\nDone. Quality checks live in the eval suites — see README.")


if __name__ == "__main__":
    main()
