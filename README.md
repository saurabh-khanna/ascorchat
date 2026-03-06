# 💬 surveychat

A minimal Streamlit app for running chatbot experiments. Participants are routed to one of N chatbot conditions via a session code, chat with the bot, then copy a JSON transcript to paste back into your survey (e.g. Qualtrics).

---

## Quick start

```bash
git clone https://github.com/YOUR_USERNAME/surveychat.git
cd surveychat
pip install -r requirements.txt
cp .env.example .env          # then add your API key to .env
streamlit run app.py
```

---

## Configuration

All settings are at the top of `app.py`. You should not need to edit anything else.

### Conditions

```python
N_CONDITIONS = 2   # 1 = no randomization (survey mode), 2 = A/B, 3+ = multi-arm

CONDITIONS = [
    {
        "name":          "Condition A - Neutral",   # internal label only
        "key":           "ALPHA",                   # session code for this arm
        "system_prompt": "You are a neutral assistant...",
        "model":         "gpt-oss-120b",
    },
    {
        "name":          "Condition B - Empathetic",
        "key":           "BETA",
        "system_prompt": "You are a warm, empathetic assistant...",
        "model":         "gpt-oss-120b",
    },
]
```

- `name` — internal label, never shown to participants
- `key` — session code that routes participants to this arm (case-insensitive); omit when `N_CONDITIONS = 1`
- `system_prompt` — hidden instruction that shapes the chatbot's behavior
- `model` — model name for this condition

### Other settings

```python
STUDY_TITLE      = "surveychat"   # browser tab + page heading
KEY_ENTRY_PROMPT = "Please enter the session code you received in the survey to begin."
WELCOME_MESSAGE  = ""             # optional instruction shown above the chat
```

---

## How it works

**With session codes (N > 1):**
1. Qualtrics assigns participants to arms and shows each participant their code (e.g. *"Your session code is: ALPHA"*)
2. Participant opens the surveychat link, enters their code, and is routed to the matching condition
3. They chat, click **End**, and copy the JSON transcript
4. They paste the transcript into a Qualtrics text-entry question

**Survey mode (N = 1):**
No code screen. All participants see the same chatbot.

Session codes are stable across page refreshes — re-entering the same code always returns the same arm.

---

## Transcript format

```json
{
  "messages": [
    {"role": "participant", "content": "Hello!", "timestamp": "2026-03-06T14:22:01+00:00"},
    {"role": "assistant",   "content": "Hi there!", "timestamp": "2026-03-06T14:22:03+00:00"}
  ]
}
```

Condition name and model are excluded — participants read this JSON and must not know their arm. Treatment assignment is tracked in Qualtrics via the session code.

**Parse in Python:**
```python
import json, pandas as pd
data = json.loads(transcript_string)
df   = pd.DataFrame(data["messages"])
```

**Parse in R:**
```r
library(jsonlite)
data <- fromJSON(transcript_string)
df   <- as.data.frame(data$messages)
```

---

## Deployment

### Streamlit Community Cloud (free)
1. Push your repo to GitHub (`.env` is gitignored)
2. Go to [share.streamlit.io](https://share.streamlit.io), connect your repo
3. Under **Advanced settings → Secrets** add: `OPENAI_API_KEY = "sk-..."`
4. Deploy — you get a public URL to share with participants

### Cloud VM
```bash
pip install -r requirements.txt
streamlit run app.py --server.port 80 --server.headless true
```
Add HTTPS via Caddy or nginx (required for Qualtrics embeds).

---

## Integrating with Qualtrics

1. Add a **Text / Graphic** block with a link to your surveychat URL
2. Show the session code for each arm in the appropriate Qualtrics branch
3. After the chat, add a **Text Entry** question: *"Paste your chat transcript here"*
4. Export responses and parse the JSON from that column

---

## Troubleshooting

**"Code not recognised"** — Check that the code matches a `"key"` value in `CONDITIONS` (case-insensitive). Common cause: typo in config or participant miscopied the code.

**"OPENAI_API_KEY not found"** — Make sure `.env` exists and contains `OPENAI_API_KEY=your-key` (no spaces around `=`).

**Chat returns an API error** — Verify `API_BASE_URL` is correct for your provider and the key has the right permissions.

**Port 8501 already in use** — Run `pkill -f "streamlit run"` then retry, or use `--server.port 8502`.

