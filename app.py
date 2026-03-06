# =============================================================================
#  surveychat - Chatbot Surveys and Randomized Experiments
# =============================================================================
#
#  PURPOSE
#  -------
#  surveychat supports two use modes:
#
#  Survey mode  (N_CONDITIONS = 1)
#    Every participant talks to the same chatbot.  No passcodes, no
#    randomization.  Use this for open-ended interviews, cognitive
#    interviewing, pilot testing, or any qualitative data collection that
#    benefits from a conversational format rather than a plain text box.
#    Examples: exploratory interviews, pilot testing, cognitive debriefs,
#    and any study where adaptive follow-up questions driven by participant
#    responses would produce richer data than a fixed question list.
#
#  Experiment mode  (N_CONDITIONS >= 2)
#    Participants are routed to one of N chatbot "conditions", each defined
#    by a unique system prompt and model choice.  Use this for A/B tests or
#    multi-arm studies that compare how different chatbot styles affect
#    participant responses, attitudes, or behaviour.
#    Examples: comparing empathetic vs. neutral interviewers, testing
#    different question orderings, or manipulating response thoroughness.
#
#  In both modes the participant chats, clicks End, and copies a JSON
#  transcript back into the parent survey tool (e.g. Qualtrics).
#
#  TRANSCRIPT FORMAT
#  -----------------
#  After clicking End, the participant receives a JSON block:
#
#      {
#        "messages": [
#          {
#            "role":      "participant",
#            "content":   "Hello!",
#            "timestamp": "2026-03-06T14:22:01.123456+00:00"
#          },
#          {
#            "role":      "assistant",
#            "content":   "Hi there, how can I help you today?",
#            "timestamp": "2026-03-06T14:22:03.456789+00:00"
#          }
#        ]
#      }
#
#  Timestamps are UTC ISO-8601 with an explicit +00:00 offset so they are
#  unambiguous across time zones.  Condition name and model are deliberately
#  excluded so participants cannot infer their assigned arm.
#
#  Parse in Python:
#      import json, pandas as pd
#      data = json.loads(transcript_string)
#      df   = pd.DataFrame(data["messages"])   # one row per turn
#
#  Parse in R:
#      library(jsonlite)
#      data <- fromJSON(transcript_string)
#      df   <- as.data.frame(data$messages)    # one row per turn
#
#  INTEGRATION WITH SURVEY TOOLS
#  ------------------------------
#  Survey mode:
#    (1) Add a Text / Graphic block in Qualtrics with a link to the app.
#    (2) After the chat, add a Text Entry question where participants
#        paste their transcript.
#
#  Experiment mode:
#    (1) Use Qualtrics Survey Flow > Randomizer to split participants.
#    (2) In each arm display the matching passcode and the app URL.
#    (3) After the chat, add a Text Entry question for the transcript.
#    (4) Export responses - treatment assignment is recovered from the
#        passcode stored in the relevant Qualtrics branch variable.
#
#  DEPLOYMENT OPTIONS
#  ------------------
#  Local development:
#      streamlit run app.py
#
#  Streamlit Community Cloud (free, no server needed):
#      Push the repo to GitHub, connect at share.streamlit.io, and add
#      OPENAI_API_KEY under Advanced settings → Secrets.
#
#  Cloud VM (e.g. AWS EC2, DigitalOcean, Azure):
#      pip install -r requirements.txt
#      streamlit run app.py --server.port 80 --server.headless true
#      Serve HTTPS via Caddy or nginx (required for Qualtrics iFrame embeds).
#
#  LLM PROVIDERS
#  -------------
#  Set API_BASE_URL to any OpenAI-compatible endpoint:
#      Standard OpenAI:   https://api.openai.com/v1
#      Azure via LiteLLM: https://your-proxy.azurewebsites.net
#      OpenRouter:        https://openrouter.ai/api/v1
#      Local (LiteLLM):   http://localhost:4000
#
#  QUICK START
#  -----------
#  1. Edit the RESEARCHER CONFIGURATION section below.
#  2. Add your OPENAI_API_KEY to the .env file (see .env.example).
#  3. Run:   streamlit run app.py
#
#  FORKING & REUSE
#  ---------------
#  This file is intentionally self-contained.  The only section you need
#  to edit for most studies is the RESEARCHER CONFIGURATION block below.
#  Everything else - session management, participant routing, transcript
#  export, and the chat UI - is handled for you automatically.
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

