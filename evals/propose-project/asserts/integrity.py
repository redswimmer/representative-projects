"""Promptfoo assertion: the ranked project set must account for every problem
it was given — each problem addressed by some project's component or explicitly
ruled out of scope with a rationale — every id reference must resolve, and the
number of projects must match what was requested.

One file, two layers: pure set logic on top (unit-tested from tests/unit/),
the promptfoo GradingResult adapter (get_assert) at the bottom.
"""

import json
from collections.abc import Collection, Iterable, Sequence


def find_unknown_ids(claimed: Sequence[str], known: Collection[str]) -> list[str]:
    """Return the claimed ids that name nothing in `known`, in claim order."""
    known_set = set(known)
    return [claimed_id for claimed_id in claimed if claimed_id not in known_set]


def find_unaccounted_problems(
    problem_ids: Sequence[str], addressed: Iterable[str], out_of_scope: Iterable[str]
) -> list[str]:
    """Return the problem ids neither addressed nor ruled out of scope, in problem order."""
    accounted = set(addressed) | set(out_of_scope)
    return [problem_id for problem_id in problem_ids if problem_id not in accounted]


def find_contradictions(addressed: Iterable[str], out_of_scope: Sequence[str]) -> list[str]:
    """Return the ids claimed both addressed and out of scope, in out-of-scope order."""
    addressed_set = set(addressed)
    return [problem_id for problem_id in out_of_scope if problem_id in addressed_set]


# --- promptfoo adapter -------------------------------------------------------


def _contract_failure(reason: str) -> dict:
    return {"pass_": False, "score": 0.0, "reason": reason}


def _id_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def get_assert(output, context):
    try:
        data = output if isinstance(output, dict) else json.loads(output)
        projects = data["projects"]
        out_of_scope = data["out_of_scope"]
    except (TypeError, ValueError, KeyError) as parse_error:
        return _contract_failure(f"output is not contract JSON: {parse_error!r}")

    test_vars = context.get("vars", {})
    try:
        problem_ids = [problem["id"] for problem in json.loads(test_vars.get("problems"))["problems"]]
    except (TypeError, ValueError, KeyError) as parse_error:
        return _contract_failure(f"problems var is not contract JSON: {parse_error!r}")
    if not problem_ids:
        return _contract_failure("fixture contains no problem ids")
    try:
        expected_projects = int(test_vars.get("num_projects"))
    except (TypeError, ValueError):
        return _contract_failure("num_projects var missing or not an integer")

    if not isinstance(projects, list) or not all(isinstance(p, dict) for p in projects):
        return _contract_failure("projects must be a list of objects")
    if not isinstance(out_of_scope, list) or not all(isinstance(o, dict) for o in out_of_scope):
        return _contract_failure("out_of_scope must be a list of objects")

    component_results = []
    total_refs = 0
    dangling_refs = 0
    all_addresses = []

    count_ok = len(projects) == expected_projects
    component_results.append({
        "pass_": count_ok,
        "score": 1.0 if count_ok else 0.0,
        "reason": (
            f"{len(projects)} projects as requested"
            if count_ok
            else f"expected {expected_projects} projects, got {len(projects)}"
        ),
    })

    for rank, project in enumerate(projects, start=1):
        components = project.get("components")
        roadmap = project.get("roadmap")
        if not isinstance(components, list) or not all(isinstance(c, dict) for c in components):
            return _contract_failure(f"project {rank}: components must be a list of objects")
        if not isinstance(roadmap, list) or not all(isinstance(m, dict) for m in roadmap):
            return _contract_failure(f"project {rank}: roadmap must be a list of objects")

        component_ids = []
        for component in components:
            component_id = component.get("id", "?")
            component_ids.append(component_id)
            addresses = component.get("addresses", [])
            if not _id_list(addresses):
                return _contract_failure(
                    f"project {rank} {component_id}: addresses must be a list of strings"
                )
            all_addresses.extend(addresses)
            unknown = find_unknown_ids(addresses, problem_ids)
            total_refs += len(addresses)
            dangling_refs += len(unknown)
            component_results.append({
                "pass_": not unknown,
                "score": 0.0 if unknown else 1.0,
                "reason": (
                    f"project {rank} {component_id}: unknown problem ids — {', '.join(unknown)}"
                    if unknown
                    else f"project {rank} {component_id}: addresses valid problems"
                ),
            })

        for milestone in roadmap:
            label = milestone.get("milestone", "?")
            milestone_components = milestone.get("components", [])
            if not _id_list(milestone_components):
                return _contract_failure(
                    f"project {rank} roadmap '{label}': components must be a list of strings"
                )
            unknown = find_unknown_ids(milestone_components, component_ids)
            total_refs += len(milestone_components)
            dangling_refs += len(unknown)
            component_results.append({
                "pass_": not unknown,
                "score": 0.0 if unknown else 1.0,
                "reason": (
                    f"project {rank} roadmap '{label}': unknown component ids — "
                    f"{', '.join(unknown)}"
                    if unknown
                    else f"project {rank} roadmap '{label}': references its own components"
                ),
            })

    out_ids = []
    for entry in out_of_scope:
        out_id = entry.get("id", "?")
        out_ids.append(out_id)
        rationale = entry.get("rationale", "")
        unknown = find_unknown_ids([out_id], problem_ids)
        total_refs += 1
        dangling_refs += len(unknown)
        component_results.append({
            "pass_": not unknown,
            "score": 0.0 if unknown else 1.0,
            "reason": (
                f"out_of_scope: unknown problem id — {out_id}"
                if unknown
                else f"{out_id}: out of scope — {rationale}"
            ),
        })

    unaccounted = find_unaccounted_problems(problem_ids, all_addresses, out_ids)
    contradictions = find_contradictions(all_addresses, out_ids)
    for problem_id in problem_ids:
        if problem_id in set(contradictions):
            verdict, ok = "both addressed and out of scope", False
        elif problem_id in set(unaccounted):
            verdict, ok = "neither addressed nor ruled out of scope", False
        elif problem_id in set(out_ids):
            continue  # its out_of_scope row above already tells the story
        else:
            verdict, ok = "addressed", True
        component_results.append({
            "pass_": ok,
            "score": 1.0 if ok else 0.0,
            "reason": f"{problem_id}: {verdict}",
        })

    failed_problems = len(unaccounted) + len(set(contradictions))
    ref_integrity = (total_refs - dangling_refs) / total_refs if total_refs else 0.0
    problem_accounting = (len(problem_ids) - failed_problems) / len(problem_ids)
    addressed_set = set(all_addresses) & set(problem_ids)
    all_consistent = count_ok and dangling_refs == 0 and failed_problems == 0
    total_checks = 1 + total_refs + len(problem_ids)
    passed_checks = (
        int(count_ok)
        + (total_refs - dangling_refs)
        + (len(problem_ids) - failed_problems)
    )

    return {
        "pass_": all_consistent,
        "score": passed_checks / total_checks,
        "reason": (
            f"{len(projects)} projects; all ids resolve and every problem is accounted for"
            if all_consistent
            else f"count {'ok' if count_ok else 'WRONG'}; {dangling_refs} dangling id refs; "
            f"unaccounted: {', '.join(unaccounted) or 'none'}; contradictions: "
            f"{', '.join(contradictions) or 'none'}"
        ),
        "named_scores": {
            "ref_integrity": ref_integrity,
            "problem_accounting": problem_accounting,
            "problem_coverage": len(addressed_set) / len(problem_ids),
        },
        "component_results": component_results,
    }
