"""
helpers.py - Pure helper functions for surveychat.

These functions contain all business logic that does not depend on
Streamlit, making them independently importable and fully testable.
app.py imports and calls them; app.py owns the Streamlit error-display
and session-state concerns.
"""


def check_passcode_routing(conditions: list, n_conditions: int) -> tuple[bool, str]:
    """
    Validate the passcode-routing configuration and return a result tuple.

    Returns
    -------
    (True, "")         Configuration is valid.
    (False, message)   Configuration is invalid; message explains the problem.

    Enforces four invariants:
      0. n_conditions must be >= 1 and <= len(conditions).
      1. If any active condition defines a "passcode" field, every active
         condition must define one (no partial configuration).
      2. Every passcode value must be a non-empty string after stripping
         leading/trailing whitespace.
      3. All passcodes must be unique when compared case-insensitively.
    """
    if n_conditions < 1:
        return False, (
            "`n_conditions` must be at least **1**. "
            "Set it to 1 for survey mode or 2+ for experiments."
        )

    if len(conditions) < n_conditions:
        return False, (
            f"`conditions` contains **{len(conditions)}** entr"
            f"{'y' if len(conditions) == 1 else 'ies'}, "
            f"but `n_conditions` is **{n_conditions}**."
        )

    active = conditions[:n_conditions]

    for i, condition in enumerate(active, start=1):
        if not isinstance(condition, dict):
            return False, (
                f"Condition #{i} is not a dictionary. "
                "Each condition must be a dict with study settings."
            )

    passcoded = [c for c in active if "passcode" in c]

    # Invariant 1: Partial configuration.
    if 0 < len(passcoded) < n_conditions:
        return False, (
            f"Passcode routing is partially configured: **{len(passcoded)}** of "
            f"**{n_conditions}** active conditions have a `\"passcode\"` field. "
            "Either add a `\"passcode\"` to every condition or remove them all."
        )

    if len(passcoded) == n_conditions:
        passcodes = []
        for condition in active:
            # Invariant 2: Every passcode must be a non-empty string.
            raw_passcode = condition["passcode"]
            if not isinstance(raw_passcode, str):
                return False, (
                    "One or more condition `\"passcode\"` values are not strings. "
                    "Every passcode must be a non-empty string."
                )

            passcode = raw_passcode.strip()
            if not passcode:
                return False, (
                    "One or more condition `\"passcode\"` values are empty strings. "
                    "Every passcode must contain at least one character."
                )

            passcodes.append(passcode.lower())

        # Invariant 3: All passcodes must be unique (case-insensitive).
        if len(passcodes) != len(set(passcodes)):
            return False, (
                "Two or more conditions share the same `\"passcode\"` value. "
                "Every condition must have a unique passcode."
            )

    return True, ""


def build_api_messages(conversation: list, system_prompt: str) -> list:
    """
    Construct the message list to send to the LLM API for a single turn.

    The system prompt is inserted as a {"role": "system"} message at
    position 0.  Only "role" and "content" are forwarded from the
    conversation history; the "timestamp" key is local-only metadata that
    the OpenAI API does not accept.

    Parameters
    ----------
    conversation : list[dict]
        Each element has "role", "content", and optionally "timestamp" keys.
    system_prompt : str
        The hidden system prompt from the active condition.

    Returns
    -------
    list[dict]
        A list of {"role": str, "content": str} dicts ready for the
        OpenAI chat completions endpoint.
    """
    return (
        [{"role": "system", "content": system_prompt}]
        + [
            {"role": m["role"], "content": m["content"]}
            for m in conversation
        ]
    )


def build_transcript(messages: list) -> dict:
    """
    Format the conversation history as the transcript object shown after the
    chat ends.

    Returns a JSON-serialisable dict with a single "messages" key.  Each
    entry carries "role" ("participant" or "assistant"), "content", and
    "timestamp".  The "user" role is relabelled "participant" so researchers
    get a domain-appropriate label when parsing in Python or R.

    Parameters
    ----------
    messages : list[dict]
        Each element has "role", "content", and optionally "timestamp" keys.

    Returns
    -------
    dict
        Transcript object suitable for json.dumps(indent=2, ensure_ascii=False).
    """
    return {
        "messages": [
            {
                "role":      "participant" if m["role"] == "user" else "assistant",
                "content":   m["content"],
                "timestamp": m.get("timestamp", ""),
            }
            for m in messages
        ],
    }