# ── Local helpers (pure functions, independently testable) ────────────────────
from helpers import check_passcode_routing, build_api_messages, build_transcript

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
#   N_CONDITIONS = 1   →  Survey mode.  Every participant talks to the same
#                          chatbot.  No passcodes or randomization needed.
#                          The passcode gate screen is suppressed entirely;
#                          participants go straight to the chat.
#                          Use this for structured or semi-structured
#                          interviews, pilot testing, cognitive debriefs, or
#                          any study where a conversation replaces a plain
#                          text-entry question.
#
#   N_CONDITIONS = 2   →  Experiment mode, classic A/B test.
#                          Participants are split ~50 / 50 across two
#                          conditions and enter a passcode to reach their arm.
#
#   N_CONDITIONS = 3+  →  Experiment mode, multi-arm.
#                          Participants are split as evenly as possible across
#                          all conditions.
#
#   Default: 2
N_CONDITIONS = 2

# ── Define each chatbot condition ─────────────────────────────────────────────
#
#  Add one dictionary per condition.  You MUST have at least N_CONDITIONS
#  entries.  Any extra entries beyond N_CONDITIONS are silently ignored.
#
#  Fields per condition
#  --------------------
#  "name"           Short internal label used in log messages and debug info.
#                   Never shown to participants.  Keep it descriptive enough
#                   to identify the condition when reviewing data or logs.
#
#  "passcode"       Passcode that routes participants to this condition.
#                   Only needed in experiment mode (N_CONDITIONS > 1).
#                   Assign one unique passcode per condition and configure
#                   your survey tool to display the correct passcode to each
#                   participant before they open the chat link.
#                   Matching is case-insensitive ("alpha" == "ALPHA").
#                   Omit this field entirely when N_CONDITIONS = 1.
#
#  "system_prompt"  The hidden instruction sent to the model at the very
#                   start of every conversation.  Participants never see
#                   this text, but it defines the chatbot's entire persona,
#                   tone, and behavioral boundaries.
#
#                   In survey mode, treat this as an interviewer brief:
#                   describe the study topic, the interview style, how to
#                   handle off-topic responses, and when to wrap up.
#
#                   In experiment mode, make sure the prompts differ clearly
#                   between conditions so the manipulation is strong and its
#                   effects are detectable in your outcome measures.
#
#  "model"          The model identifier string for this condition.
#                   Common options:
#                     "gpt-oss-120b"  - large open-weights model (default proxy)
#                     "gpt4o"         - GPT-4o via OpenAI or Azure
#                     "gpt4o-mini"    - GPT-4o Mini, faster and cheaper
#                   Different conditions can use different models if you want
#                   to directly compare model-level effects.
#
#  Tips
#  ----
#  - In experiment mode use short, neutral passcodes ("ALPHA"/"BETA",
#    colours, animals) that give participants no hint of their condition.
#  - System prompts work best when they specify tone, task, and limits all
#    at once.  Vague prompts produce inconsistent behavior across sessions.
#  - Test each condition manually before launching the study.
#
#  Survey mode example (N_CONDITIONS = 1, no "passcode" field needed):
#  ─────────────────────────────────────────────────────────────────────
#  CONDITIONS = [
#      {
#          "name":          "Social-media interview bot",
#          "system_prompt": (
#              "You are a friendly research interviewer studying how people "
#              "use social media in their daily lives.  Ask one open-ended "
#              "question at a time, listen carefully, and ask follow-up "
#              "questions to explore the participant's experience in depth. "
#              "After 5-7 exchanges, thank the participant warmly and let "
#              "them know they can click End this chat."
#          ),
#          "model": "gpt-oss-120b",
#      },
#  ]

