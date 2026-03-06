# =============================================================================
#  abchat — A/B Testing Chatbot Platform for Research
# =============================================================================
#
#  PURPOSE
#  -------
#  abchat lets you run A/B (or multi-arm) conversational experiments.
#  Each incoming participant is randomly assigned to one of N chatbot
#  "conditions", where each condition is defined by a unique system prompt
#  and model choice.  When N = 1 there is no randomization — every
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
import os
import random
import uuid

# ── Third-party ───────────────────────────────────────────────────────────────
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv          # reads .env into os.environ automatically

# Load the .env file so that OPENAI_API_KEY (and optional BASE_URL) are
# available via os.environ even when the app is run without pre-exporting them.
load_dotenv()


# ╔═════════════════════════════════════════════════════════════════════════════╗
# ║  ✏️  RESEARCHER CONFIGURATION — edit this section to set up your study    ║
# ╚═════════════════════════════════════════════════════════════════════════════╝

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
#  "name"           Short internal label (appears in sidebar and transcripts).
#  "system_prompt"  The hidden instruction sent to the model before the
#                   conversation starts.  Participants never see this text, but
#                   it shapes the entire personality and behavior of the chatbot.
#  "model"          The OpenAI model name for this condition.
#                   Common options: "gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"
#
#  Tip: Write system prompts that clearly differ between conditions so your
#  experimental manipulation is strong and easy to detect in your data.

CONDITIONS = [

    # ── Condition A ───────────────────────────────────────────────────────────
    {
        "name": "Condition A — Neutral",
        "system_prompt": (
            "You are a helpful and neutral research assistant. "
            "Answer all questions clearly and concisely without expressing "
            "personal opinions or emotional reactions."
        ),
        "model": "gpt-4o",
    },

    # ── Condition B ───────────────────────────────────────────────────────────
    {
        "name": "Condition B — Empathetic",
        "system_prompt": (
            "You are a warm and empathetic research assistant. "
            "Acknowledge the user's perspective and respond with care, "
            "understanding, and emotional sensitivity."
        ),
        "model": "gpt-4o",
    },

    # ── Add more conditions below by copying the block above ─────────────────
    # {
    #     "name": "Condition C — Directive",
    #     "system_prompt": (
    #         "You are a direct and assertive research assistant. "
    #         "Give clear, action-oriented guidance without hedging."
    #     ),
    #     "model": "gpt-4o",
    # },

]

# ── Study title (shown in the browser tab and as the page heading) ────────────
STUDY_TITLE = "abchat"

# ╔═════════════════════════════════════════════════════════════════════════════╗
# ║  END OF RESEARCHER CONFIGURATION — no edits needed below this line        ║
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

# Hide Streamlit's default chrome (menu, footer, header, sidebar toggle)
# for a clean, distraction-free research interface.
st.markdown(
    """
    <style>
    #MainMenu                        { visibility: hidden; }
    footer                           { visibility: hidden; }
    header                           { visibility: hidden; }
    [data-testid="collapsedControl"] { display: none; }

    /* Widen and center the chat area */
    .block-container { max-width: 760px; padding-top: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
#  ENVIRONMENT & CONFIGURATION VALIDATION
# =============================================================================

# Read the OpenAI API key from the environment (populated from .env above).
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Optional: if you route requests through a custom API proxy (e.g. an Azure
# Function that forwards to OpenAI), set BASE_URL in your .env file.
# Leave it unset or blank to use the standard OpenAI endpoint.
BASE_URL = os.environ.get("BASE_URL") or None

# Fail fast with a clear, actionable error if the API key is missing.
if not OPENAI_API_KEY:
    st.error(
        "**OPENAI_API_KEY not found.**  "
        "Please add it to your `.env` file and restart the app.\n\n"
        "Example `.env`:\n```\nOPENAI_API_KEY=sk-...\n```"
    )
    st.stop()

# Validate researcher configuration — surfaces common setup mistakes early.
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
#  once per browser session — i.e. once per participant visit.

# Assign a short, readable unique participant ID on first load.
if "participant_id" not in st.session_state:
    st.session_state["participant_id"] = str(uuid.uuid4())[:8].upper()

# Randomly assign this participant to one of the N conditions.
# With N = 1 there is only one option, so no randomization occurs.
if "condition_index" not in st.session_state:
    st.session_state["condition_index"] = (
        0 if N_CONDITIONS == 1 else random.randint(0, N_CONDITIONS - 1)
    )

# Retrieve the full condition dictionary for the assigned condition.
condition = CONDITIONS[st.session_state["condition_index"]]

# Initialize an empty conversation history on first load.
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Create the OpenAI client once and store it so it survives reruns.
if "client" not in st.session_state:
    st.session_state["client"] = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=BASE_URL,      # None → standard api.openai.com endpoint
    )


# =============================================================================
#  MAIN CHAT INTERFACE
# =============================================================================

# Minimal header: app name + participant ID on one line
st.title(f"💬 {STUDY_TITLE}")
st.caption(f"Participant ID: `{st.session_state['participant_id']}`")

# Render every message already in the conversation history
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input — Streamlit waits here for the participant to type and submit
if prompt := st.chat_input("Type your message here…"):

    prompt = prompt.strip()
    if not prompt:
        st.stop()

    # Append and immediately display the user's message
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build the full message list for the API call.
    # The system prompt is prepended at position 0 — participants never see it.
    api_messages = (
        [{"role": "system", "content": condition["system_prompt"]}]
        + [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state["messages"]
        ]
    )

    # Stream the model's response token-by-token for a natural feel
    with st.chat_message("assistant"):
        stream = st.session_state["client"].chat.completions.create(
            model=condition["model"],
            messages=api_messages,
            stream=True,
        )
        response = st.write_stream(stream)

    # Save the completed assistant response to history
    st.session_state["messages"].append({"role": "assistant", "content": response})