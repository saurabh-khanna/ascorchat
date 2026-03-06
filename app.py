# =============================================================================
#  surveychat - A/B Testing Chatbot Platform for Research
# =============================================================================
#
#  PURPOSE
#  -------
#  surveychat lets you run A/B (or multi-arm) conversational experiments.
#  Each incoming participant is randomly assigned to one of N chatbot
#  "conditions", where each condition is defined by a unique system prompt
#  and model choice.  When N = 1 there is no randomization - every
#  participant sees the same chatbot, making it suitable for simple surveys.
#
#  QUICK START
#  -----------
#  1. Edit the RESEARCHER CONFIGURATION section below (clearly marked).
#  2. Add your OPENAI_API_KEY to the .env file (see .env for format).
#  3. Run:   streamlit run app.py
#
#  FORKING & REUSE
#  ---------------
#  This file is intentionally self-contained.  The only section you need
#  to touch for most studies is the RESEARCHER CONFIGURATION block below.
#  Everything else (session management, participant routing, UI) is handled
#  for you automatically.
#
# =============================================================================


# ── Standard library ──────────────────────────────────────────────────────────
import json
import os
import random
from datetime import datetime, timezone

# ── Third-party ───────────────────────────────────────────────────────────────
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv          # reads .env into os.environ automatically

# Load the .env file so that OPENAI_API_KEY is available via os.environ
# even when the app is run without pre-exporting it in the shell.
load_dotenv()


# ╔═════════════════════════════════════════════════════════════════════════════╗
# ║  ✏️  RESEARCHER CONFIGURATION - edit this section to set up your study    ║
# ╚═════════════════════════════════════════════════════════════════════════════╝

# ── LLM API settings ──────────────────────────────────────────────────────────
#
#  API_BASE_URL  The base URL for your LLM API endpoint.
#                - Azure LiteLLM proxy (default):
#                    "https://ai-research-proxy.azurewebsites.net"
#                - Standard OpenAI endpoint:
#                    "https://api.openai.com/v1"
#                - OpenRouter:
#                    "https://openrouter.ai/api/v1"
#
#  The API key is read from OPENAI_API_KEY in the .env file - do not paste
#  keys directly here.
API_BASE_URL = "https://ai-research-proxy.azurewebsites.net"

# ── How many chatbot conditions does your study have? ─────────────────────────
#
#   N_CONDITIONS = 1   →  Single condition (no randomization). Useful when you
#                          just want a plain survey chatbot for all participants.
#   N_CONDITIONS = 2   →  Classic A/B test.  Participants split ~50 / 50.
#   N_CONDITIONS = 3+  →  Multi-arm experiment.  Participants split evenly.
#
#   Default: 2
N_CONDITIONS = 2

# ── Define each chatbot condition ─────────────────────────────────────────────
#
#  Add one dictionary per condition.  You MUST have at least N_CONDITIONS
#  entries.  Any extra entries beyond N_CONDITIONS are ignored.
#
#  Keys per condition
#  ------------------
#  "name"           Short internal label (shown in the debug subtitle).
#  "key"            Session code that routes participants to this condition.
#                   Required when N > 1; assign one unique code per condition
#                   and give each code to Qualtrics so it can display the right
#                   one to each participant before the chat starts.
#                   Case-insensitive.  Omit (or leave out) when N = 1.
#  "system_prompt"  The hidden instruction sent to the model before the
#                   conversation starts.  Participants never see this text, but
#                   it shapes the entire personality and behavior of the chatbot.
#  "model"          The model name for this condition.
#                   Common options: "gpt-oss-120b", "gpt4o", "gpt4o-mini"
#
#  Tip: Write system prompts that clearly differ between conditions so your
#  experimental manipulation is strong and easy to detect in your data.
#  Tip: Use short, neutral codes ("ALPHA"/"BETA", colours, animals, etc.)
#  that give no hint of the condition's content.