CONDITIONS = [

    # ── Condition A ───────────────────────────────────────────────────────────
    {
        "name":          "Condition A - Neutral",
        "passcode":      "ALPHA",      # routes participants to this condition
        "system_prompt": (
            "You are a neutral, information-focused research assistant participating "
            "in an academic study. Your role is to respond to the participant's "
            "messages in a clear, balanced, and factual manner. "
            "Do not express personal opinions, take sides, or use emotionally charged "
            "language. Maintain a consistent, professional tone throughout. "
            "If the participant raises a topic that is subjective or contested, "
            "present relevant considerations from multiple perspectives without "
            "endorsing any particular view. "
            "Keep your responses concise but complete - aim for two to four sentences "
            "unless the participant explicitly asks for more detail. "
            "Do not volunteer unsolicited advice or personal anecdotes."
        ),
        "model": "gpt-oss-120b",
    },

    # ── Condition B ───────────────────────────────────────────────────────────
    {
        "name":          "Condition B - Empathetic",
        "passcode":      "BETA",       # routes participants to this condition
        "system_prompt": (
            "You are a warm, empathetic research assistant participating in an "
            "academic study. Your role is to make the participant feel genuinely "
            "heard and understood throughout the conversation. "
            "Begin each response by briefly acknowledging the participant's "
            "feelings or perspective before offering any information or asking "
            "a follow-up question - for example, by reflecting back what they "
            "said or validating their experience without being patronising. "
            "Use a conversational, supportive tone. Avoid clinical or bureaucratic "
            "language. When a participant shares something personal or emotionally "
            "significant, slow down and engage with that before moving on. "
            "Keep your responses concise but warm - aim for two to four sentences "
            "unless the participant explicitly asks for more detail. "
            "Do not minimise, dismiss, or redirect away from anything the "
            "participant seems to find important."
        ),
        "model": "gpt-oss-120b",
    },

    # ── Add more conditions below by copying the block above ─────────────────
    # {
    #     "name":          "Condition C - Socratic",
    #     "passcode":      "GAMMA",
    #     "system_prompt": (
    #         "You are a Socratic research assistant participating in an academic "
    #         "study. Your role is to help the participant think through topics "
    #         "more deeply by asking carefully chosen questions rather than "
    #         "providing answers or information directly. "
    #         "Never volunteer your own opinion, conclusion, or recommendation. "
    #         "Instead, respond to each message by reflecting back what the "
    #         "participant seems to be assuming or implying, then posing one "
    #         "probing question that invites them to examine that assumption, "
    #         "consider a counterexample, or articulate their reasoning more "
    #         "precisely. "
    #         "Questions should be open-ended and genuinely exploratory - not "
    #         "leading questions that hint at a preferred answer. "
    #         "If the participant asks you a direct question, turn it back to them "
    #         "with a question that helps them work toward their own answer. "
    #         "Keep the conversational pressure gentle but persistent: always end "
    #         "your turn with exactly one question, never more. "
    #         "Do not summarise, conclude, or wrap up the conversation - your goal "
    #         "is continued, deepening inquiry."
    #     ),
    #     "model": "gpt-oss-120b",
    # },

]

# ── Study title (shown in the browser tab and as the page heading) ────────────
STUDY_TITLE = "surveychat"

# ── Welcome / instruction message shown above the chat input ─────────────────
#
#   Displayed in a shaded banner at the top of the chat interface.  Use it
#   to orient participants before they start typing.
#
#   Good uses:
#     - Task framing:  "In this part of the study you will discuss your
#       recent online shopping experiences with an AI assistant."
#     - Consent reminder:  "This conversation is recorded as part of a
#       research study and will be stored securely."
#     - Behavioural instruction:  "Please respond as you normally would.
#       There are no right or wrong answers."
#
#   Set to "" to show no banner - useful if your Qualtrics page already
#   provides full instructions before the participant opens the chat link.
#
#   HTML is supported - use <strong>, <em>, <br> etc. for emphasis.
#
#   Examples:
#
#       WELCOME_MESSAGE = ""   # no banner
#
#       WELCOME_MESSAGE = (
#           "Welcome. In this part of the study you will have a short "
#           "conversation with an AI assistant about climate change. "
#           "When you are done, click <strong>End this chat</strong> "
#           "to receive your transcript."
#       )
#
#       WELCOME_MESSAGE = (
#           "This conversation is part of a research study on AI-assisted "
#           "decision-making.  Your responses are confidential and will only "
#           "be used for research purposes.<br><br>"
#           "When finished, click <strong>End this chat</strong> to copy "
#           "your transcript and paste it into the survey."
#       )
WELCOME_MESSAGE = (
    "You are about to have a short conversation with an AI assistant. "
    "When you are finished, click the <strong>End</strong> button to receive your transcript, "
    "then paste it back into the survey."
)

