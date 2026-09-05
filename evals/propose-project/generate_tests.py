"""One promptfoo test per verified phase-1 fixture, paired with its listing.
Deliberate IO glue — exercised by every eval run, so it carries no unit tests
(see spec §8)."""

from pathlib import Path


def generate_tests(config=None):
    config = config or {}
    here = Path(__file__).resolve().parent
    fixtures_dir = (here / config.get("fixtures_dir", "fixtures")).resolve()
    job_listings_dir = (here / config.get("job_listings_dir", "../../job_listings")).resolve()
    fixture_paths = sorted(fixtures_dir.glob("*.json"))
    if not fixture_paths:
        raise FileNotFoundError(f"no *.json fixtures found in {fixtures_dir}")
    return [
        {
            "description": path.stem,
            "vars": {
                "listing_id": path.stem,
                "listing": (job_listings_dir / f"{path.stem}.txt").read_text(encoding="utf-8"),
                "problems": path.read_text(encoding="utf-8"),
            },
        }
        for path in fixture_paths
    ]
