"""
Tests for surveychat/helpers.py

Covers the three pure helper functions:
  - check_passcode_routing   (configuration validation)
  - build_api_messages       (LLM request construction)
  - build_transcript         (transcript serialisation)
"""
import pytest
import sys
import os

# Ensure the repo root is on the path so `helpers` is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from helpers import check_passcode_routing, build_api_messages, build_transcript


# ---------------------------------------------------------------------------
# check_passcode_routing
# ---------------------------------------------------------------------------

class TestCheckPasscodeRouting:

    def _cond(self, name, passcode=None):
        c = {"name": name, "system_prompt": "You are helpful.", "model": "gpt-4o"}
        if passcode is not None:
            c["passcode"] = passcode
        return c

    # --- valid configurations ---

    def test_no_passcodes_is_valid(self):
        """Random routing: no passcode keys at all."""
        conds = [self._cond("A"), self._cond("B")]
        ok, err = check_passcode_routing(conds, 2)
        assert ok is True
        assert err == ""

    def test_all_passcodes_defined_is_valid(self):
        conds = [self._cond("A", "ALPHA"), self._cond("B", "BETA")]
        ok, err = check_passcode_routing(conds, 2)
        assert ok is True
        assert err == ""

    def test_case_insensitive_uniqueness_distinct_codes(self):
        """Different codes that differ only in case are still distinct after lowercasing."""
        conds = [self._cond("A", "alpha"), self._cond("B", "BETA")]
        ok, err = check_passcode_routing(conds, 2)
        assert ok is True

    def test_extra_conditions_beyond_n_are_ignored(self):
        """Only the first n_conditions entries are considered active."""
        conds = [
            self._cond("A", "ALPHA"),
            self._cond("B", "BETA"),
            self._cond("C"),          # no passcode, but n_conditions=2 so ignored
        ]
        ok, err = check_passcode_routing(conds, 2)
        assert ok is True

    def test_survey_mode_single_condition_no_passcode(self):
        conds = [self._cond("Interview")]
        ok, err = check_passcode_routing(conds, 1)
        assert ok is True

    def test_non_positive_n_conditions_returns_error(self):
        conds = [self._cond("A")]
        ok, err = check_passcode_routing(conds, 0)
        assert ok is False
        assert "at least" in err.lower()

    def test_n_conditions_greater_than_conditions_length_returns_error(self):
        conds = [self._cond("A")]
        ok, err = check_passcode_routing(conds, 2)
        assert ok is False
        assert "contains" in err.lower()

    def test_non_dict_condition_returns_error(self):
        conds = [self._cond("A", "ALPHA"), "not-a-dict"]
        ok, err = check_passcode_routing(conds, 2)
        assert ok is False
        assert "dictionary" in err.lower()

    # --- partial configuration ---

    def test_partial_passcode_config_returns_error(self):
        """One of two conditions has a passcode and the other does not."""
        conds = [self._cond("A", "ALPHA"), self._cond("B")]
        ok, err = check_passcode_routing(conds, 2)
        assert ok is False
        assert "partially configured" in err.lower() or "partial" in err.lower()

    def test_partial_config_message_includes_counts(self):
        conds = [self._cond("A", "ALPHA"), self._cond("B"), self._cond("C")]
        ok, err = check_passcode_routing(conds, 3)
        assert ok is False
        assert "1" in err   # 1 of 3 passcoded
        assert "3" in err

    # --- blank passcodes ---

    def test_empty_passcode_string_returns_error(self):
        conds = [self._cond("A", ""), self._cond("B", "BETA")]
        ok, err = check_passcode_routing(conds, 2)
        assert ok is False
        assert "empty" in err.lower()

    def test_whitespace_only_passcode_returns_error(self):
        conds = [self._cond("A", "   "), self._cond("B", "BETA")]
        ok, err = check_passcode_routing(conds, 2)
        assert ok is False

    def test_non_string_passcode_returns_error(self):
        conds = [self._cond("A", 123), self._cond("B", "BETA")]
        ok, err = check_passcode_routing(conds, 2)
        assert ok is False
        assert "not strings" in err.lower()

    # --- duplicate passcodes ---

    def test_duplicate_passcodes_returns_error(self):
        conds = [self._cond("A", "ALPHA"), self._cond("B", "ALPHA")]
        ok, err = check_passcode_routing(conds, 2)
        assert ok is False
        assert "unique" in err.lower() or "duplicate" in err.lower() or "same" in err.lower()

    def test_duplicate_passcodes_case_insensitive(self):
        """'alpha' and 'ALPHA' are considered duplicates."""
        conds = [self._cond("A", "alpha"), self._cond("B", "ALPHA")]
        ok, err = check_passcode_routing(conds, 2)
        assert ok is False

    def test_three_arm_with_one_duplicate(self):
        conds = [
            self._cond("A", "RED"),
            self._cond("B", "BLUE"),
            self._cond("C", "RED"),   # duplicate of A
        ]
        ok, err = check_passcode_routing(conds, 3)
        assert ok is False


# ---------------------------------------------------------------------------
# build_api_messages
# ---------------------------------------------------------------------------