# ── Prompt shown on the passcode entry screen (passcode routing only) ──────
#
#   Displayed above the passcode text box when N > 1 and all conditions define
#   a "passcode".  Ignored when N = 1.
PASSCODE_ENTRY_PROMPT = (
    "Please enter the passcode you received in the survey to begin chatting."
)

# ── Configuration reference ───────────────────────────────────────────────────
#
#  Variable               Default           Description
#  ──────────────────────────────────────────────────────────────────────────────
#  API_BASE_URL           (proxy URL)       Base URL for the LLM API endpoint.
#  N_CONDITIONS           2                 1 = survey mode, 2 = A/B test,
#                                           3+ = multi-arm experiment.
#  CONDITIONS             [A, B]            List of condition dicts.  Each has
#                                           "name", optional "passcode",
#                                           "system_prompt", and "model".
#  STUDY_TITLE            "surveychat"      Browser tab title and page heading.
#  WELCOME_MESSAGE        (default string)  Banner shown above the chat.
#                                           Set to "" to hide.
#  PASSCODE_ENTRY_PROMPT  (default string)  Text above the passcode box.
#                                           Only shown in experiment mode.
#  ──────────────────────────────────────────────────────────────────────────────
#
#  Routing behaviour summary
#  ─────────────────────────
#  N = 1                Survey mode.  No gate, no passcode, direct to chat.
#  N > 1, no passcode   Random routing.  Condition drawn at random on load.
#  N > 1, with passcode Passcode routing.  Same passcode → same condition,
#                       stable across page refreshes.
#
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

