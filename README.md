# 💬 surveychat

A lightweight Python app for running **chatbot surveys and experiments**.

- **Survey mode** (`N_CONDITIONS = 1`) — every participant talks to the same chatbot. Great for open-ended interviews, pilot testing, or replacing a text-entry question with a conversation.
- **Experiment mode** (`N_CONDITIONS ≥ 2`) — participants are randomly assigned to different chatbot versions (e.g. neutral vs. empathetic). Use this for A/B tests or multi-arm studies.

In both modes the participant chats, clicks **End**, and copies a JSON transcript back into your survey tool (e.g. Qualtrics). No server, no database — just configure and run.

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

**Survey mode** — one chatbot for everyone, no codes needed:

```python
N_CONDITIONS = 1

CONDITIONS = [
    {
        "name":          "Interview bot",
        "system_prompt": "You are a friendly research interviewer. Ask open-ended follow-up questions.",
        "model":         "gpt-oss-120b",
    },
]
```

**Experiment mode** — multiple conditions, each participant gets a code:

```python
N_CONDITIONS = 2   # 2 = A/B test, 3+ = multi-arm

CONDITIONS = [
    {
        "name":          "Condition A - Neutral",   # internal label only
        "passcode":      "ALPHA",                   # passcode for this arm
        "system_prompt": "You are a neutral assistant...",
        "model":         "gpt-oss-120b",
    },
    {
        "name":          "Condition B - Empathetic",
        "passcode":      "BETA",
        "system_prompt": "You are a warm, empathetic assistant...",
        "model":         "gpt-oss-120b",
    },
]
```

- `name` — internal label, never shown to participants
- `passcode` — passcode that routes participants to this arm (case-insensitive); omit when `N_CONDITIONS = 1`
- `system_prompt` — hidden instruction that shapes the chatbot's behavior
- `model` — model name for this condition

### Other settings

```python
STUDY_TITLE      = "surveychat"   # browser tab + page heading
PASSCODE_ENTRY_PROMPT = "Please enter the passcode you received in the survey to begin."
WELCOME_MESSAGE  = ""             # optional instruction shown above the chat
```

---

## How it works

### Survey mode (`N_CONDITIONS = 1`)

Use this when you want every participant to talk to the same chatbot — for example, an open-ended interview, a pilot study, or a qualitative data-collection task.

1. Set `N_CONDITIONS = 1` in `app.py` and write your `system_prompt`
2. Share the surveychat link with participants (no passcode needed)
3. They chat, click **End**, and copy the JSON transcript
4. They paste the transcript into a Qualtrics text-entry question (or you collect it however you like)

### Experiment mode (`N_CONDITIONS ≥ 2`)

Use this when you want to compare how different chatbot versions affect participants — for example, testing whether a more empathetic tone increases disclosure.

1. Qualtrics randomly assigns each participant to an arm and shows them their passcode (e.g. *"Your passcode is: ALPHA"*)
2. Participant opens the surveychat link, enters their code, and is routed to the matching chatbot condition
3. They chat, click **End**, and copy the JSON transcript
4. They paste the transcript into a Qualtrics text-entry question

Passcodes are stable across page refreshes — re-entering the same passcode always returns the same condition.

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

Condition name and model are excluded — participants read this JSON and must not know their arm. Treatment assignment is tracked in Qualtrics via the passcode.

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

### Docker
The repo ships with a `Dockerfile` and `docker-compose.yml`.

**Quick start (recommended):**
```bash
docker compose up --build
```
Open [http://localhost:8501](http://localhost:8501). The container reads your `.env` file automatically.

**Without Compose:**
```bash
docker build -t surveychat .
docker run --rm -p 8501:8501 --env-file .env surveychat
```

**Production tips:**
- Remove the `volumes:` bind-mount in `docker-compose.yml` so the image is fully self-contained.
- Serve HTTPS via a reverse proxy (Caddy, nginx) in front of port 8501 — required for Qualtrics iFrame embeds.
- On a cloud VM, add `--server.port 80` to the `ENTRYPOINT` in the `Dockerfile` if you expose port 80 directly.

### Cloud VM (without Docker)
```bash
pip install -r requirements.txt
streamlit run app.py --server.port 80 --server.headless true
```
Add HTTPS via Caddy or nginx (required for Qualtrics embeds).

---

## Integrating with Qualtrics

**Survey mode (N = 1) — simplest setup:**
1. Add a **Text / Graphic** block with your surveychat link and a brief instruction
2. After the chat embed, add a **Text Entry** question: *"Paste your chat transcript here"*
3. Export responses and parse the JSON from that column

**Experiment mode (N > 1) — A/B or multi-arm:**
1. Use Qualtrics **Survey Flow → Randomizer** to split participants into arms
2. In each arm's branch, display the matching passcode (e.g. *"Your passcode is: ALPHA"*) and a link to the surveychat URL
3. After the chat, add a **Text Entry** question: *"Paste your chat transcript here"*
4. Export responses — condition assignment is recoverable from the passcode in your Qualtrics data

---

## Troubleshooting

**"Code not recognised"** — Check that the passcode matches a `"passcode"` value in `CONDITIONS` (case-insensitive). Common cause: typo in config or participant miscopied the passcode.

**"OPENAI_API_KEY not found"** — Make sure `.env` exists and contains `OPENAI_API_KEY=your-key` (no spaces around `=`).

**Chat returns an API error** — Verify `API_BASE_URL` is correct for your provider and the key has the right permissions.

**Port 8501 already in use** — Run `pkill -f "streamlit run"` then retry, or use `--server.port 8502`.

---

## Citing

If you use `surveychat` in published research, please cite the accompanying
JOSS paper (replace with the DOI assigned after acceptance):

```bibtex
@article{surveychat,
  title   = {surveychat: A {Streamlit} Platform for Chatbot Surveys
             and Randomized Experiments},
  author  = {Khanna, Saurabh},
  journal = {Journal of Open Source Software},
  year    = {2026},
  doi     = {TODO},
}
```

