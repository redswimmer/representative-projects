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


def _contract_failure(reason: str) -> dict:
    return {"pass_": False, "score": 0.0, "reason": reason}


def get_assert(output, context):
    try:
        data = output if isinstance(output, dict) else json.loads(output)
        problems = data["problems"]
    except (TypeError, ValueError, KeyError) as parse_error:
        return _contract_failure(f"output is not contract JSON: {parse_error!r}")

    if not isinstance(problems, list) or not all(isinstance(p, dict) for p in problems):
        return _contract_failure("problems must be a list of objects")

    listing = context.get("vars", {}).get("listing")
    if not isinstance(listing, str) or not listing:
        return _contract_failure("listing var missing from test context")

    component_results = []
    total_quotes = 0
    fabricated_quotes = 0

    for problem in problems:
        problem_id = problem.get("id", "?")
        quotes = problem.get("evidence", [])
        if not isinstance(quotes, list) or not all(isinstance(q, str) for q in quotes):
            return _contract_failure(f"{problem.get('id', '?')}: evidence must be a list of strings")
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
