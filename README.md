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
| **Condition assignment** | Each participant is randomly assigned to one of N chatbot personalities when they first open the app. Because session state resets on page refresh, a participant who reloads the page may be assigned a different condition. |
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

Each condition is a dictionary with three keys:

```python
CONDITIONS = [
    {
        "name": "Condition A - Neutral",     # internal label only, not shown to participants
        "system_prompt": (
            "You are a helpful and neutral research assistant. "
            "Answer all questions clearly and concisely without expressing "
            "personal opinions or emotional reactions."
        ),
        "model": "gpt-oss-120b",             # model name for this condition
    },
    {
        "name": "Condition B - Empathetic",
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

### API endpoint

```python
API_BASE_URL = "https://ai-research-proxy.azurewebsites.net"
```

Change this if you switch providers. Available model names depend on your endpoint.

### Study title

```python
STUDY_TITLE = "surveychat"   # shown in browser tab and as the page heading
```

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

surveychat handles randomization *within* the chat portion of your study. If your broader Qualtrics survey already randomizes participants into arms (e.g. different vignettes, different question frames), you can run a **separate surveychat deployment per arm**, each with `N_CONDITIONS = 1` and a condition-specific system prompt.

Workflow:
1. Qualtrics assigns the participant to Arm A or Arm B via its own randomization logic
2. The Qualtrics branch for Arm A links to a surveychat instance configured for that arm
3. The Qualtrics branch for Arm B links to a different surveychat instance configured for that arm
4. Each instance uses `N_CONDITIONS = 1` - no further randomization inside the chat

This keeps condition assignment fully in Qualtrics (where you already track it) while still benefiting from surveychat's streaming interface and transcript export.

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

The JSON transcript always records which model (and therefore which condition) generated the responses. In your Qualtrics export, the `model` value acts as a ready-made treatment indicator - no need to merge a separate randomization file.

---

## Testing your conditions before launch

**Refreshing the page can change the arm.** Streamlit session state is tied to the WebSocket connection, which resets on page reload. A new session means a new random assignment, so the condition is not guaranteed to be the same after a refresh. In a real study, participants are expected to stay on the page for the duration of the chat without refreshing.

To see a different condition while testing:

| What you want | How to do it |
|---|---|
| Try a fresh random assignment | Refresh the page, or open a new tab |
| Force a *specific* condition | Temporarily set `N_CONDITIONS = 1` and move the condition you want to test to the first slot in `CONDITIONS` |
| Reset every active session | Restart the server: `Ctrl-C` then `streamlit run app.py` |
| Confirm which arm you are in | Set `DEBUG_MODE = True` - the assigned condition name appears under the page title |

A good pre-launch checklist:
1. Set `DEBUG_MODE = True`
2. Open the app in a normal window and in an incognito window - with `N_CONDITIONS = 2` you should eventually land in different arms across several opens
3. Send a few messages in each and verify the chatbot behaves as expected
4. Set `DEBUG_MODE = False` before sharing the link with participants

---

## Participant flow

```
Participant opens link
        │
        ▼
Session ID assigned (UUID, never shown to participant)
        │
        ▼
Condition randomly assigned (seeded by random session ID)
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

### Analysing transcripts in Python

```python
import pandas as pd, json

raw   = 'paste the JSON string from Qualtrics export here'
data  = json.loads(raw)
model = data["model"]                  # treatment variable
df    = pd.DataFrame(data["messages"]) # one row per turn
print(model, df)
```

### Analysing transcripts in R

```r
library(jsonlite)
library(tidyverse)

raw   <- 'paste the JSON string from Qualtrics export here'
data  <- fromJSON(raw)
model <- data$model                    # treatment variable
df    <- as.data.frame(data$messages)  # one row per turn
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

**"OPENAI_API_KEY not found or empty"**  
→ Make sure `.env` exists in the project root and contains `OPENAI_API_KEY=...` (no spaces around `=`).

**"CONDITIONS list has N entries but N_CONDITIONS is set to M"**  
→ Either add more condition dictionaries to `CONDITIONS` or reduce `N_CONDITIONS`.

**The app opens but the chat returns an error**  
→ Check that `API_BASE_URL` is correct for your provider and that your key has the right permissions.

**I always get Condition A / the same condition**  
→ With `N_CONDITIONS = 2` the probability of landing in Condition A is 50%, so it is normal to see the same one a few times in a row. Each page load is an independent randomization. Try opening several tabs in quick succession - you should see both conditions appear. To force a specific condition for a test, temporarily set `N_CONDITIONS = 1` and put the desired condition first in `CONDITIONS`.

**Port 8501 is already in use**  
→ Run `pkill -f "streamlit run"` then try again, or use a different port:  
`streamlit run app.py --server.port 8502`

---

## License

[AGPL-3.0](LICENSE) - free to use and fork for academic research. Any modifications must be released under the same license.
