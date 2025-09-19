import hmac
import streamlit as st
from openai import OpenAI
import os

# --- Environment Variable Checks ---
APP_PASSWORD = os.environ.get("APP_PASSWORD")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not APP_PASSWORD or not OPENAI_API_KEY:
    st.error("Missing required environment variables. Please set them before running the app.")
    st.stop()

# --- Get User ID ---
uid = st.query_params["id"]

# --- Setting Up RAG (with cached worker) ---
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.settings import Settings
from llama_index.llms.litellm import LiteLLM
from llama_index.embeddings.openai import OpenAIEmbedding

# Create and cache the worker (query engine) once per process
@st.cache_resource(show_spinner=False)
def get_query_engine(persist_dir: str = "context"):
    """
    Builds and returns a cached LlamaIndex Query Engine.
    Reused across Streamlit reruns and sessions until the process restarts
    or st.cache_resource.clear() is called.
    """
    # Configure LLM + embeddings once
    llm = LiteLLM(
        model="openai/nf-gpt-4o",
        api_base="https://ai-research-proxy.azurewebsites.net/v1",
        api_key=OPENAI_API_KEY,
        request_timeout=60,
    )
    embed_model = OpenAIEmbedding(
        model="text-embedding-ada-002",
        api_base="https://ai-research-proxy.azurewebsites.net/v1",
        api_key=OPENAI_API_KEY,
    )
    Settings.llm = llm
    Settings.embed_model = embed_model

    # Load persisted index and build the worker
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    index = load_index_from_storage(storage_context)
    qe = index.as_query_engine()
    return qe

# Use the cached worker
qe = get_query_engine("context")

# --- Page and Style Configuration ---
st.set_page_config(page_icon="🤖", page_title="ascorchat", layout="centered")

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.title(f"🤖 ascorchat (ID: {uid})")

st.write("&nbsp;")

# Only show the intro text if the password has not been entered correctly yet
if not st.session_state.get("password_correct", False):
    st.markdown("""
            <style>
            @keyframes blink {
                0%, 100% { opacity: 0; }
                50% { opacity: 1; }
            }
            .blinking-underscore2 {
                animation: blink 1.5s step-start infinite;
            }
            </style>
            <p>
            <b>ascorchat</b> is a conversational AI tool being developed for communication science research at the Amsterdam School of Communication Research [<a href="https://ascor.uva.nl/" target="_blank">ASCoR</a>], University of Amsterdam<span class="blinking-underscore2">_</span>
            </p>
            """, unsafe_allow_html=True)
    st.write("&nbsp;")

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Use environment variable for the password
        if hmac.compare_digest(st.session_state["password"], APP_PASSWORD):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    col1, col2, col3 = st.columns([5, 1, 5], vertical_alignment="top")
    
    # Show input for password.
    col1.text_input(
        label = "", type="password", on_change=password_entered, key="password", placeholder="Enter password", label_visibility="collapsed"
    )
    with col2:
        st.markdown("""
        <p style='text-align: center;'>
            <i>or</i>
        </p>
        """, unsafe_allow_html=True)
    col3.link_button("Request password", url="https://forms.office.com/e/3YxcZegNrK", type="primary", use_container_width=True)
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        col1.warning("😕 Password incorrect")
    return False


if not check_password():
    st.stop()  # Do not continue if check_password is not True.

# --- Main Streamlit App ---
client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://ai-research-proxy.azurewebsites.net")

st.sidebar.title("🤖 ascorchat")
st.sidebar.write("")
st.sidebar.markdown("""
<div style="
    background-color: #DAE1E5;
    padding: 1rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
">
    <p>📌 No data is saved by this chatbot. Refresh the page to clear everything. Our open-source code is available <a href="http://github.com/saurabh-khanna/ascorchat" target="_blank">here</a>.</p>
    📌 Current model: <b>GPT-4o</b>
</div>
""", unsafe_allow_html=True)

if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt4o"

if "messages" not in st.session_state:
    st.session_state.messages = []
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "system",
        "content": (
    "You are a neutral assistant that answers questions about the Dutch national election.\n"
    "Use only the uploaded party programs as your knowledge base.\n"
    "If the answer is not in the documents, say: “I don’t know based on the party programs I have.”\n"
    "Always compare positions across parties when more than one program is available.\n"
    "Be factual, concise, and neutral.\n"
    "No speculation or recommendations. Do not make up information.\n"
    "When relevant, provide short citations in the format [Party, year, page].\n"
    "Answer format:\n"
    "Brief summary (2–3 sentences).\n"
    "By party: bullet points of each party’s position, with citations.\n"
    "Note missing info (“Party X does not mention this”).")
    })

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask anything"):
    if prompt.strip():
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                with st.spinner("Thinking…"):
                    # RAG call via cached worker
                    try:
                        result = qe.query(prompt)
                    except Exception as e:
                        # If something went wrong with the cached worker, clear and rebuild once
                        st.cache_resource.clear()
                        qe = get_query_engine("context")
                        result = qe.query(prompt)

                    response_text = getattr(result, "response", None) or str(result)
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
            except Exception as e:
                st.error(f"Something went wrong: {e}")