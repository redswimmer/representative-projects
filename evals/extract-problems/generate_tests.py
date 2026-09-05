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
