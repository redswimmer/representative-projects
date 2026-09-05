"""Promptfoo assertion: the proposed project must be internally consistent with
the verified problems it was given — no dangling ids, no problem left behind.

One file, two layers: pure set logic on top (unit-tested from tests/unit/),
the promptfoo GradingResult adapter (get_assert) at the bottom.
"""

import json
from collections.abc import Collection, Iterable, Sequence


def find_unknown_ids(claimed: Sequence[str], known: Collection[str]) -> list[str]:
    """Return the claimed ids that name nothing in `known`, in claim order."""
    known_set = set(known)
    return [claimed_id for claimed_id in claimed if claimed_id not in known_set]


def find_unaddressed_problems(problem_ids: Sequence[str], addressed: Iterable[str]) -> list[str]:
    """Return the problem ids no component addresses, in problem order."""
    addressed_set = set(addressed)
    return [problem_id for problem_id in problem_ids if problem_id not in addressed_set]


# --- promptfoo adapter -------------------------------------------------------


def _contract_failure(reason: str) -> dict:
    return {"pass_": False, "score": 0.0, "reason": reason}


def _id_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def get_assert(output, context):
    try:
        data = output if isinstance(output, dict) else json.loads(output)
        project = data["project"]
        components = project["components"]
        roadmap = project["roadmap"]
    except (TypeError, ValueError, KeyError) as parse_error:
        return _contract_failure(f"output is not contract JSON: {parse_error!r}")

    try:
        problems_var = context.get("vars", {}).get("problems")
        problem_ids = [problem["id"] for problem in json.loads(problems_var)["problems"]]
    except (TypeError, ValueError, KeyError) as parse_error:
        return _contract_failure(f"problems var is not contract JSON: {parse_error!r}")
    if not problem_ids:
        return _contract_failure("fixture contains no problem ids")

    if not isinstance(components, list) or not all(isinstance(c, dict) for c in components):
        return _contract_failure("components must be a list of objects")
    if not isinstance(roadmap, list) or not all(isinstance(m, dict) for m in roadmap):
        return _contract_failure("roadmap must be a list of objects")

    component_results = []
    total_refs = 0
    dangling_refs = 0

    component_ids = []
    all_addresses = []
    for component in components:
        component_id = component.get("id", "?")
        component_ids.append(component_id)
        addresses = component.get("addresses", [])
        if not _id_list(addresses):
            return _contract_failure(f"{component_id}: addresses must be a list of strings")
        all_addresses.extend(addresses)
        unknown = find_unknown_ids(addresses, problem_ids)
        total_refs += len(addresses)
        dangling_refs += len(unknown)
        component_results.append({
            "pass_": not unknown,
            "score": 0.0 if unknown else 1.0,
            "reason": (
                f"{component_id}: unknown problem ids — {', '.join(unknown)}"
                if unknown
                else f"{component_id}: addresses valid problems"
            ),
        })

    for milestone in roadmap:
        label = milestone.get("milestone", "?")
        milestone_components = milestone.get("components", [])
        if not _id_list(milestone_components):
            return _contract_failure(f"roadmap '{label}': components must be a list of strings")
        unknown = find_unknown_ids(milestone_components, component_ids)
        total_refs += len(milestone_components)
        dangling_refs += len(unknown)
        component_results.append({
            "pass_": not unknown,
            "score": 0.0 if unknown else 1.0,
            "reason": (
                f"roadmap '{label}': unknown component ids — {', '.join(unknown)}"
                if unknown
                else f"roadmap '{label}': references existing components"
            ),
        })

    unaddressed = find_unaddressed_problems(problem_ids, all_addresses)
    for problem_id in problem_ids:
        is_addressed = problem_id not in set(unaddressed)
        component_results.append({
            "pass_": is_addressed,
            "score": 1.0 if is_addressed else 0.0,
            "reason": (
                f"{problem_id}: addressed"
                if is_addressed
                else f"{problem_id}: addressed by no component"
            ),
        })

    ref_integrity = (total_refs - dangling_refs) / total_refs if total_refs else 0.0
    problem_coverage = (len(problem_ids) - len(unaddressed)) / len(problem_ids)
    total_checks = total_refs + len(problem_ids)
    passed_checks = (total_refs - dangling_refs) + (len(problem_ids) - len(unaddressed))
    all_consistent = dangling_refs == 0 and not unaddressed

    return {
        "pass_": all_consistent,
        "score": passed_checks / total_checks,
        "reason": (
            "all ids resolve and every problem is addressed"
            if all_consistent
            else f"{dangling_refs} dangling id refs; unaddressed problems: "
            f"{', '.join(unaddressed) if unaddressed else 'none'}"
        ),
        "named_scores": {
            "ref_integrity": ref_integrity,
            "problem_coverage": problem_coverage,
        },
        "component_results": component_results,
    }