CONDITIONS = [

    # ── Condition A ───────────────────────────────────────────────────────────
    {
        "name":          "Condition A - Neutral",
        "key":           "ALPHA",      # session code → routes to this condition
        "system_prompt": (
            "You are a helpful and neutral research assistant. "
            "Answer all questions clearly and concisely without expressing "
            "personal opinions or emotional reactions."
        ),
        "model": "gpt-oss-120b",
    },

    # ── Condition B ───────────────────────────────────────────────────────────
    {
        "name":          "Condition B - Empathetic",
        "key":           "BETA",       # session code → routes to this condition
        "system_prompt": (
            "You are a warm and empathetic research assistant. "
            "Acknowledge the user's perspective and respond with care, "
            "understanding, and emotional sensitivity."
        ),
        "model": "gpt-oss-120b",
    },

    # ── Add more conditions below by copying the block above ─────────────────
    # {
    #     "name":          "Condition C - Directive",
    #     "key":           "GAMMA",
    #     "system_prompt": (
    #         "You are a direct and assertive research assistant. "
    #         "Give clear, action-oriented guidance without hedging."
    #     ),
    #     "model": "gpt-oss-120b",
    # },

]

# ── Study title (shown in the browser tab and as the page heading) ────────────
STUDY_TITLE = "surveychat"

# ── Welcome / instruction message shown above the chat input ─────────────────
#
#   Leave as an empty string "" for no message (default).
#   Set to a sentence or short paragraph to orient participants before they
#   start chatting - useful for informed consent reminders, task instructions,
#   or framing the conversation topic.
#
#   Example:
#       WELCOME_MESSAGE = (
#           "Welcome. In this part of the study you will have a short "
#           "conversation with an AI assistant about climate change. "
#           "When you are done, click the End button to receive your transcript."
#       )
WELCOME_MESSAGE = ""

# ── Prompt shown on the session-code entry screen (keyword routing only) ─────
#
#   Displayed above the code text box when N > 1 and all conditions define a
#   "key".  Ignored when N = 1.
KEY_ENTRY_PROMPT = (
    "Please enter the session code you received in the survey to begin."
)

# ── Debug mode ────────────────────────────────────────────────────────────────
#
#   DEBUG_MODE = True   →  A subtitle under the app title shows which condition
#                          this participant was assigned to.  Useful when testing
#                          that randomization and system prompts are working.
#   DEBUG_MODE = False  →  No subtitle is shown.  Use this for real surveys so
#                          participants cannot see the condition label.
DEBUG_MODE = True

# ╔═════════════════════════════════════════════════════════════════════════════╗
# ║  END OF RESEARCHER CONFIGURATION - no edits needed below this line        ║
# ╚═════════════════════════════════════════════════════════════════════════════╝


# =============================================================================
#  PAGE & STYLE SETUP
# =============================================================================

