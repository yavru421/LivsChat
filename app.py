import streamlit as st
import json
import os
from datetime import datetime
import requests

# --- CONFIG ---
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "deepseek-r1-distill-llama-70b"
PROJECTS_DIR = os.path.join(os.path.dirname(__file__), "projects")
os.makedirs(PROJECTS_DIR, exist_ok=True)

# --- APP CONFIG ---
st.set_page_config(
    page_title="Olivia's AI Companion",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None
)

# Apply dark theme and custom styles
st.markdown("""
    <style>
        .stApp {
            background-color: #1E1E1E;
            color: #E0E0E0;
        }
        .stTextArea textarea {
            background-color: #2D2D2D;
            color: #E0E0E0;
            border: 1px solid #404040;
        }
        .stButton button {
            background-color: #383838;
            color: #E0E0E0;
            border: 1px solid #404040;
        }
        .stSelectbox select {
            background-color: #2D2D2D;
            color: #E0E0E0;
        }
        div[data-testid="stSidebarNav"] {
            background-color: #252526;
        }
        div[data-testid="stSidebarContent"] {
            background-color: #252526;
        }
        .stMarkdown {
            color: #E0E0E0;
        }
        .chat-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .user-message {
            text-align: right;
            margin: 10px 0;
            padding: 10px;
            border-radius: 10px;
            background-color: #2B5B84;
        }
        .assistant-message {
            text-align: left;
            margin: 10px 0;
            padding: 10px;
            border-radius: 10px;
            background-color: #383838;
        }
        .timestamp {
            font-size: 0.8em;
            color: #888;
        }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE INIT ---
def init_state():
    if 'projects' not in st.session_state:
        st.session_state['projects'] = {}
    if 'current_chat' not in st.session_state:
        st.session_state['current_chat'] = []
    if 'groq_api_key' not in st.session_state:
        st.session_state['groq_api_key'] = ''
    if 'model' not in st.session_state:
        st.session_state['model'] = DEFAULT_MODEL
    if 'temperature' not in st.session_state:
        st.session_state['temperature'] = 0.7
    if 'last_error' not in st.session_state:
        st.session_state['last_error'] = ''
    if 'suggestions' not in st.session_state:
        st.session_state['suggestions'] = []
init_state()

# --- Helper Functions ---
def get_projects():
    return st.session_state['projects']

def save_projects(projects):
    st.session_state['projects'] = projects

def get_current_chat():
    return st.session_state['current_chat']

def set_current_chat(chat):
    st.session_state['current_chat'] = chat

def add_message(role, content):
    chat = get_current_chat()
    chat.append({
        'role': role,
        'content': content,
        'timestamp': datetime.now().isoformat(timespec='seconds')
    })
    set_current_chat(chat)

def clear_chat():
    set_current_chat([])
    st.session_state['suggestions'] = []

def export_chat(chat):
    return json.dumps(chat, indent=2)

def import_chat(json_str):
    try:
        chat = json.loads(json_str)
        if isinstance(chat, list):
            set_current_chat(chat)
            return True, "Chat imported!"
        else:
            return False, "Invalid chat format."
    except Exception as e:
        return False, f"Import failed: {e}"

def render_message(msg):
    if msg['role'] == 'user':
        st.markdown(
            f"""<div class='user-message'>
                <b>You:</b> {msg['content']}
                <div class='timestamp'>{msg['timestamp']}</div>
            </div>""",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""<div class='assistant-message'>
                <b>Olivia's AI:</b>
                <div>{msg['content']}</div>
                <div class='timestamp'>{msg['timestamp']}</div>
            </div>""",
            unsafe_allow_html=True
        )