# Clean, minimal stylesheet - accent colors kept in sync with config.toml.
# Streamlit renders its own theme via CSS-in-JS and does not expose theme
# values as CSS custom properties, so we hardcode the palette here.
# If you change colors in .streamlit/config.toml, update these too:
#
#   PRIMARY   = #5C6C79   (primaryColor)             - borders, accents
#   TEXT      = #1F2429   (textColor)                - body text
#   BG_SEC    = #EFF1F3   (secondaryBackgroundColor)  - banner backgrounds
st.markdown("""
<style>
/* ── Typography ────────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

/* Apply Inter to the entire app, overriding Streamlit's default font. */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Chrome removal ─────────────────────────────────────────────────────────── */
/* Hide the Streamlit toolbar, footer, and hamburger menu so the page looks
   like a standalone app rather than a Streamlit dashboard. */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="collapsedControl"] { display: none; }

/* ── Page layout ────────────────────────────────────────────────────────────── */
/* Constrain to a readable column width and reduce default top padding. */
.block-container { max-width: 740px; padding-top: 2.25rem; padding-bottom: 1rem; }

/* ── Transcript code block ──────────────────────────────────────────────────── */
/* Wrap long JSON lines so participants on narrow screens can read everything
   without horizontal scrolling. */
.stCode pre { white-space: pre-wrap; word-break: break-word; }

/* ── App header ─────────────────────────────────────────────────────────────── */
/* A thin rule below the study title separates it visually from the chat. */
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

/* ── Welcome / instruction banner ───────────────────────────────────────────── */
/* Shown above the chat input when WELCOME_MESSAGE is non-empty.  The left
   accent border matches the primary color to tie it to the site palette. */
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

/* ── Transcript panel ───────────────────────────────────────────────────────── */
/* Shown after the participant clicks End.  Slightly more prominent border
   than the welcome banner to draw attention to the copy instruction. */
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
        "Please add it to your `.env` file and restart the application.\n\n"
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

# Validate passcode-routing configuration when N > 1.
# check_passcode_routing() is a pure function in helpers.py; any error is
# displayed here so the app halts before any participant-facing UI is shown.
if N_CONDITIONS > 1:
    _ok, _err = check_passcode_routing(CONDITIONS, N_CONDITIONS)
    if not _ok:
        st.error(_err)
        st.stop()


# =============================================================================
#  SESSION STATE INITIALIZATION
# =============================================================================
#
#  Streamlit re-runs the entire script on every user interaction (button
#  click, chat message, page refresh).  Any Python variable assigned during
#  one run is lost on the next.  st.session_state is the mechanism for
#  persisting values across reruns within a single browser session.
#
#  Each `if … not in st.session_state` guard ensures values are initialised
#  exactly once - on the participant's very first page load - and left
#  unchanged on every subsequent rerun.

# ── Determine routing mode ────────────────────────────────────────────────────
#
#  Survey mode      →  N_CONDITIONS = 1.
#                      No routing step.  Condition index is always 0.
#                      Participant goes straight to the chat interface.
#
#  Passcode routing →  N > 1 AND every active condition defines a "passcode".
#                      The passcode entry gate is shown before the chat.
#                      The same passcode always resolves to the same condition
#                      index, so a participant who refreshes the page and
#                      re-enters their passcode lands on the same arm -
#                      without any server-side session storage.
#
#  Random routing   →  N > 1 BUT no conditions define a "passcode".
#                      Condition is drawn uniformly at random on first load.
#                      A page refresh draws a new condition, so this mode is
#                      only appropriate when refresh is unlikely or impossible
#                      (e.g. the survey platform embeds the link once).
_passcode_routing = N_CONDITIONS > 1 and all(
    "passcode" in CONDITIONS[i] for i in range(N_CONDITIONS)
)

# ── Assign condition index ────────────────────────────────────────────────────
#
#  For survey/random routing, assign immediately.
#  For passcode routing, defer until the participant enters their passcode;
#  assignment happens in the passcode-gate block below.
if not _passcode_routing and "condition_index" not in st.session_state:
    st.session_state["condition_index"] = (
        0 if N_CONDITIONS == 1 else random.randint(0, N_CONDITIONS - 1)
    )

# ── Per-session flags ─────────────────────────────────────────────────────────

# Whether the passcode gate has been passed.
# Initialised to True when no gate is needed (survey / random routing).
if "passcode_accepted" not in st.session_state:
    st.session_state["passcode_accepted"] = not _passcode_routing

# Whether the participant has ended the chat session.
# Flips to True when they confirm End; triggers the transcript panel.
if "chat_ended" not in st.session_state:
    st.session_state["chat_ended"] = False

# Two-step end-confirmation flag.
# First click on "End this chat" sets this to True (arming the confirmation).
# Second click on "✓ Confirm" sets chat_ended to True and shows the transcript.
# This prevents accidental chat termination and loss of the conversation.
if "confirm_end" not in st.session_state:
    st.session_state["confirm_end"] = False

# Flipped to True the moment the participant sends their first message.
# The End Chat button is hidden until this is True to avoid showing a useless
# button before any conversation has happened.
if "has_sent_message" not in st.session_state:
    st.session_state["has_sent_message"] = False

# The full conversation history for this session.
# Each item is a dict: {"role": str, "content": str, "timestamp": str}.
# Grows by one entry per user message and one per assistant reply.
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# ── OpenAI client ─────────────────────────────────────────────────────────────

@st.cache_resource
def get_client(api_key: str, base_url: str) -> OpenAI:
    """
    Create and cache a singleton OpenAI client.

    @st.cache_resource creates the object once, shares it across all reruns
    and browser sessions on the same server, and never serialises it to disk.
    This is the correct Streamlit pattern for connection-like objects.

    Parameters
    ----------
    api_key : str
        The API key read from the environment (OPENAI_API_KEY).
    base_url : str
        The API_BASE_URL set in the researcher configuration.

    Returns
    -------
    OpenAI
        A configured OpenAI client instance.
    """
    return OpenAI(api_key=api_key, base_url=base_url)

client = get_client(OPENAI_API_KEY, API_BASE_URL)


# =============================================================================
#  MAIN CHAT INTERFACE
# =============================================================================
#
#  The interface is rendered in a single linear pass from top to bottom.
#  Streamlit's execution model means every widget call below is conditional
#  on session-state flags set during earlier runs; this drives the multi-step
#  participant flow:
#
#  Stage 1 - Passcode gate  (experiment mode with passcode routing only)
#    • Displayed when st.session_state["passcode_accepted"] is False.
#    • A form with a single text input collects the passcode.
#    • Valid entry maps to a condition index, sets passcode_accepted=True,
#      and triggers a full rerun so stage 1 is skipped on subsequent runs.
#    • Invalid entry shows an inline error; the gate remains visible.
#    • st.stop() at the end of stage 1 prevents any subsequent code from
#      running until the gate is passed - the chat UI is never rendered
#      even partially for unauthenticated participants.
#
#  Stage 2 - Active chat
#    • Displayed when chat_ended is False.
#    • The optional welcome banner is rendered first.
#    • All messages in st.session_state["messages"] are replayed in order
#      so the full conversation history is visible on every rerun.
#    • st.chat_input() blocks further execution until the participant sends
#      a message; the user message is appended, then the LLM is called.
#    • The response is streamed token-by-token via st.write_stream() to give
#      a natural, responsive feel even on slow connections.
#    • The End Chat button appears in a right-aligned column after the first
#      exchange.  A two-step confirmation (End → Confirm) prevents
#      participants from accidentally discarding their conversation.
#
#  Stage 3 - Transcript panel
#    • Displayed when chat_ended is True.
#    • The transcript banner and JSON code block are rendered.
#    • Streamlit’s st.code() provides a built-in copy button in the
#      top-right corner of the block, requiring no custom JavaScript.
#    • The participant copies the JSON and pastes it back into Qualtrics
#      (or whichever survey tool they came from).
#
# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="app-header">'
    f'<div class="app-title">💬 {STUDY_TITLE}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Passcode entry (experiment mode with passcode routing only) ─────────────
# Shown before the chat until the participant enters a valid passcode.
# On page refresh the gate reappears, but the same passcode always maps to the
# same condition, so assignment is stable across refreshes.
if not st.session_state["passcode_accepted"]:
    _passcode_map = {
        CONDITIONS[i]["passcode"].strip().lower(): i
        for i in range(N_CONDITIONS)
    }
    if WELCOME_MESSAGE:
        st.markdown(
            f'<div class="welcome-banner">{WELCOME_MESSAGE}</div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<p style="margin-bottom:1rem;font-size:0.95rem;color:#1F2429">'
        f'{PASSCODE_ENTRY_PROMPT}</p>',
        unsafe_allow_html=True,
    )
    with st.form("key_form"):
        _code = st.text_input("Passcode", placeholder="e.g. ALPHA")
        _submitted = st.form_submit_button("Continue →", type="primary")
    if _submitted:
        _idx = _passcode_map.get(_code.strip().lower())
        if _idx is not None:
            st.session_state["condition_index"] = _idx
            st.session_state["passcode_accepted"] = True
            st.rerun()
        else:
            st.error("Code not recognised. Please check and try again.")
    st.stop()

# Passcode accepted (or not required) - condition is now resolved.
condition = CONDITIONS[st.session_state["condition_index"]]

# ── End Chat button - appears after the first exchange ────────────────────────
# Placed below the header so it does not compete with the title layout.
if not st.session_state["chat_ended"] and st.session_state["has_sent_message"]:
    _, end_col = st.columns([5, 1])
    with end_col:
        if not st.session_state["confirm_end"]:
            if st.button("End chat", use_container_width=True, type="secondary"):
                st.session_state["confirm_end"] = True
                st.rerun()
        else:
            # Second click required to confirm - prevents accidental endings
            if st.button("✓ Confirm", use_container_width=True, type="primary"):
                st.session_state["chat_ended"] = True
                st.rerun()

# ── Active chat ───────────────────────────────────────────────────────────────
if not st.session_state["chat_ended"]:

    # Optional welcome / instruction message - hidden once chatting has begun,
    # or immediately if the participant just passed through the passcode gate.
    if WELCOME_MESSAGE and not _passcode_routing and not st.session_state["has_sent_message"]:
        st.markdown(
            f'<div class="welcome-banner">{WELCOME_MESSAGE}</div>',
            unsafe_allow_html=True,
        )

    # Render conversation history.
    # Every message stored in st.session_state["messages"] is displayed on
    # each rerun, giving the participant a full view of the conversation.
    # st.chat_message() renders a colored avatar and indented bubble whose
    # style depends on the role: "user" gets a right-aligned bubble and
    # "assistant" a left-aligned one, matching familiar chat conventions.
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
        st.session_state["has_sent_message"] = True  # reveal End Chat button from now on
        with st.chat_message("user"):
            st.markdown(prompt)

        # Build the full message list for the API call.
        # See build_api_messages() in helpers.py for details.
        api_messages = build_api_messages(
            st.session_state["messages"],
            condition["system_prompt"],
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
                # Remove the user message we just appended - leaving it in
                # history without a paired assistant reply would send two
                # consecutive user turns to the API on the next message.
                if (
                    st.session_state["messages"]
                    and st.session_state["messages"][-1]["role"] == "user"
                ):
                    st.session_state["messages"].pop()

                # Keep this flag consistent with rolled-back history so the
                # End Chat button is not shown when no message remains.
                st.session_state["has_sent_message"] = bool(
                    st.session_state["messages"]
                )
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
        # and the End Chat button becomes visible immediately.
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
        'Your chat has ended. Your transcript is below. '
        'Click the <strong>copy symbol in the top-right corner</strong> of the box, '
        'then paste it back into the survey.'
        '</div>',
        unsafe_allow_html=True,
    )

    # Build and render the transcript.
    # See build_transcript() in helpers.py for design notes on why
    # condition name/model are excluded and how the role label works.
    transcript = build_transcript(st.session_state["messages"])

    st.code(json.dumps(transcript, indent=2, ensure_ascii=False), language="json")


# =============================================================================
#  STUDY DATA HANDLING NOTES  (for researchers)
# =============================================================================
#
#  These notes describe how to process the transcript data collected from
#  participants.  They are for researcher reference only and have no effect
#  on the running application.
#
#  PARSING THE TRANSCRIPT IN PYTHON
#  ---------------------------------
#  import json
#  import pandas as pd
#
#  raw = qualtrics_response_column   # string value from Qualtrics export
#  data = json.loads(raw)
#  df = pd.DataFrame(data["messages"])  # columns: role, content, timestamp
#
#  Useful derived columns:
#    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
#    df["turn"]      = range(len(df))
#    df["words"]     = df["content"].str.split().str.len()
#    df_user         = df[df["role"] == "participant"]
#    df_asst         = df[df["role"] == "assistant"]
#
#  PARSING THE TRANSCRIPT IN R
#  ----------------------------
#  library(jsonlite)
#
#  raw  <- qualtrics_response_column   # character vector from survey export
#  data <- fromJSON(raw)
#  df   <- as.data.frame(data$messages)  # columns: role, content, timestamp
#
#  Useful transformations:
#    df$timestamp <- as.POSIXct(df$timestamp, tz = "UTC", format = "%Y-%m-%dT%H:%M:%OS")
#    df_user <- subset(df, role == "participant")
#    df_asst <- subset(df, role == "assistant")
#
#  CONDITION ASSIGNMENT (EXPERIMENT MODE)
#  ----------------------------------------
#  Condition identity is NOT in the transcript.  Recover it from the survey
#  branching logic:
#    - In passcode routing: store the passcode shown to each participant in
#      a Qualtrics embedded data field.  Map passcode → condition name in R/Python.
#    - In random routing:   store the displayed arm label in an embedded data
#      field in the Qualtrics Survey Flow randomizer branch.
#
#  DATA QUALITY CHECKS
#  --------------------
#  Recommended minimum checks before analysis:
#    1. Verify json.loads() succeeds for every row (malformed pastes).
#    2. Drop sessions with fewer than 2 messages (participant sent nothing).
#    3. Check for unusually short response times (bot detection, inattention).
#    4. Review assistant messages flagged with "Error" (API failures mid-session).
#
# =============================================================================