st.set_page_config(
    page_title=STUDY_TITLE,
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Clean, minimal stylesheet — accent colors kept in sync with config.toml.
# Streamlit applies theme colors through its own CSS-in-JS system and does
# not inject them as CSS custom properties, so we hardcode the same values
# here.  If you change the palette in config.toml, update the variables
# below to match.
#
#   PRIMARY   = #5C6C79   (primaryColor)
#   TEXT      = #1F2429   (textColor)
#   BG_SEC    = #EFF1F3   (secondaryBackgroundColor)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="collapsedControl"] { display: none; }

/* Page layout */
.block-container { max-width: 740px; padding-top: 2.25rem; padding-bottom: 1rem; }

/* Transcript code block - wrap long lines on narrow screens */
.stCode pre { white-space: pre-wrap; word-break: break-word; }

/* App header */
.app-header {
    border-bottom: 2px solid #5C6C79;
    padding-bottom: 0.65rem;
    margin-bottom: 1.5rem;
}
.app-title {
    font-size: 1.35rem;
    font-weight: 600;
    color: #1F2429;
    letter-spacing: -0.4px;
    margin: 0;
}
.app-subtitle {
    font-size: 0.8rem;
    color: #9ca3af;
    margin-top: 0.2rem;
}

/* Welcome / instruction banner */
.welcome-banner {
    background: #EFF1F3;
    border-left: 4px solid #5C6C79;
    border-radius: 0 6px 6px 0;
    padding: 0.75rem 1rem;
    font-size: 0.9rem;
    color: #1F2429;
    margin-bottom: 1.25rem;
    line-height: 1.55;
}

/* Transcript panel */
.transcript-banner {
    background: #EFF1F3;
    border: 1px solid #e5e7eb;
    border-left: 4px solid #5C6C79;
    border-radius: 0 8px 8px 0;
    padding: 0.8rem 1.1rem;
    font-size: 0.85rem;
    color: #1F2429;
    margin-bottom: 1.25rem;
}
</style>
""", unsafe_allow_html=True)


# =============================================================================
#  ENVIRONMENT & CONFIGURATION VALIDATION
# =============================================================================

# Read the OpenAI API key from the environment (populated from .env above).
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Fail fast with a clear, actionable error if the API key is missing or blank.
if not OPENAI_API_KEY or not OPENAI_API_KEY.strip():
    st.error(
        "**OPENAI_API_KEY not found or empty.**  "
        "Please add it to your `.env` file and restart the app.\n\n"
        "Example `.env`:\n```\nOPENAI_API_KEY=sk-...\n```"
    )
    st.stop()

# Validate researcher configuration - surfaces common setup mistakes early.
if N_CONDITIONS < 1:
    st.error(
        "`N_CONDITIONS` must be at least **1**. "
        "Please update the Researcher Configuration section."
    )
    st.stop()

if len(CONDITIONS) < N_CONDITIONS:
    st.error(
        f"`CONDITIONS` list has **{len(CONDITIONS)}** "
        f"entr{'y' if len(CONDITIONS) == 1 else 'ies'}, "
        f"but `N_CONDITIONS` is set to **{N_CONDITIONS}**. "
        "Please add more condition definitions or reduce `N_CONDITIONS`."
    )
    st.stop()

# Validate keyword-routing configuration when N > 1.
if N_CONDITIONS > 1:
    _active = CONDITIONS[:N_CONDITIONS]
    _keyed  = [c for c in _active if "key" in c]
    if 0 < len(_keyed) < N_CONDITIONS:
        st.error(
            f"Keyword routing is partially configured: **{len(_keyed)}** of "
            f"**{N_CONDITIONS}** active conditions have a `\"key\"` field. "
            "Either add a `\"key\"` to every condition or remove them all."
        )
        st.stop()
    if len(_keyed) == N_CONDITIONS:
        if any(not c["key"].strip() for c in _active):
            st.error(
                "One or more condition `\"key\"` values are empty strings. "
                "Every session code must contain at least one character."
            )
            st.stop()
        _keys = [c["key"].strip().lower() for c in _active]
        if len(_keys) != len(set(_keys)):
            st.error(
                "Two or more conditions share the same `\"key\"` value. "
                "Every condition must have a unique session code."
            )
            st.stop()


# =============================================================================
#  SESSION STATE INITIALIZATION
# =============================================================================
#
#  Streamlit re-runs the entire script on every user interaction, so we
#  store anything that must persist across reruns in `st.session_state`.
#  Each `if … not in st.session_state` guard ensures values are set only
#  once per browser session - i.e. once per participant visit.

# Routing mode:
#   keyword routing  →  N > 1 and every active condition defines a "key" field.
#                       Participants enter a session code; same code = same arm,
#                       so the condition is stable across page refreshes.
#   random routing   →  N = 1 (always condition 0) or no keys defined.
#                       Condition is drawn at random on each new session.
_key_routing = N_CONDITIONS > 1 and all(
    "key" in CONDITIONS[i] for i in range(N_CONDITIONS)
)

# For random/single-condition routing, assign now.
# For keyword routing, defer until the participant enters their code.
if not _key_routing and "condition_index" not in st.session_state:
    st.session_state["condition_index"] = (
        0 if N_CONDITIONS == 1 else random.randint(0, N_CONDITIONS - 1)
    )

# Tracks whether the session-code gate has been passed.
# Starts True when no gate is needed (random/single routing).
if "key_accepted" not in st.session_state:
    st.session_state["key_accepted"] = not _key_routing

# Track whether the participant has ended the chat session.
# Once True, the chat input is hidden and the transcript panel is shown.
if "chat_ended" not in st.session_state:
    st.session_state["chat_ended"] = False

# Two-step end confirmation: first click arms it, second confirms.
# Prevents accidental loss of the conversation.
if "confirm_end" not in st.session_state:
    st.session_state["confirm_end"] = False

# Flipped to True as soon as the user sends their very first message.
# Used to reveal the End button immediately after the first turn.
if "has_sent_message" not in st.session_state:
    st.session_state["has_sent_message"] = False

# Initialize an empty conversation history on first load.
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Create and cache the OpenAI client as a global singleton.
# @st.cache_resource is the correct Streamlit pattern for connection-like
# objects: it is created once, shared across all reruns and sessions,
# and never serialized to disk.
@st.cache_resource
def get_client(api_key: str, base_url: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url)

client = get_client(OPENAI_API_KEY, API_BASE_URL)


# =============================================================================
#  MAIN CHAT INTERFACE
# =============================================================================

# ── Header ───────────────────────────────────────────────────────────────────────
if DEBUG_MODE:
    if "condition_index" in st.session_state:
        _debug_label = CONDITIONS[st.session_state["condition_index"]]["name"]
    elif _key_routing:
        _debug_label = "awaiting session code…"
    else:
        _debug_label = ""
    subtitle_html = (
        f'<div class="app-subtitle">Testing: {_debug_label}</div>'
        if _debug_label else ""
    )
else:
    subtitle_html = ""

st.markdown(
    f'<div class="app-header">'
    f'<div class="app-title">💬 {STUDY_TITLE}</div>'
    f'{subtitle_html}'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Session code entry (keyword routing only) ────────────────────────────────────
# Shown before the chat until the participant enters a valid code.
# On page refresh the gate reappears, but the same code always maps to the same
# condition, so the arm is stable - unlike random routing where refresh re-draws.
if not st.session_state["key_accepted"]:
    _key_map = {
        CONDITIONS[i]["key"].strip().lower(): i
        for i in range(N_CONDITIONS)
    }
    if WELCOME_MESSAGE:
        st.markdown(
            f'<div class="welcome-banner">{WELCOME_MESSAGE}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<p style="margin-bottom:1rem;font-size:0.95rem;color:#1F2429">'
        f'{KEY_ENTRY_PROMPT}</p>',
        unsafe_allow_html=True,
    )
    with st.form("key_form"):
        _code = st.text_input("Session code", placeholder="e.g. ALPHA")
        _submitted = st.form_submit_button("Continue →", type="primary")
    if _submitted:
        _idx = _key_map.get(_code.strip().lower())
        if _idx is not None:
            st.session_state["condition_index"] = _idx
            st.session_state["key_accepted"] = True
            st.rerun()
        else:
            st.error("Code not recognised. Please check and try again.")
    st.stop()

# Session code accepted (or not required) — condition is now resolved.
condition = CONDITIONS[st.session_state["condition_index"]]

# ── End Chat button - appears after the first exchange ────────────────────────
# Placed below the header so it does not compete with the title layout.
if not st.session_state["chat_ended"] and st.session_state["has_sent_message"]:
    _, end_col = st.columns([5, 1])
    with end_col:
        if not st.session_state["confirm_end"]:
            if st.button("End", use_container_width=True, type="secondary"):
                st.session_state["confirm_end"] = True
                st.rerun()
        else:
            # Second click required to confirm - prevents accidental endings
            if st.button("✓ Confirm", use_container_width=True, type="primary"):
                st.session_state["chat_ended"] = True
                st.rerun()

# ── Active chat ───────────────────────────────────────────────────────────────
if not st.session_state["chat_ended"]:

    # Optional welcome / instruction message
    if WELCOME_MESSAGE:
        st.markdown(
            f'<div class="welcome-banner">{WELCOME_MESSAGE}</div>',
            unsafe_allow_html=True,
        )

    # Render conversation history
    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input - hidden once chat_ended is True
    if prompt := st.chat_input("Type your message here…"):

        prompt = prompt.strip()
        if not prompt:
            st.stop()

        # Append and immediately display the user's message
        st.session_state["messages"].append({
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        st.session_state["has_sent_message"] = True  # reveal End button from now on
        with st.chat_message("user"):
            st.markdown(prompt)

        # Build the full message list for the API call.
        # The system prompt is prepended at position 0 - participants never see it.
        api_messages = (
            [{"role": "system", "content": condition["system_prompt"]}]
            + [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state["messages"]
            ]
        )

        # Stream the model's response token-by-token for a natural feel
        with st.chat_message("assistant"):
            try:
                stream = client.chat.completions.create(
                    model=condition["model"],
                    messages=api_messages,
                    stream=True,
                )
                response = st.write_stream(stream)
            except Exception as e:
                response = None
                # Remove the user message we just appended — leaving it in
                # history without a paired assistant reply would send two
                # consecutive user turns to the API on the next message.
                st.session_state["messages"].pop()
                st.error(
                    f"**Could not reach the LLM.** "
                    f"Check your `API_BASE_URL` and `OPENAI_API_KEY`.\n\n"
                    f"Error: `{e}`"
                )

        # Save the completed assistant response to history
        if response:
            st.session_state["messages"].append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        # On the very first exchange, force a rerun so the header re-renders
        # and the End button becomes visible immediately.
        if len(st.session_state["messages"]) == 2:
            st.rerun()

# =============================================================================
#  POST-CHAT TRANSCRIPT
# =============================================================================
#
#  Shown after the participant clicks "End".
#  The transcript is a JSON object with one key:
#    - "messages": a list of turns, each with role/content/timestamp
#
#  Parsing in Python:
#      import json, pandas as pd
#      data = json.loads(transcript_string)
#      df   = pd.DataFrame(data["messages"])  # one row per turn
#
#  Parsing in R:
#      library(jsonlite)
#      data <- fromJSON(transcript_string)
#      df   <- as.data.frame(data$messages)   # one row per turn
#
#  Streamlit's st.code() block has a built-in copy button in the top-right
#  corner - one click copies everything to the clipboard.

else:
    st.markdown(
        '<div class="transcript-banner">'
        'Your chat has ended. Copy your transcript below and paste it back into the survey.'
        '</div>',
        unsafe_allow_html=True,
    )

    # Build the transcript object.
    # - Condition name and model are intentionally omitted - participants see
    #   this transcript and must not know which arm they were assigned to.
    #   Treatment assignment is tracked in Qualtrics (via the session code),
    #   not in the transcript itself.
    # - "user" is relabelled "participant" for clarity in the messages array.
    # - Timestamps are UTC ISO-8601 with explicit +00:00 offset, e.g.
    #   "2026-03-06T14:22:01.123456+00:00" - unambiguous across time zones.
    transcript = {
        "messages": [
            {
                "role":      "participant" if m["role"] == "user" else "assistant",
                "content":   m["content"],
                "timestamp": m.get("timestamp", ""),
            }
            for m in st.session_state["messages"]
        ],
    }

    st.code(json.dumps(transcript, indent=2, ensure_ascii=False), language="json")