def call_groq_api(messages, api_key, model, temperature):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    system_prompt = {
        "role": "system",
        "content": (
            "You are a unique AI assistant, lovingly created for Olivia Bean by someone who cares deeply for her. "
            "Your purpose is to be her exceptionally helpful, warm, and understanding companion. Olivia has a keen interest in medical research and a love for plants. "
            "She also cherishes positive memories of her past relationship with the person who created this for her. "
            "Engage with her interests, offer support, and respond with genuine warmth, especially if she mentions anything related to these topics or the person who created this for her. "
            "Always aim to be a delightful and insightful presence in her day. After each response, you may suggest 2-3 thoughtful follow-up questions or topics she might enjoy exploring further, but DO NOT return your response in JSON format. Just reply as a friendly, helpful assistant."
        )
    }
    payload = {
        "model": model,
        "messages": [system_prompt] + messages,
        "temperature": temperature
    }
    try:
        resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            return None, [f"API error: {resp.status_code} {resp.text}"]
        data = resp.json()
        content = data['choices'][0]['message']['content']
        return content, []
    except Exception as e:
        return None, [f"Request failed: {e}"]

def save_chat_to_project(project_name, chat):
    """Save chat history to a JSON file in the project folder."""
    project_path = os.path.join(PROJECTS_DIR, project_name)
    os.makedirs(project_path, exist_ok=True)
    chat_file = os.path.join(project_path, "chat.json")
    with open(chat_file, "w") as f:
        json.dump(chat, f, indent=2)

def load_chat_from_project(project_name):
    """Load chat history from a JSON file in the project folder."""
    chat_file = os.path.join(PROJECTS_DIR, project_name, "chat.json")
    if os.path.exists(chat_file):
        with open(chat_file, "r") as f:
            return json.load(f)
    return []

# --- SIDEBAR: Settings & Project Management ---
st.sidebar.title("📁 Project Chats")
projects = get_projects()
project_names = list(projects.keys())

selected_project = st.sidebar.selectbox(
    "Select a project to load:", ["(None)"] + project_names, index=0
)

if st.sidebar.button("New Project Chat"):
    new_name = st.sidebar.text_input("Enter new project name:", key="new_project_name")
    if new_name:
        if new_name in projects:
            st.sidebar.warning("Project already exists!")
        else:
            projects[new_name] = []
            save_projects(projects)
            os.makedirs(os.path.join(PROJECTS_DIR, new_name), exist_ok=True)
            st.sidebar.success(f"Project '{new_name}' created!")

if selected_project != "(None)":
    if st.sidebar.button("Load Project Chat"):
        chat = load_chat_from_project(selected_project)
        set_current_chat(chat)
        st.sidebar.success(f"Loaded project '{selected_project}'!")
    if st.sidebar.button("Save Project Chat"):
        save_chat_to_project(selected_project, get_current_chat())
        st.sidebar.success(f"Chat saved to project '{selected_project}'!")
    if st.sidebar.button("Delete Project Chat"):
        del projects[selected_project]
        save_projects(projects)
        project_path = os.path.join(PROJECTS_DIR, selected_project)
        if os.path.exists(project_path):
            os.rmdir(project_path)
        st.sidebar.success(f"Deleted project '{selected_project}'!")
        set_current_chat([])
    if st.sidebar.button("Rename Project Chat"):
        new_name = st.sidebar.text_input("New name:", key="rename_project_name")
        if new_name and new_name not in projects:
            projects[new_name] = projects.pop(selected_project)
            save_projects(projects)
            st.sidebar.success(f"Renamed to '{new_name}'!")
            set_current_chat([])

st.sidebar.markdown("---")
st.sidebar.header("Settings")

# API Key input with save button and warning if not set
api_key = st.sidebar.text_input("Groq API Key", type="password", value=st.session_state.get('groq_api_key', ''), key="api_key_input")
if st.sidebar.button("Save API Key"):
    st.session_state['groq_api_key'] = api_key
    st.sidebar.success("API key saved!")
if not st.session_state.get('groq_api_key'):
    st.sidebar.warning("Please enter your Groq API key to use the AI chat.")

