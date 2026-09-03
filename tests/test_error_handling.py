from unittest import mock

import pytest
import streamlit as st

# Import the function under test and its directly imported exception classes.
import app


class ConnectionError(Exception):
    pass


class BadRequestError(Exception):
    pass


class StatusError(Exception):
    pass


# These subclasses mirror the OpenAI SDK hierarchy. generate_reply must catch
# them before StatusError so retryable failures receive the retry message.
class RateLimitError(StatusError):
    pass


class InternalServerError(StatusError):
    pass

# ----------------------------------------------------------------------
# Helper: build a minimal “condition” dict that generate_reply expects.
# ----------------------------------------------------------------------
@pytest.fixture
def dummy_condition():
    return {
        "model": "gpt-4o",  # any string – the client is mocked
        "system_prompt": "You are a helpful bot.",
    }


# ----------------------------------------------------------------------
# Helper: reset Streamlit session state before each test.
# ----------------------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_session_state():
    # Streamlit stores state in a global dict; clear it so tests are isolated.
    st.session_state.clear()
    st.session_state["messages"] = []
    st.error.reset_mock()
    with mock.patch.multiple(
        app,
        APIConnectionError=ConnectionError,
        BadRequestError=BadRequestError,
        APIStatusError=StatusError,
        RateLimitError=RateLimitError,
        InternalServerError=InternalServerError,
    ):
        yield
    st.session_state.clear()


# ----------------------------------------------------------------------
# Simulate a connection‑level failure (e.g. DNS / network error)
# ----------------------------------------------------------------------
def test_api_connection_error(dummy_condition):
    st.session_state["messages"].append({"role": "user", "content": "Hello"})
    with mock.patch(
        "app.client.chat.completions.create",
        side_effect=ConnectionError("Network unreachable"),
    ):
        response, user_turns = app.generate_reply(dummy_condition)

    assert response is None
    assert user_turns == 1
    assert st.session_state["messages"] == []
    st.error.assert_called_once_with("Error. Please contact the researchers.")


# ----------------------------------------------------------------------
# Simulate a non-retryable HTTP status error. A RateLimitError or
# InternalServerError would be caught by the preceding, retry-specific branch.
# ----------------------------------------------------------------------
def test_api_status_error(dummy_condition):
    st.session_state["messages"].append({"role": "user", "content": "Hello"})

    with mock.patch(
        "app.client.chat.completions.create",
        # Use the base status error so this reaches app.py's final
        # `except APIStatusError` branch.
        side_effect=StatusError("Service unavailable"),
    ):
        response, user_turns = app.generate_reply(dummy_condition)

    assert response is None
    assert user_turns == 1
    assert st.session_state["messages"] == []
    st.error.assert_called_once_with("Error. Please contact the researchers.")


# ----------------------------------------------------------------------
# Simulate a BadRequestError (content‑policy violation)
# ----------------------------------------------------------------------
def test_bad_request_error(dummy_condition):
    st.session_state["messages"].append({"role": "user", "content": "Hello"})

    with mock.patch(
        "app.client.chat.completions.create",
        side_effect=BadRequestError("Content policy violation"),
    ):
        response, user_turns = app.generate_reply(dummy_condition)

    assert response is None
    assert user_turns == 1
    assert st.session_state["messages"] == []
    st.error.assert_called_once_with(
        "Error. Possible content policy violation. "
        "Please modify your prompt and retry. "
        "Contact the researchers if the issue persists."
    )