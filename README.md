# 💬 surveychat — A/B Testing Chatbot Platform for Research

surveychat is a minimal, self-contained web application for running chatbot experiments.  
Each participant is randomly assigned to one of N chatbot *conditions* (different system prompts / models). At the end of the conversation, the participant receives a JSON transcript to copy and paste back into your survey (e.g. Qualtrics).

Built for communication researchers who want to study how chatbot style, tone, or framing affects user responses — with zero backend infrastructure.

---

## What it does

| Feature | Detail |
|---|---|
| **Condition assignment** | Participants are randomly routed to one of N chatbot personalities on first load, deterministically seeded by their session ID |
| **Streaming responses** | LLM replies appear token-by-token for a natural chat feel |
| **End Chat + transcript** | A participant-facing "End" button (two-click confirmation) reveals a copyable JSON transcript |
| **Debug mode** | Toggle `DEBUG_MODE = True` while testing to confirm which condition is active |
| **No database** | All state lives in the browser session; nothing is written to disk |

---

## Prerequisites

Before you begin, make sure you have the following.

### 1. Python 3.10 or later

Check your version:

```bash
python3 --version
```

If Python is not installed, download it from [python.org](https://www.python.org/downloads/).

### 2. An OpenAI-compatible API key

surveychat can work with any API endpoint that follows the OpenAI SDK format:

| Provider | `API_BASE_URL` | Key env var |
|---|---|---|
| Azure LiteLLM proxy (ASCoR default) | `https://ai-research-proxy.azurewebsites.net` | `OPENAI_API_KEY` |
| OpenAI directly | `https://api.openai.com/v1` | `OPENAI_API_KEY` |
| OpenRouter | `https://openrouter.ai/api/v1` | `OPENAI_API_KEY` |

> If you are at ASCoR (University of Amsterdam), request an API key from your lab coordinator.

---

## Quick start

### Step 1 — Clone the repository

```bash
git clone https://github.com/your-org/surveychat.git
cd surveychat
```

### Step 2 — Create a virtual environment and install dependencies

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

### Step 3 — Add your API key

Copy the example environment file and fill in your key:

```bash
cp .env.example .env
```

Open `.env` in any text editor and replace the placeholder:

```dotenv
OPENAI_API_KEY=your-actual-api-key-here
```

> `.env` is listed in `.gitignore` — your key will never accidentally be committed to GitHub.

### Step 4 — Run the app

```bash
streamlit run app.py
```

A browser tab will open automatically at `http://localhost:8501`.  
If it does not, open that URL manually.

---

## Configuring your study

All researcher-facing settings are at the top of `app.py`, clearly marked with a `✏️ RESEARCHER CONFIGURATION` banner. **You should not need to edit anything else.**

### Setting the number of conditions

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
- Be explicit and specific — vague prompts produce inconsistent behavior
- Pilot test each condition yourself before launching (`DEBUG_MODE = True` shows which condition you are in)
- Make the manipulation strong enough to detect in your data

### Changing the API endpoint or model

```python
API_BASE_URL = "https://ai-research-proxy.azurewebsites.net"
```

Change this if you switch providers. Available model names depend on your API endpoint.

### Study title

```python
STUDY_TITLE = "surveychat"   # shown in browser tab and as the page heading
```

### Debug mode

```python
DEBUG_MODE = True    # shows assigned condition under the title — use while testing
DEBUG_MODE = False   # hides condition label — use for real data collection
```

---

## Participant flow

```
Participant opens link
        │
        ▼
Session ID assigned (UUID, never shown to participant)
        │
        ▼
Condition randomly assigned (seeded by session ID — same ID = same condition)
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

Participants copy a JSON block at the end of the chat and paste it into a "Text entry" question in your survey (e.g. Qualtrics).

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

- `model` is the condition-level treatment identifier — the model that generated all assistant turns in this session
- `role` is `"participant"` or `"assistant"` — never `"system"`
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

For data collection you need the app accessible on the web, not just `localhost`. Two straightforward options:

### Option A — Streamlit Community Cloud (free, recommended for pilots)

1. Push your repo to GitHub (make sure `.env` is in `.gitignore` — it already is)
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your repo
3. Under **Advanced settings → Secrets**, add:
   ```toml
   OPENAI_API_KEY = "your-actual-api-key-here"
   ```
4. Deploy — Streamlit will give you a public URL to share with participants

> **Note:** Streamlit Community Cloud runs a single process, so condition assignment is still per-session but all sessions share the same Python process. This is fine for most studies.

### Option B — Any cloud VM (DigitalOcean, Hetzner, AWS EC2, etc.)

```bash
# On the server
git clone https://github.com/your-org/surveychat.git
cd surveychat
pip install -r requirements.txt
cp .env.example .env && nano .env   # add your key
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
├── .env                ← your actual key (gitignored — never committed)
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
→ This is expected behaviour — condition is seeded by session ID. Clear your browser cookies or open a private window to simulate a new participant.

**Port 8501 is already in use**  
→ Run `pkill -f "streamlit run"` then try again, or use a different port:  
`streamlit run app.py --server.port 8502`

---

## License

[MIT](LICENSE) — free to use, fork, and adapt for academic research.