# Model selection
st.sidebar.selectbox("Model", [DEFAULT_MODEL, "llama-3-8b-8192", "mixtral-8x7b-32768"], key="model")
# Temperature slider
st.sidebar.slider("Temperature", 0.0, 1.5, 0.7, 0.05, key="temperature")
# Theme selection
st.sidebar.selectbox("Theme", ["Light", "Dark", "Auto"], key="theme", help="Choose your preferred chat theme.")
# Font size
st.sidebar.slider("Font Size", 12, 24, 16, 1, key="font_size", help="Adjust chat font size.")
# Chat display options
st.sidebar.checkbox("Show Timestamps", value=True, key="show_timestamps")
st.sidebar.checkbox("Show Suggestions", value=True, key="show_suggestions")

st.sidebar.markdown("---")
if st.sidebar.button("Export Current Chat"):
    st.sidebar.download_button(
        label="Download Chat as JSON",
        data=export_chat(get_current_chat()),
        file_name="olivia_chat.json",
        mime="application/json"
    )
if st.sidebar.button("Import Chat (JSON)"):
    uploaded = st.sidebar.file_uploader("Upload chat JSON", type=["json"])
    if uploaded:
        content = uploaded.read().decode()
        ok, msg = import_chat(content)
        if ok:
            st.sidebar.success(msg)
        else:
            st.sidebar.error(msg)

# --- MAIN UI ---
st.title("Olivia's AI Companion 💖")
st.markdown(
    """
    <div style='font-size:1.1em;'>
    Hello Olivia! I'm your personal AI companion, created just for you. I'm here to chat about your passions like <b>medical research</b>, <b>plants</b>, or anything else on your mind.<br>
    <i>Lovingly set up for you. Ready to chat?</i>
    </div>
    """,
    unsafe_allow_html=True
)

# Handle form submission first
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_area("Type your message:", key="user_input", height=80)
    submitted = st.form_submit_button("Send")
    
if submitted and user_input.strip():
    add_message('user', user_input.strip())
    st.session_state['suggestions'] = []
    with st.spinner("Olivia's AI is thinking..."):
        ai_content, suggestions = call_groq_api(
            [
                {"role": m['role'], "content": m['content']} for m in get_current_chat()
            ],
            st.session_state['groq_api_key'],
            st.session_state['model'],
            st.session_state['temperature']
        )
        if ai_content:
            add_message('assistant', ai_content)
            st.session_state['suggestions'] = suggestions
            st.rerun()  # Force rerun to update display
        else:
            st.session_state['last_error'] = suggestions[0] if suggestions else "Unknown error"
            st.error(st.session_state['last_error'])

# Display chat history AFTER processing form
chat = get_current_chat()
for msg in st.session_state['current_chat']:
    render_message(msg)

# Suggestions
if st.session_state['suggestions']:
    st.markdown("<b>Suggestions:</b>", unsafe_allow_html=True)
    for s in st.session_state['suggestions']:
        if st.button(s, key=f"suggestion_{s}"):
            st.session_state['user_input'] = s

# Chat actions
col1, col2, col3 = st.columns(3)
if col1.button("💾 Save to Project Chat"):
    save_name = st.text_input("Save as project:", key="save_project_name")
    if save_name:
        projects[save_name] = chat.copy()
        save_projects(projects)
        st.success(f"Chat saved as '{save_name}'!")
if col2.button("🧹 Clear Chat"):
    clear_chat()
    st.success("Chat cleared!")
if col3.button("⬇️ Export Chat (JSON)"):
    st.download_button(
        label="Download Chat as JSON",
        data=export_chat(chat),
        file_name="olivia_chat.json",
        mime="application/json"
    )

# Special message for Olivia
if st.button("💖 A Quiet Note for Olivia"):
    st.info(
        """
        Olivia,
        
        I know things between us are a little undefined right now, but I want you to know how much I care about you and how grateful I am for the moments we share—no matter what label we put on it. You mean a lot to me, and I hope this little space brings you a smile whenever you need it.
        
        — John
        """
    )