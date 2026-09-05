"""Behavior tests for the runner's prompt filling: agent inputs are built from
the same {{name}} slots the eval prompts use."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pipeline import fill_prompt


def test_fills_every_named_slot():
    template = "Listing {{listing_id}}:\n{{listing}}"
    filled = fill_prompt(template, {"listing_id": "acme", "listing": "We hire."})
    assert filled == "Listing acme:\nWe hire."


def test_unknown_slot_stays_visible_instead_of_vanishing():
    filled = fill_prompt("Problems: {{problems}}", {"listing": "irrelevant"})
    assert filled == "Problems: {{problems}}"


def test_value_containing_braces_is_inserted_literally():
    filled = fill_prompt("Data: {{problems}}", {"problems": '{"problems": []}'})
    assert filled == 'Data: {"problems": []}'
