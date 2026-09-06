"""One promptfoo test per frozen fixture: a listing's verified problems and its
proposed projects, captured together from one passing phase-2 run so the pair
stays coherent. Deliberate IO glue — exercised by every eval run, so it carries
no unit tests (see spec §8)."""

import json
from pathlib import Path


def generate_tests(config=None):
    config = config or {}
    here = Path(__file__).resolve().parent
    fixtures_dir = (here / config.get("fixtures_dir", "fixtures")).resolve()
    fixture_paths = sorted(fixtures_dir.glob("*.json"))
    if not fixture_paths:
        raise FileNotFoundError(f"no *.json fixtures found in {fixtures_dir}")
    tests = []
    for path in fixture_paths:
        fixture = json.loads(path.read_text(encoding="utf-8"))
        company = fixture.get("company")
        if not company:
            # company: null means the listing never names its company — research
            # scoped to company-published sources is impossible by definition, so
            # such a listing has no phase 3. A fixture like that is a curation
            # error; fail loud rather than skip it silently or fabricate a name.
            raise ValueError(f"{path.name}: fixture has no company name — this listing has no phase 3")
        tests.append(
            {
                "description": path.stem,
                "vars": {
                    "listing_id": path.stem,
                    "company": company,
                    "problems": json.dumps({"problems": fixture["problems"]}, indent=2),
                    "projects": json.dumps({"projects": fixture["projects"]}, indent=2),
                },
            }
        )
    return tests
