"""Downstream punctuation heuristic: caller's stall gates and retry cap stay intact."""

import pytest

from agent.agent_runtime_helpers import trailing_continue_intent


@pytest.mark.parametrize("text", ["Verifying the configuration:", "x" * 900 + ": \n\t"])
def test_trailing_colon_announces_continuation_at_any_length(text):
    assert trailing_continue_intent(text)


@pytest.mark.parametrize("text", ["Status: complete.", "SELECT 1;", "", None])
def test_other_punctuation_does_not_add_a_trigger(text):
    assert not trailing_continue_intent(text)
