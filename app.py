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
import uuid
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
#  "name"           Short internal label (shown in the debug subtitle and transcript).
#  "system_prompt"  The hidden instruction sent to the model before the
#                   conversation starts.  Participants never see this text, but
#                   it shapes the entire personality and behavior of the chatbot.
#  "model"          The model name for this condition.
#                   Common options: "gpt-oss-120b", "gpt4o", "gpt4o-mini"
#
#  Tip: Write system prompts that clearly differ between conditions so your
#  experimental manipulation is strong and easy to detect in your data.

CONDITIONS = [

    # ── Condition A ───────────────────────────────────────────────────────────
    {
        "name": "Condition A - Neutral",
        "system_prompt": (
            "You are a helpful and neutral research assistant. "
            "Answer all questions clearly and concisely without expressing "
            "personal opinions or emotional reactions."
        ),
        "model": "gpt-oss-120b",
    },

    # ── Condition B ───────────────────────────────────────────────────────────
    {
        "name": "Condition B - Empathetic",
        "system_prompt": (
            "You are a warm and empathetic research assistant. "
            "Acknowledge the user's perspective and respond with care, "
            "understanding, and emotional sensitivity."
        ),
        "model": "gpt-oss-120b",
    },

    # ── Add more conditions below by copying the block above ─────────────────
    # {
    #     "name": "Condition C - Directive",
    #     "system_prompt": (
    #         "You are a direct and assertive research assistant. "
    #         "Give clear, action-oriented guidance without hedging."
    #     ),
    #     "model": "gpt-oss-120b",
    # },

]

# ── Study title (shown in the browser tab and as the page heading) ────────────
STUDY_TITLE = "surveychat"

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

# Clean, minimal stylesheet inspired by academic UI conventions.
# Uses Inter for UI chrome and keeps color palette to near-black + greys.
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
    border-bottom: 2px solid #1a1a2e;
    padding-bottom: 0.65rem;
    margin-bottom: 1.5rem;
}
.app-title {
    font-size: 1.35rem;
    font-weight: 600;
    color: #1a1a2e;
    letter-spacing: -0.4px;
    margin: 0;
}
.app-subtitle {
    font-size: 0.8rem;
    color: #9ca3af;
    margin-top: 0.2rem;
}

/* Transcript panel */
.transcript-banner {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-left: 4px solid #1a1a2e;
    border-radius: 0 8px 8px 0;
    padding: 0.8rem 1.1rem;
    font-size: 0.85rem;
    color: #374151;
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


# =============================================================================
#  SESSION STATE INITIALIZATION
# =============================================================================
#
#  Streamlit re-runs the entire script on every user interaction, so we
#  store anything that must persist across reruns in `st.session_state`.
#  Each `if … not in st.session_state` guard ensures values are set only
#  once per browser session - i.e. once per participant visit.

# Assign a short, readable unique participant ID on first load.
if "participant_id" not in st.session_state:
    st.session_state["participant_id"] = str(uuid.uuid4())[:8].upper()

# Randomly assign this participant to one of the N conditions.
# The RNG is seeded with the participant_id so the assignment is fully
# determined by the random ID drawn at session start.  Note: because
# st.session_state is reset on every page refresh (the WebSocket reconnects),
# participant_id is re-drawn on reload and the condition can therefore change
# between page loads.  This is by design - it keeps the implementation simple.
# With N = 1 there is only one option, so no randomization occurs.
if "condition_index" not in st.session_state:
    rng = random.Random(st.session_state["participant_id"])
    st.session_state["condition_index"] = (
        0 if N_CONDITIONS == 1 else rng.randint(0, N_CONDITIONS - 1)
    )

# Retrieve the full condition dictionary for the assigned condition.
condition = CONDITIONS[st.session_state["condition_index"]]

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

# ── Header: title and optional debug subtitle, rendered as one HTML fragment ──
# Note: each st.markdown() call is an independent HTML document fragment in
# Streamlit, so opening/closing <div> tags must be in the same call.
subtitle_html = (
    f'<div class="app-subtitle">Testing: {condition["name"]}</div>'
    if DEBUG_MODE else ""
)
st.markdown(
    f'<div class="app-header">'
    f'<div class="app-title">💬 {STUDY_TITLE}</div>'
    f'{subtitle_html}'
    f'</div>',
    unsafe_allow_html=True,
)

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
#  The transcript is a JSON object with two keys:
#    - "model":    the model used in this session (condition-level treatment)
#    - "messages": a list of turns, each with role/content/timestamp
#
#  Parsing in Python:
#      import json, pandas as pd
#      data  = json.loads(transcript_string)
#      model = data["model"]
#      df    = pd.DataFrame(data["messages"])
#
#  Parsing in R:
#      library(jsonlite)
#      data  <- fromJSON(transcript_string)
#      model <- data$model
#      df    <- as.data.frame(data$messages)
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
    # - "model" is saved at the top level because it is a condition-level
    #   variable (the same model is used for every turn in a session).
    #   In a multi-arm study this is the primary treatment identifier.
    # - "user" is relabelled "participant" for clarity in the messages array.
    # - Timestamps are UTC ISO-8601 with explicit +00:00 offset, e.g.
    #   "2026-03-06T14:22:01.123456+00:00" - unambiguous across time zones.
    transcript = {
        "model": condition["model"],
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