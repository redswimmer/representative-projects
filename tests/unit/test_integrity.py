"""Behavior tests for project-set integrity: the requested number of ranked
projects, every id reference resolving, and every problem accounted for —
addressed by some project or explicitly out of scope."""

import json

from integrity import (
    find_contradictions,
    find_unaccounted_problems,
    find_unknown_ids,
    get_assert,
)

PROBLEMS_VAR = json.dumps({
    "problems": [
        {"id": "P1", "problem": "pipeline fails silently", "evidence": ["x"], "rationale": "r"},
        {"id": "P2", "problem": "metrics nobody trusts", "evidence": ["y"], "rationale": "r"},
    ]
})


def ctx(num_projects=2):
    return {"vars": {"problems": PROBLEMS_VAR, "num_projects": str(num_projects)}}


def proposal(projects, out_of_scope=()):
    return json.dumps({"projects": projects, "out_of_scope": list(out_of_scope)})


def project(components, roadmap=None):
    return {
        "title": "t",
        "summary": "s",
        "components": components,
        "roadmap": roadmap or [{"milestone": "m", "components": [c["id"] for c in components]}],
    }


def component(cid, addresses):
    return {"id": cid, "name": "n", "description": "d", "addresses": addresses,
            "rationale": "r"}


# --- pure logic ---------------------------------------------------------------


def test_known_ids_are_not_flagged():
    assert find_unknown_ids(["P1", "P2"], {"P1", "P2"}) == []


def test_unknown_ids_are_reported_in_claim_order():
    assert find_unknown_ids(["P9", "P1", "P8"], {"P1"}) == ["P9", "P8"]


def test_fully_accounted_problems_are_not_flagged():
    assert find_unaccounted_problems(["P1", "P2"], ["P1"], ["P2"]) == []


def test_unaccounted_problem_is_reported():
    assert find_unaccounted_problems(["P1", "P2"], ["P1"], []) == ["P2"]


def test_contradiction_is_reported():
    assert find_contradictions(["P1", "P2"], ["P2"]) == ["P2"]


# --- get_assert behavior ------------------------------------------------------


def test_two_projects_covering_all_problems_pass():
    output = proposal([
        project([component("C1", ["P1"])]),
        project([component("C1", ["P2"])]),
    ])
    result = get_assert(output, ctx(2))
    assert result["pass_"] is True and result["score"] == 1.0
    assert result["named_scores"]["problem_accounting"] == 1.0
    assert result["named_scores"]["problem_coverage"] == 1.0


def test_shared_out_of_scope_accounts_for_a_skipped_problem():
    output = proposal(
        [project([component("C1", ["P1"])]), project([component("C1", ["P1"])])],
        out_of_scope=[{"id": "P2", "rationale": "cultural issue, not demonstrable"}],
    )
    result = get_assert(output, ctx(2))
    assert result["pass_"] is True
    assert result["named_scores"]["problem_coverage"] == 0.5
    assert any("cultural issue" in c["reason"] for c in result["component_results"])


def test_wrong_project_count_fails():
    output = proposal([project([component("C1", ["P1", "P2"])])])
    result = get_assert(output, ctx(3))
    assert result["pass_"] is False
    assert "expected 3 projects, got 1" in result["reason"] or "count WRONG" in result["reason"]


def test_silently_dropped_problem_fails_accounting():
    output = proposal([project([component("C1", ["P1"])])])
    result = get_assert(output, ctx(1))
    assert result["pass_"] is False
    assert "P2" in result["reason"]
    assert result["named_scores"]["problem_accounting"] == 0.5


def test_problem_both_addressed_and_out_of_scope_fails():
    output = proposal(
        [project([component("C1", ["P1", "P2"])])],
        out_of_scope=[{"id": "P2", "rationale": "too costly"}],
    )
    result = get_assert(output, ctx(1))
    assert result["pass_"] is False
    assert "contradictions: P2" in result["reason"]


def test_dangling_out_of_scope_id_fails():
    output = proposal(
        [project([component("C1", ["P1", "P2"])])],
        out_of_scope=[{"id": "P9", "rationale": "does not exist"}],
    )
    result = get_assert(output, ctx(1))
    assert result["pass_"] is False
    assert any("unknown problem id — P9" in c["reason"] for c in result["component_results"])


def test_dangling_address_ref_fails_and_names_project_and_component():
    output = proposal([
        project([component("C1", ["P1", "P9"])]),
        project([component("C1", ["P2"])]),
    ])
    result = get_assert(output, ctx(2))
    assert result["pass_"] is False
    assert result["named_scores"]["ref_integrity"] < 1.0
    assert any("project 1 C1" in c["reason"] and "P9" in c["reason"]
               for c in result["component_results"] if not c["pass_"])


def test_roadmap_may_only_reference_its_own_projects_components():
    output = proposal([
        project([component("C1", ["P1"])]),
        project([component("C2", ["P2"])],
                roadmap=[{"milestone": "m", "components": ["C1"]}]),
    ])
    result = get_assert(output, ctx(2))
    assert result["pass_"] is False
    assert any("project 2 roadmap" in c["reason"] and "C1" in c["reason"]
               for c in result["component_results"] if not c["pass_"])


# --- get_assert contract: malformed input fails gracefully, never raises ------


def test_non_json_output_fails_without_raising():
    result = get_assert("not json at all", ctx())
    assert result["pass_"] is False and "not contract JSON" in result["reason"]


def test_missing_problems_var_fails_without_raising():
    output = proposal([project([component("C1", ["P1"])])])
    result = get_assert(output, {"vars": {"num_projects": "1"}})
    assert result["pass_"] is False and "problems var" in result["reason"]


def test_missing_num_projects_var_fails_without_raising():
    output = proposal([project([component("C1", ["P1", "P2"])])])
    result = get_assert(output, {"vars": {"problems": PROBLEMS_VAR}})
    assert result["pass_"] is False and "num_projects" in result["reason"]


def test_addresses_as_plain_string_fails_without_raising():
    bad = {"id": "C1", "name": "n", "description": "d", "addresses": "P1", "rationale": "r"}
    output = proposal([project([bad])])
    result = get_assert(output, ctx(1))
    assert result["pass_"] is False and "list of strings" in result["reason"]


def test_out_of_scope_as_plain_strings_fails_without_raising():
    output = json.dumps({
        "projects": [project([component("C1", ["P1", "P2"])])],
        "out_of_scope": ["P2"],
    })
    result = get_assert(output, ctx(1))
    assert result["pass_"] is False and "out_of_scope" in result["reason"]
