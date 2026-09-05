"""Evidence grounding: is a quote the model attributes to a listing actually in it?

Pure functions only — no promptfoo types, no IO.
"""

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
