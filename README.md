# 💬 surveychat

[![Open Source Love](https://badges.frapsoft.com/os/v1/open-source.svg?v=103)](https://github.com/ellerbrock/open-source-badges/)
![GitHub License](https://img.shields.io/github/license/surveychat/surveychat)

A lightweight Python application for running **surveys and experiments with AI chatbots**. 

surveychat works in two modes:

- **Survey mode** - every participant talks to the same chatbot. Good for open-ended interviews, pilot testing, or replacing a plain text-entry question with a richer conversation.
- **Experiment mode** - participants are automatically assigned to different chatbot versions (e.g. neutral vs. empathetic vs. socratic). Use this when you want to *compare* how different chatbot styles/models/prompts affect responses.

In both modes the participant chats, clicks **End chat**, and copies a text transcript back into your survey tool (e.g. Qualtrics). No coding experience beyond editing a text file is required - no server to manage, no database to set up.

surveychat can be **embedded directly inside a Qualtrics survey** as an iFrame, so participants never leave the survey page. In survey mode, the chatbot loads directly on the page and participants start chatting straight away. In experiment mode, Qualtrics shows each participant their passcode first, then the chatbot loads below it on the same page.

> Demo of an experimental setup [here](https://surveychat.invisible.info) - use code ALPHA for neutral chatbot, and BETA for empathetic chatbot.

Entering the chatbot (this example shows a passcode screen used in experiment mode):

<img width="744" height="393" alt="image" src="https://github.com/user-attachments/assets/64c0d4c4-9eca-4318-833f-e834cf178e1b" />

Ongoing conversation:

<img width="754" height="708" alt="image" src="https://github.com/user-attachments/assets/9e2d5a81-5782-46ad-afec-037e8225a3f7" />

Participant copies and pastes the conversation back into the original survey tool (e.g. Qualtrics):

<img width="775" height="745" alt="image" src="https://github.com/user-attachments/assets/433ae630-0894-4dee-9467-03c016562919" />

---

## Before you start

You will need:

- **Python 3.10 or newer.** Check by running `python3 --version` in your terminal. If you don't have Python, download it from [python.org](https://www.python.org/downloads/).
- **An API key.** surveychat uses a large language model (LLM) to power the chatbot. You will need an API key from any compatible provider (OpenAI, Azure, OpenRouter, or a local proxy). The key is stored in the `OPENAI_API_KEY` environment variable by convention.
- **A terminal.** On macOS/Linux open **Terminal**. On Windows open **Command Prompt** or **PowerShell**.

---

## Quick start

**Step 1 - Fork the repo**

Click **Fork** at the top right of this GitHub page. This creates your own copy of surveychat under your GitHub account, which you can edit and deploy freely.

**Step 2 - Clone your fork to your computer**

Replace `YOUR_USERNAME` with your GitHub username:

```bash
git clone https://github.com/YOUR_USERNAME/surveychat.git
cd surveychat
pip install -r requirements.txt
cp .env.example .env
```

> **Don't have git?** Download it from [git-scm.com](https://git-scm.com/downloads) (free). On macOS it may already be installed - check with `git --version` in your terminal.

Now open the file called `.env` in any text editor and replace `your-key-here` with your actual API key:

```
OPENAI_API_KEY=sk-...
```

Save the file, then start the app by running this command in the terminal:

```bash
streamlit run app.py
```

Your browser will open automatically at http://localhost:8501. You should see the chatbot interface.

---

## Configuration

All settings live at the top of the file `app.py` inside a clearly marked section. You do not need to touch any other part of the file.

Open `app.py` in a text editor and find the block that begins:

```
# ╔══════════ RESEARCHER CONFIGURATION ═══════════╗
```

Everything you need to change is between that line and the matching closing line.

---

### Step 1 - Choose your mode

Set `N_CONDITIONS` to the number of different chatbot versions you need:

```python
N_CONDITIONS = 1   # survey mode  - one chatbot for everyone
N_CONDITIONS = 2   # experiment mode - A/B test (two versions)
N_CONDITIONS = 3   # experiment mode - three versions, and so on
```

---

### Step 2 - Write your chatbot instructions

The `CONDITIONS` list defines each chatbot version. Each version is a block of settings inside curly braces `{ }`.

**Survey mode example** (`N_CONDITIONS = 1`):

```python
CONDITIONS = [
    {
        "name":          "Interview bot",
        "system_prompt": "You are a friendly research interviewer. Ask one open-ended question at a time about the participant's social media habits. After 5–6 exchanges, thank them and let them know they can click End this chat.",
        "model":         "gpt-oss-120b",
    },
]
```

**Experiment mode example** (`N_CONDITIONS = 2`):

```python
CONDITIONS = [
    {
        "name":          "Condition A - Neutral",
        "passcode":      "ALPHA",
        "system_prompt": "You are a neutral research assistant. Answer questions clearly and factually without expressing opinions.",
        "model":         "gpt-oss-120b",
    },
    {
        "name":          "Condition B - Empathetic",
        "passcode":      "BETA",
        "system_prompt": "You are a warm, empathetic research assistant. Acknowledge the participant's feelings before responding.",
        "model":         "gpt-oss-120b",
    },
]
```

**What each field means:**

| Field | Required? | What it does |
|---|---|---|
| `"name"` | Always | A label for your own reference. Participants never see this. |
| `"passcode"` | Experiment mode only | The code a participant enters to reach this condition. Case-insensitive (`"alpha"` and `"ALPHA"` are the same). Leave this out when `N_CONDITIONS = 1`. |
| `"system_prompt"` | Always | The hidden instruction that tells the chatbot how to behave. Participants never see this text. |
| `"model"` | Always | Which AI model to use. Ask your lab coordinator which model name to use. |

---

### Step 3 - Optional settings

```python
STUDY_TITLE = "surveychat"
# The name shown in the browser tab and at the top of the page.
# Change this to your study name, e.g. "Climate Attitudes Study".

WELCOME_MESSAGE = ""
# A message shown to participants before they start chatting.
# Leave as "" for no message, or write something like:
# "Welcome. You will have a short conversation with an AI assistant.
#  When you are done, click End this chat to receive your transcript."

PASSCODE_ENTRY_PROMPT = "Please enter the passcode you received in the survey to begin."
# The instruction shown above the passcode box (experiment mode only).
```

---

## How it works

### Survey mode (`N_CONDITIONS = 1`)

1. Set `N_CONDITIONS = 1` and write your `system_prompt`
2. Embed the app URL within Qualtrics for participants - no passcode needed
3. They chat, click **End chat**, and copy the JSON transcript
4. They paste the transcript into a Qualtrics text-entry question

### Experiment mode (`N_CONDITIONS ≥ 2`)

1. In Qualtrics, use **Survey Flow → Randomizer** to split participants into arms
2. In each arm's branch, tell participants their passcode (e.g. *"Your passcode is: ALPHA"*) and show the app link
3. They open the link, enter their passcode, and are routed to the right chatbot
4. They chat, click **End chat**, and copy the JSON transcript
5. They paste the transcript into a Qualtrics text-entry question
6. When you export data, which condition each participant was in is known from which Qualtrics branch showed them their passcode

---

## Transcript format

```json
{
  "messages": [
    {
      "role": "participant", 
      "content": "Hello!", 
      "timestamp": "2026-03-06T14:22:01+00:00"
    },
    {
      "role": "assistant",
      "content": "Hi there! How can I help you today?", 
      "timestamp": "2026-03-06T14:22:03+00:00"
    }
  ]
}
```

Each message has:
- `role` - either `"participant"` (what the person typed) or `"assistant"` (the chatbot's reply)
- `content` - the full text of the message
- `timestamp` - when the message was sent (UTC time)


**Note:** The JSON transcript can be parsed in Python or R using standard libraries. Each message becomes a row in a dataframe, with columns for `role`, `content`, and `timestamp`.

Parse in Python:
```python
import json, pandas as pd
data = json.loads(transcript_string)   # transcript_string is the text they pasted
df   = pd.DataFrame(data["messages"]) # one row per message
```

Parse in R:
```r
library(jsonlite)
data <- fromJSON(transcript_string)
df   <- as.data.frame(data$messages)
```

---

## Deployment

### Option 1 - Run locally on your own computer

This is the easiest option for testing or small studies where you can keep your laptop running.

```bash
streamlit run app.py
```

Share the URL that appears in the terminal with participants on the same network.

### Option 2 - Streamlit Community Cloud (free for public repos)

This gives you a permanent public URL with no server to manage.

1. Push your repo to GitHub (your `.env` file is excluded automatically)
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your GitHub repo
3. Under **Advanced settings → Secrets**, add: `OPENAI_API_KEY = "sk-..."`
4. Click **Deploy** - you get a public URL to share with participants

### Option 3 - Docker (for researchers comfortable with the command line)
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
- Serve HTTPS via a reverse proxy (Caddy, nginx) in front of port 8501 - required for Qualtrics iFrame embeds.
- On a cloud VM, add `--server.port 80` to the `ENTRYPOINT` in the `Dockerfile` if you expose port 80 directly.

### Option 4 - Cloud VM (advanced)

For a permanent public deployment on a cloud server (e.g. Azure, AWS, DigitalOcean), set up a VM with Python and Docker, clone your repo, and run the app with:

```bash
pip install -r requirements.txt
streamlit run app.py --server.port 80 --server.headless true
```

---

## Integrating with Qualtrics

surveychat works well when embedded directly inside your Qualtrics survey using an **iFrame** - a standard way to show one website inside another. Participants stay on the Qualtrics page the whole time: the chatbot loads right there, they chat, and then paste their transcript into the next question without ever opening a separate tab. In experiment mode, Qualtrics shows each participant their passcode just above the iFrame so they can enter it to start.

To embed, add a **Text / Graphic** block in Qualtrics and paste this HTML, replacing the URL with your own:

```html
<iframe
  src="https://your.apps.url/"
  width="100%"
  height="600"
  frameborder="0"
  allow="clipboard-write"
></iframe>
```

The `allow="clipboard-write"` attribute lets the built-in copy button work inside the iFrame.

**Survey mode (N = 1):**
1. Add a **Text / Graphic** block containing the iFrame above (or just a plain link if you prefer)
2. After that block, add a **Text Entry** question: *"Paste your chat transcript here"*
3. Export responses and parse the JSON from that column

**Experiment mode (N > 1):**
1. Use Qualtrics **Survey Flow - Randomizer** to split participants into arms
2. In each arm's branch, display the matching passcode (e.g. *"Your passcode is: ALPHA"*) and embed the iFrame below it
3. After the iFrame block, add a **Text Entry** question: *"Paste your chat transcript here"*
4. Export responses - you know which condition each participant was in from which Qualtrics branch they went through

---

## Troubleshooting

**"Code not recognised"**
The passcode the participant typed does not match any `"passcode"` value in `CONDITIONS`. Check for typos in `app.py`. Passcode matching is case-insensitive, so `"alpha"` and `"ALPHA"` both work.

**"OPENAI_API_KEY not found"**
Make sure the `.env` file exists in the project folder and contains a line exactly like this (no spaces around `=`):
```
OPENAI_API_KEY=sk-your-key-here
```

**Chat returns an error message**
Verify that `API_BASE_URL` in `app.py` is set to the correct URL for your API provider, and that your key is valid and has not expired.

**The app does not open in the browser**
Manually open http://localhost:8501. If you see "connection refused", the app may have crashed - check the terminal for error messages.

**"Port 8501 already in use"**
Another instance of the app is already running. Stop it with:
```bash
pkill -f "streamlit run"
```
Or start the app on a different port:
```bash
streamlit run app.py --server.port 8502
```

**I edited `app.py` but nothing changed**
Streamlit usually reloads automatically when you save the file. If it does not, press **R** in the terminal where the app is running, or stop and restart with `streamlit run app.py`.


