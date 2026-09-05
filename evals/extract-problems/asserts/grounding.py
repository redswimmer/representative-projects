"""Promptfoo assertion: every evidence quote must appear verbatim in the listing.

One file, two layers: pure matching logic on top (unit-tested from tests/unit/),
the promptfoo GradingResult adapter (get_assert) at the bottom.
"""

import json
import re
import unicodedata
from collections.abc import Sequence

_PUNCTUATION_TRANSLATION = str.maketrans({
    "‘": "'",  # left single curly quote
    "’": "'",  # right single curly quote
    "“": '"',  # left double curly quote
    "”": '"',  # right double curly quote
    "–": "-",  # en dash
    "—": "-",  # em dash
    "−": "-",  # minus sign
})
_WHITESPACE_RUNS = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Collapse cosmetic differences (unicode forms, curly punctuation, whitespace, case)
    so that only real wording differences distinguish two strings."""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_PUNCTUATION_TRANSLATION)
    return _WHITESPACE_RUNS.sub(" ", text).casefold().strip()


def find_ungrounded_quotes(quotes: Sequence[str], listing: str) -> list[str]:
    """Return the quotes that do NOT appear verbatim in the listing, after normalization.

    An empty result means every quote is grounded. Returned quotes keep their
    original form so callers can name the offender.
    """
    normalized_listing = normalize_text(listing)
    return [quote for quote in quotes if normalize_text(quote) not in normalized_listing]


# --- promptfoo adapter -------------------------------------------------------


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
            return _contract_failure(f"{problem_id}: evidence must be a list of strings")
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
