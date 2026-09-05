"""Behavior tests for project integrity: do all id references resolve, and is
every verified problem addressed by some component?"""

import json

from integrity import find_unaddressed_problems, find_unknown_ids, get_assert

PROBLEMS_VAR = json.dumps({
    "problems": [
        {"id": "P1", "problem": "pipeline fails silently", "evidence": ["x"], "rationale": "r"},
        {"id": "P2", "problem": "metrics nobody trusts", "evidence": ["y"], "rationale": "r"},
    ]
})
CONTEXT = {"vars": {"problems": PROBLEMS_VAR}}


def project(components, roadmap):
    return json.dumps({
        "project": {
            "title": "t",
            "summary": "s",
            "components": components,
            "roadmap": roadmap,
        }
    })


def component(cid, addresses):
    return {"id": cid, "name": "n", "description": "d", "addresses": addresses,
            "justification": "j"}


# --- pure logic ---------------------------------------------------------------


def test_known_ids_are_not_flagged():
    assert find_unknown_ids(["P1", "P2"], {"P1", "P2"}) == []


def test_unknown_ids_are_reported_in_claim_order():
    assert find_unknown_ids(["P9", "P1", "P8"], {"P1"}) == ["P9", "P8"]


def test_fully_addressed_problems_are_not_flagged():
    assert find_unaddressed_problems(["P1", "P2"], ["P2", "P1"]) == []


def test_unaddressed_problem_is_reported():
    assert find_unaddressed_problems(["P1", "P2"], ["P1"]) == ["P2"]


# --- get_assert behavior ------------------------------------------------------


def test_consistent_project_passes_with_full_scores():
    output = project(
        [component("C1", ["P1"]), component("C2", ["P2"])],
        [{"milestone": "m1", "components": ["C1", "C2"]}],
    )
    result = get_assert(output, CONTEXT)
    assert result["pass_"] is True and result["score"] == 1.0
    assert result["named_scores"] == {"ref_integrity": 1.0, "problem_coverage": 1.0}


def test_dangling_address_ref_fails_and_names_the_offender():
    output = project([component("C1", ["P1", "P9"]), component("C2", ["P2"])],
                     [{"milestone": "m1", "components": ["C1"]}])
    result = get_assert(output, CONTEXT)
    assert result["pass_"] is False
    assert result["named_scores"]["ref_integrity"] < 1.0
    assert any("P9" in c["reason"] for c in result["component_results"] if not c["pass_"])


def test_unaddressed_problem_scores_the_coverage_fraction():
    output = project([component("C1", ["P1"])],
                     [{"milestone": "m1", "components": ["C1"]}])
    result = get_assert(output, CONTEXT)
    assert result["pass_"] is False
    assert result["named_scores"]["problem_coverage"] == 0.5
    assert "P2" in result["reason"]


def test_dangling_roadmap_ref_fails_and_names_the_offender():
    output = project([component("C1", ["P1", "P2"])],
                     [{"milestone": "m1", "components": ["C1", "C7"]}])
    result = get_assert(output, CONTEXT)
    assert result["pass_"] is False
    assert any("C7" in c["reason"] for c in result["component_results"] if not c["pass_"])


# --- get_assert contract: malformed input fails gracefully, never raises ------


def test_non_json_output_fails_without_raising():
    result = get_assert("not json at all", CONTEXT)
    assert result["pass_"] is False and "not contract JSON" in result["reason"]


def test_missing_problems_var_fails_without_raising():
    output = project([component("C1", ["P1"])], [{"milestone": "m", "components": ["C1"]}])
    result = get_assert(output, {"vars": {}})
    assert result["pass_"] is False and "problems var" in result["reason"]


def test_addresses_as_plain_string_fails_without_raising():
    bad = {"id": "C1", "name": "n", "description": "d", "addresses": "P1",
           "justification": "j"}
    result = get_assert(project([bad], [{"milestone": "m", "components": ["C1"]}]), CONTEXT)
    assert result["pass_"] is False and "list of strings" in result["reason"]
