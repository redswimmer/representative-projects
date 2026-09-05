"""Behavior tests for evidence grounding: does a claimed quote actually appear in the listing?"""

from grounding import find_ungrounded_quotes, get_assert

LISTING = '''Acme Corp is hiring a Senior Data Engineer.
You will take ownership of our nightly ETL
pipeline - it currently fails "silently" and finance
reports arrive LATE. Tech: Python, dbt, Airflow.'''


def test_verbatim_quote_is_grounded():
    assert find_ungrounded_quotes(['it currently fails "silently"'], LISTING) == []


def test_fabricated_quote_is_reported():
    quotes = ["experience with Kubernetes required"]
    assert find_ungrounded_quotes(quotes, LISTING) == quotes


def test_quote_spanning_a_line_wrap_is_grounded():
    assert find_ungrounded_quotes(["ownership of our nightly ETL pipeline"], LISTING) == []


def test_prettified_curly_quotes_still_ground():
    # models often emit curly quotes even when the source is ASCII
    assert find_ungrounded_quotes(['fails “silently”'], LISTING) == []


def test_em_dash_matches_source_hyphen():
    assert find_ungrounded_quotes(['pipeline — it currently fails'], LISTING) == []


def test_case_difference_still_grounds():
    assert find_ungrounded_quotes(["reports arrive late."], LISTING) == []


def test_unicode_ligature_still_grounds():
    # NFKC folds the ﬁ ligature into "fi"
    assert find_ungrounded_quotes(["ﬁnance reports"], LISTING) == []


def test_partial_overlap_is_still_fabrication():
    quotes = ["nightly ETL pipeline that never fails"]
    assert find_ungrounded_quotes(quotes, LISTING) == quotes


def test_mixed_quotes_reports_only_the_fabricated_one():
    grounded = "Tech: Python, dbt, Airflow."
    fabricated = "must mentor junior engineers"
    assert find_ungrounded_quotes([grounded, fabricated], LISTING) == [fabricated]


def test_empty_quote_list_is_vacuously_grounded():
    assert find_ungrounded_quotes([], LISTING) == []


# --- get_assert contract: malformed output fails gracefully, never raises ---


def test_null_problems_fails_without_raising():
    result = get_assert('{"problems": null}', {"vars": {"listing": LISTING}})
    assert result["pass_"] is False and "list of objects" in result["reason"]


def test_non_dict_problem_entry_fails_without_raising():
    result = get_assert('{"problems": ["not a dict"]}', {"vars": {"listing": LISTING}})
    assert result["pass_"] is False


def test_evidence_as_plain_string_fails_without_raising():
    output = '{"problems": [{"id": "P1", "evidence": "nightly ETL"}]}'
    result = get_assert(output, {"vars": {"listing": LISTING}})
    assert result["pass_"] is False and "list of strings" in result["reason"]


def test_missing_listing_var_fails_without_raising():
    output = '{"problems": [{"id": "P1", "evidence": ["nightly ETL"]}]}'
    result = get_assert(output, {"vars": {}})
    assert result["pass_"] is False and "listing var" in result["reason"]


def test_partially_grounded_output_scores_the_fraction():
    output = '{"problems": [{"id": "P1", "evidence": ["nightly ETL", "made-up quote"]}]}'
    result = get_assert(output, {"vars": {"listing": LISTING}})
    assert result["pass_"] is False and result["score"] == 0.5
    assert "1/2" in result["reason"]