class TestBuildApiMessages:

    def test_system_prompt_at_position_zero(self):
        msgs = build_api_messages([], "Be helpful.")
        assert msgs[0] == {"role": "system", "content": "Be helpful."}

    def test_empty_conversation(self):
        result = build_api_messages([], "System prompt.")
        assert result == [{"role": "system", "content": "System prompt."}]

    def test_conversation_messages_appended_in_order(self):
        conversation = [
            {"role": "user", "content": "Hello", "timestamp": "2026-01-01T00:00:00Z"},
            {"role": "assistant", "content": "Hi there", "timestamp": "2026-01-01T00:00:01Z"},
        ]
        result = build_api_messages(conversation, "Prompt.")
        assert len(result) == 3
        assert result[1] == {"role": "user", "content": "Hello"}
        assert result[2] == {"role": "assistant", "content": "Hi there"}

    def test_timestamp_stripped_from_output(self):
        """Timestamps must not appear in the API payload."""
        conversation = [
            {"role": "user", "content": "Hi", "timestamp": "2026-01-01T00:00:00Z"},
        ]
        result = build_api_messages(conversation, "Prompt.")
        for msg in result:
            assert "timestamp" not in msg

    def test_role_and_content_preserved_exactly(self):
        conversation = [{"role": "user", "content": "Test message", "timestamp": ""}]
        result = build_api_messages(conversation, "Sys")
        assert result[1]["content"] == "Test message"
        assert result[1]["role"] == "user"

    def test_multiline_system_prompt(self):
        prompt = "Line one.\nLine two.\nLine three."
        result = build_api_messages([], prompt)
        assert result[0]["content"] == prompt

    def test_multiple_turns_order_preserved(self):
        conversation = [
            {"role": "user", "content": "Q1", "timestamp": ""},
            {"role": "assistant", "content": "A1", "timestamp": ""},
            {"role": "user", "content": "Q2", "timestamp": ""},
        ]
        result = build_api_messages(conversation, "S")
        assert [m["content"] for m in result] == ["S", "Q1", "A1", "Q2"]


# ---------------------------------------------------------------------------
# build_transcript
# ---------------------------------------------------------------------------

class TestBuildTranscript:

    def test_output_has_messages_key(self):
        result = build_transcript([])
        assert "messages" in result

    def test_empty_conversation_gives_empty_list(self):
        result = build_transcript([])
        assert result["messages"] == []

    def test_user_role_relabelled_participant(self):
        msgs = [{"role": "user", "content": "Hi", "timestamp": "2026-01-01T00:00:00Z"}]
        result = build_transcript(msgs)
        assert result["messages"][0]["role"] == "participant"

    def test_assistant_role_unchanged(self):
        msgs = [{"role": "assistant", "content": "Hello", "timestamp": "2026-01-01T00:00:01Z"}]
        result = build_transcript(msgs)
        assert result["messages"][0]["role"] == "assistant"

    def test_content_preserved(self):
        msgs = [{"role": "user", "content": "My answer", "timestamp": ""}]
        result = build_transcript(msgs)
        assert result["messages"][0]["content"] == "My answer"

    def test_timestamp_preserved(self):
        ts = "2026-03-06T14:22:01+00:00"
        msgs = [{"role": "user", "content": "Hi", "timestamp": ts}]
        result = build_transcript(msgs)
        assert result["messages"][0]["timestamp"] == ts

    def test_missing_timestamp_defaults_to_empty_string(self):
        msgs = [{"role": "user", "content": "Hi"}]   # no timestamp key
        result = build_transcript(msgs)
        assert result["messages"][0]["timestamp"] == ""

    def test_multiple_turns_all_present(self):
        msgs = [
            {"role": "user", "content": "Hello", "timestamp": ""},
            {"role": "assistant", "content": "Hi", "timestamp": ""},
            {"role": "user", "content": "Bye", "timestamp": ""},
        ]
        result = build_transcript(msgs)
        assert len(result["messages"]) == 3

    def test_multiple_turns_roles_correct(self):
        msgs = [
            {"role": "user",      "content": "Q", "timestamp": ""},
            {"role": "assistant", "content": "A", "timestamp": ""},
        ]
        result = build_transcript(msgs)
        assert result["messages"][0]["role"] == "participant"
        assert result["messages"][1]["role"] == "assistant"

    def test_no_condition_or_model_in_transcript(self):
        """Condition name and model must be absent from transcript output."""
        msgs = [{"role": "user", "content": "Hi", "timestamp": ""}]
        result = build_transcript(msgs)
        for entry in result["messages"]:
            assert "condition" not in entry
            assert "model" not in entry

    def test_output_is_json_serialisable(self):
        import json
        msgs = [
            {"role": "user", "content": "Hello 🌍", "timestamp": "2026-01-01T00:00:00Z"},
            {"role": "assistant", "content": "Hi there!", "timestamp": "2026-01-01T00:00:01Z"},
        ]
        result = build_transcript(msgs)
        serialised = json.dumps(result, ensure_ascii=False)
        restored = json.loads(serialised)
        assert restored["messages"][0]["content"] == "Hello 🌍"
