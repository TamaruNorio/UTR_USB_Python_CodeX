from collections import Counter

from src.utr_usm02_v117_validation import build_validation_plan, summarize_plan
from src.utr_v117_catalog import COMMAND_SPECS, PlanStatus, classify_for_usm02, get_command_spec


def test_catalog_is_mece_54_commands_by_manual_group():
    assert len(COMMAND_SPECS) == 54
    assert len({spec.section for spec in COMMAND_SPECS}) == 54
    assert Counter(spec.section.rsplit(".", 1)[0] for spec in COMMAND_SPECS) == {
        "7.3": 12,
        "7.4": 31,
        "7.5": 11,
    }


def test_usm02_device_exclusions_are_explicit():
    excluded = {
        spec.section
        for spec in COMMAND_SPECS
        if classify_for_usm02(spec, 2100) == PlanStatus.NOT_SUPPORTED_BY_DEVICE
    }
    assert excluded == {"7.3.6", "7.3.7", "7.4.10", "7.4.12", "7.4.26", "7.4.28"}


def test_rom_gates_are_explicit():
    assert classify_for_usm02(get_command_spec("7.3.12"), 2049) == PlanStatus.NOT_SUPPORTED_BY_ROM
    assert classify_for_usm02(get_command_spec("7.3.12"), 2050) == PlanStatus.READY
    assert classify_for_usm02(get_command_spec("7.4.14"), 2052) == PlanStatus.NOT_SUPPORTED_BY_ROM
    assert classify_for_usm02(get_command_spec("7.4.14"), 2100) == PlanStatus.READY
    assert classify_for_usm02(get_command_spec("7.5.11"), None) == PlanStatus.ROM_CHECK_REQUIRED


def test_hard_holds_and_through_command_condition():
    held = {
        spec.section
        for spec in COMMAND_SPECS
        if classify_for_usm02(spec, 2100) == PlanStatus.NOT_EXECUTED_BY_USER_DECISION
    }
    assert held == {"7.3.11", "7.5.5", "7.5.6", "7.5.10"}
    through = get_command_spec("7.5.11")
    assert classify_for_usm02(through, 2100) == PlanStatus.CONDITION_NOT_AVAILABLE
    assert classify_for_usm02(through, 2100, conditions_available=frozenset({"7.5.11"})) == PlanStatus.READY


def test_validation_plan_always_has_54_entries_and_summary_totals_54():
    plan = build_validation_plan(2052)
    assert len(plan) == 54
    assert sum(summarize_plan(plan).values()) == 54
