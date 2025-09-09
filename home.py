import hmac
import streamlit as st
from openai import OpenAI
import os

# --- Environment Variable Checks ---
# Check for required environment variables and display errors if not found.
# This is crucial for deployment and debugging.
APP_PASSWORD = os.environ.get("APP_PASSWORD")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not APP_PASSWORD or not OPENAI_API_KEY:
    st.error("Missing required environment variables. Please set them before running the app.")
    st.stop()

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

st.title("🤖 ascorchat")

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
# Use environment variable for the OpenAI API key
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

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask anything"):
    if prompt.strip():  # Check if the message is not empty or just spaces
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model=st.session_state["openai_model"],
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=True,
            )
            response = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": response})