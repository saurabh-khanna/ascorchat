# 💬 surveychat - Chatbot Platform for Research

surveychat is a minimal, self-contained web application for running chatbot surveys or experiments. Each participant is randomly assigned to one of N chatbot *conditions* (different system prompts / models). N = 1 enables survey mode with no randomization. At the end of the conversation, the participant receives a JSON transcript to copy and paste back into your survey (e.g. Qualtrics).

Built for researchers who want to study how chatbot style, tone, or framing affects user responses - with zero backend infrastructure. Can be deployed locally or online.

---

## Table of contents

1. [What it does](#what-it-does)
2. [Prerequisites](#prerequisites)
3. [Quick start](#quick-start)
4. [Configuring your study](#configuring-your-study)
5. [Research design ideas](#research-design-ideas)
6. [Testing your conditions before launch](#testing-your-conditions-before-launch)
7. [Participant flow](#participant-flow)
8. [Collecting transcripts](#collecting-transcripts)
9. [Integrating with Qualtrics](#integrating-with-qualtrics)
10. [Deploying for a real study](#deploying-for-a-real-study)
11. [Project structure](#project-structure)
12. [Troubleshooting](#troubleshooting)

---

## What it does

| Feature | Detail |
|---|---|
| **Condition assignment** | When N > 1, participants enter a short session code (given to them by Qualtrics) which maps to their assigned condition. The same code always routes to the same arm, so refreshes are safe. N = 1 skips the code screen entirely. |
| **Streaming responses** | LLM replies appear token-by-token for a natural chat feel |
| **End Chat + transcript** | A participant-facing "End" button (two-click confirmation) reveals a copyable JSON transcript |
| **Debug mode** | Toggle `DEBUG_MODE = True` while testing to confirm which condition is active |
| **No database** | Nothing is written to disk or sent to a database - all state is held in the server session |
| **Welcome message** | Optional instruction text shown above the chat, configurable per deployment |

---

## Prerequisites

### 1. Python 3.10 or later

```bash
python3 --version
```

If Python is not installed, download it from [python.org](https://www.python.org/downloads/).

### 2. An OpenAI-compatible API key

surveychat works with any API endpoint that follows the OpenAI SDK format:

| Provider | `API_BASE_URL` to use |
|---|---|
| Azure LiteLLM proxy (ASCoR default) | `https://ai-research-proxy.azurewebsites.net` |
| OpenAI directly | `https://api.openai.com/v1` |
| OpenRouter | `https://openrouter.ai/api/v1` |

> If you are at ASCoR (University of Amsterdam), request an API key from your lab coordinator.

---

## Quick start

### Step 1 - Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/surveychat.git
cd surveychat
```

Replace `YOUR_USERNAME` with your GitHub username (or organisation name).

### Step 2 - Create a virtual environment and install dependencies

**Using pip (recommended for most users):**

```bash
python3 -m venv .venv
source .venv/bin/activate        # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Using conda:**

```bash
conda create -n surveychat python=3.12 -y
conda activate surveychat
pip install -r requirements.txt
```

### Step 3 - Add your API key

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder:

```dotenv
OPENAI_API_KEY=your-actual-api-key-here
```

> `.env` is listed in `.gitignore` - your key will never be committed to GitHub.

### Step 4 - Run the app

```bash
streamlit run app.py
```

A browser tab opens at `http://localhost:8501`.

---

## Configuring your study

All researcher-facing settings are at the top of `app.py`, clearly marked with a `✏️ RESEARCHER CONFIGURATION` banner. **You should not need to edit anything else.**

### Number of conditions

```python
N_CONDITIONS = 2   # 1 = no randomization, 2 = A/B, 3+ = multi-arm
```

### Defining chatbot conditions

Each condition is a dictionary with four keys:

```python
CONDITIONS = [
    {
        "name":          "Condition A - Neutral",  # internal label, never shown to participants
        "key":           "ALPHA",                  # session code → routes here (N > 1 only)
        "system_prompt": (
            "You are a helpful and neutral research assistant. "
            "Answer all questions clearly and concisely without expressing "
            "personal opinions or emotional reactions."
        ),
        "model": "gpt-oss-120b",
    },
    {
        "name":          "Condition B - Empathetic",
        "key":           "BETA",
        "system_prompt": (
            "You are a warm and empathetic research assistant. "
            "Acknowledge the user's perspective and respond with care, "
            "understanding, and emotional sensitivity."
        ),
        "model": "gpt-oss-120b",
    },
]
```

**Tips for writing system prompts:**
- Be explicit and specific - vague prompts produce inconsistent behavior
- Pilot test each condition yourself before launching (`DEBUG_MODE = True` shows which condition you are in)
- Make the manipulation strong enough to detect in your data

**Tips for choosing session codes:**
- Use short, neutral words that give no hint of the condition content (`ALPHA`/`BETA`, colours, numbers)
- Codes are case-insensitive - participants can type in any case
- Qualtrics should display the code prominently before the chat link, e.g. *"Your session code is: ALPHA"*

### API endpoint

```python
API_BASE_URL = "https://ai-research-proxy.azurewebsites.net"
```

Change this if you switch providers. Available model names depend on your endpoint.

### Study title

```python
STUDY_TITLE = "surveychat"   # shown in browser tab and as the page heading
```

### Session code prompt

```python
KEY_ENTRY_PROMPT = "Please enter the session code you received in the survey to begin."
```

The instruction shown above the code text box on the entry screen. Ignored when `N_CONDITIONS = 1`.

### Welcome message

```python
WELCOME_MESSAGE = ""   # leave empty for no message
```

An optional instruction shown above the chat input for the duration of the conversation. Use this to give participants task instructions, framing, or a brief informed-consent reminder without needing a separate Qualtrics page:

```python
WELCOME_MESSAGE = (
    "Welcome. In this part of the study you will have a short conversation "
    "with an AI assistant about climate change. "
    "When you are done, click the End button to receive your transcript."
)
```

### Debug mode

```python
DEBUG_MODE = True    # shows assigned condition under the title - use while testing
DEBUG_MODE = False   # hides condition label - use for real data collection
```

---

## Research design ideas

### Simple chatbot surveys (N = 1)

Set `N_CONDITIONS = 1` when you just want all participants to talk to the same chatbot - no randomization, no arms. This turns surveychat into a straightforward open-ended survey instrument. Useful for:

- Pilot interviews or qualitative pre-studies
- Collecting open-ended responses at scale with conversational follow-up probing
- Any study where the chatbot itself is not the manipulation

### Mixing chatbot arms with Qualtrics arms

The recommended approach when Qualtrics already assigns participants to arms: use **session code routing**. Each condition has a short code; Qualtrics shows each participant the code for their arm before they open the chat. surveychat reads the code and routes deterministically.

Workflow:
1. Qualtrics randomizes participants between Arm A and Arm B as usual
2. The Arm A branch displays: *"Your session code is: ALPHA"*
3. The Arm B branch displays: *"Your session code is: BETA"*
4. The participant opens surveychat, enters their code, and is routed to the correct condition

Benefits over the old approach (separate N=1 deployments per arm):
- Single surveychat deployment to maintain
- Condition assignment stays entirely in Qualtrics — surveychat just follows instructions
- Refresh-safe: re-entering the same code always returns the same arm
- No risk of participants ending up in a different arm if they accidentally refresh

If you prefer separate deployments, that still works — set `N_CONDITIONS = 1` per instance and omit the `"key"` field.

### Varying the model, not just the prompt

Each condition can point to a different model:

```python
CONDITIONS = [
    {"name": "GPT-4o",      "system_prompt": "...", "model": "gpt-4o"},
    {"name": "GPT-4o-mini", "system_prompt": "...", "model": "gpt-4o-mini"},
]
```

This lets you study effects of model capability or response style independently of the system prompt, or run cost-sensitivity comparisons between arms.

### Keeping the manipulation subtle

The `name` field in each condition is only visible in debug mode - participants never see it. You can therefore use identical-seeming interfaces with only the system prompt differing, which is useful when you want to avoid demand characteristics or hypothesis guessing.

### Using the transcript `model` field as your treatment variable

The JSON transcript always records which model generated the responses. In your Qualtrics export, the `model` value acts as a ready-made treatment indicator - no need to merge a separate randomization file. If all your conditions share the same model, set distinct model names per condition (even if pointing to the same underlying API endpoint) so they remain distinguishable in the data.

---

## Testing your conditions before launch

**How routing works:**
- **N = 1**: Condition 0 assigned automatically — no code screen, no randomization.
- **N > 1 with session codes** (recommended): Participant enters a code → routed to matching arm. Same code always returns same arm; page refreshes are safe.
- **N > 1 without session codes** (fallback): Condition drawn randomly at session start. Refreshing may change the arm.

To test each arm:

| What you want | How to do it |
|---|---|
| Test a specific arm | Enter that arm's session code on the code screen |
| Confirm which arm you are in | Set `DEBUG_MODE = True` — the condition name appears under the title |
| Verify refresh stability | Refresh the page and re-enter the same code — you should land in the same condition |
| Test each arm quickly | Open a separate tab per arm and enter a different code in each |

A good pre-launch checklist:
1. Set `DEBUG_MODE = True`
2. Enter each session code in a separate tab and verify the chatbot behaves correctly for that condition
3. Confirm the code screen shows your `KEY_ENTRY_PROMPT` text
4. Try entering a wrong code and confirm the error message appears
5. Set `DEBUG_MODE = False` before sharing the link with participants

---

## Participant flow

```
Participant opens link
        │
        ▼
[N > 1 with session codes]            [N = 1]
Code entry screen                      │
        │ (valid code entered)          │
        ▼                              │
Condition assigned by code ◄───────────┘
        │
        ▼
Chat interface appears
        │
        ▼ (after first message)
"End" button appears in top-right
        │
        ▼ (two-click confirmation)
Transcript panel appears
        │
        ▼
Participant copies JSON → pastes into Qualtrics
```

---

## Collecting transcripts

Participants copy a JSON block at the end of the chat and paste it into a "Text entry" question in your survey.

### Transcript format

```json
{
  "model": "gpt-oss-120b",
  "messages": [
    {
      "role": "participant",
      "content": "Hello, I have a question about climate change.",
      "timestamp": "2026-03-06T14:22:01.123456+00:00"
    },
    {
      "role": "assistant",
      "content": "Of course! What would you like to know?",
      "timestamp": "2026-03-06T14:22:03.456789+00:00"
    }
  ]
}
```

- `model` is the condition-level treatment identifier - the model that generated all assistant turns in this session
- `role` is `"participant"` or `"assistant"` - never `"system"`
- `timestamp` is always UTC with an explicit `+00:00` offset, safe across time zones

> **Note:** The condition `name`, model name, and other condition-level fields are intentionally excluded from the transcript. Participants copy and read this JSON, so including them could reveal the treatment assignment and introduce demand characteristics. Treatment assignment is tracked in Qualtrics via the session code.

### Analysing transcripts in Python

```python
import pandas as pd, json

raw  = 'paste the JSON string from Qualtrics export here'
data = json.loads(raw)
df   = pd.DataFrame(data["messages"])  # one row per turn
print(df)
```

### Analysing transcripts in R

```r
library(jsonlite)
library(tidyverse)

raw  <- 'paste the JSON string from Qualtrics export here'
data <- fromJSON(raw)
df   <- as.data.frame(data$messages)  # one row per turn
glimpse(df)
```

---

## Deploying for a real study

For data collection you need the app accessible on the web. Two straightforward options:

### Option A - Streamlit Community Cloud (free, recommended for pilots)

1. Push your repo to GitHub (make sure `.env` is in `.gitignore` - it already is)
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo
3. Under **Advanced settings → Secrets**, add:
   ```toml
   OPENAI_API_KEY = "your-actual-api-key-here"
   ```
4. Deploy - Streamlit gives you a public URL to share with participants

### Option B - Any cloud VM (DigitalOcean, Hetzner, AWS EC2, etc.)

```bash
git clone https://github.com/your-org/surveychat.git
cd surveychat
pip install -r requirements.txt
cp .env.example .env
# add your API key to .env
streamlit run app.py --server.port 80 --server.headless true
```

Use [Caddy](https://caddyserver.com/) or nginx to add HTTPS (required for Qualtrics iframe embeds).

---

## Integrating with Qualtrics

1. Add a **Text / Graphic** question block with a link to your surveychat URL
2. After the chat block, add a **Text Entry** question:
   > *"Please paste the chat transcript you copied below."*
3. In your analysis script, parse the JSON from that column

---

## Project structure

```
surveychat/
├── app.py              ← entire application (edit the top section for your study)
├── requirements.txt    ← Python dependencies
├── .env.example        ← copy to .env and add your API key
├── .env                ← your actual key (gitignored - never committed)
├── run.sh              ← convenience script: sh run.sh
├── .streamlit/         ← Streamlit configuration (theme etc.)
├── LICENSE
└── README.md
```

---

## Troubleshooting

**"Code not recognised" on the session code screen**  
→ Check that the code is listed in a `"key"` field inside `CONDITIONS` in `app.py` (comparison is case-insensitive). Common causes: a typo in the config, or the participant miscopied the code from Qualtrics.

**The chatbot changes condition on page refresh**  
→ This happens when running without session codes (`"key"` not defined on conditions). Add a `"key"` to each condition and use the code-entry workflow — the same code always routes to the same arm. See [Testing your conditions before launch](#testing-your-conditions-before-launch).

**"OPENAI_API_KEY not found or empty"**  
→ Make sure `.env` exists in the project root and contains `OPENAI_API_KEY=...` (no spaces around `=`).

**"CONDITIONS list has N entries but N_CONDITIONS is set to M"**  
→ Either add more condition dictionaries to `CONDITIONS` or reduce `N_CONDITIONS`.

**The app opens but the chat returns an error**  
→ Check that `API_BASE_URL` is correct for your provider and that your key has the right permissions.

**I always get Condition A / the same condition**  
→ With session code routing this is expected — the code deterministically selects the arm. To test a different arm, enter a different code. With random routing (no codes), condition A has a 50% probability; open multiple tabs to see both arms.

**Port 8501 is already in use**  
→ Run `pkill -f "streamlit run"` then try again, or use a different port:  
`streamlit run app.py --server.port 8502`

---

## License

[AGPL-3.0](LICENSE) - free to use and fork for academic research. Any modifications must be released under the same license.
