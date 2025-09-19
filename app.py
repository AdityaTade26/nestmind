import streamlit as st
import json
import time
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

# Configure page
st.set_page_config(
    page_title="Nested Minded Chat",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Data Models
@dataclass
class Message:
    id: str
    content: str
    role: str  # 'user' or 'assistant'
    timestamp: datetime
    parent_id: Optional[str] = None
    thread_id: str = "main"
    attachments: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []

@dataclass
class Thread:
    id: str
    name: str
    messages: List[Message]
    parent_thread_id: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

# Custom CSS for modern styling
def load_custom_css():
    st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Root variables for theming */
    :root {
        --primary-color: #6366f1;
        --primary-hover: #5855eb;
        --secondary-color: #f1f5f9;
        --background-light: #ffffff;
        --background-dark: #0f172a;
        --text-light: #1e293b;
        --text-dark: #f8fafc;
        --border-light: #e2e8f0;
        --border-dark: #334155;
        --card-light: #ffffff;
        --card-dark: #1e293b;
    }
    
    /* Main app styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 100%;
    }
    
    /* Custom chat message styling */
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 12px;
        animation: slideIn 0.3s ease-out;
        font-family: 'Inter', sans-serif;
        line-height: 1.6;
    }
    
    .user-message {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white;
        margin-left: 2rem;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25);
    }
    
    .assistant-message {
        background: var(--card-light);
        border: 1px solid var(--border-light);
        margin-right: 2rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }
    
    /* Dark mode message styling */
    [data-theme="dark"] .assistant-message {
        background: var(--card-dark);
        border-color: var(--border-dark);
        color: var(--text-dark);
    }
    
    @keyframes slideIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
    }
    
    [data-theme="dark"] .css-1d391kg {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.2s ease;
        font-family: 'Inter', sans-serif;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
    }
    
    /* Input field styling */
    .stTextArea textarea {
        border-radius: 12px;
        border: 2px solid var(--border-light);
        font-family: 'Inter', sans-serif;
        transition: border-color 0.2s ease;
    }
    
    .stTextArea textarea:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
    }
    
    /* File uploader styling */
    .uploadedFile {
        border-radius: 8px;
        background: var(--secondary-color);
        padding: 0.5rem;
        margin: 0.25rem 0;
    }
    
    /* Thread indicator */
    .thread-indicator {
        background: linear-gradient(90deg, #6366f1, #8b5cf6);
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
        display: inline-block;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .user-message { margin-left: 0.5rem; }
        .assistant-message { margin-right: 0.5rem; }
        .main .block-container { padding: 1rem; }
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--secondary-color);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--primary-color);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--primary-hover);
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
def initialize_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "threads" not in st.session_state:
        st.session_state.threads = {
            "main": Thread(
                id="main",
                name="Main Conversation",
                messages=[]
            )
        }
    
    if "current_thread" not in st.session_state:
        st.session_state.current_thread = "main"
    
    if "theme" not in st.session_state:
        st.session_state.theme = "light"
    
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = []

# Theme toggle
def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"

# File processing utilities
def process_uploaded_file(uploaded_file) -> Dict[str, Any]:
    """Process uploaded file and return metadata"""
    file_details = {
        "name": uploaded_file.name,
        "size": uploaded_file.size,
        "type": uploaded_file.type,
        "content": None
    }
    
    # Read file content based on type
    if uploaded_file.type.startswith('text/'):
        file_details["content"] = uploaded_file.getvalue().decode('utf-8')
    elif uploaded_file.type.startswith('image/'):
        file_details["content"] = base64.b64encode(uploaded_file.getvalue()).decode()
    
    return file_details

def display_file_preview(file_details: Dict[str, Any]):
    """Display file preview in the chat"""
    with st.expander(f"📎 {file_details['name']} ({file_details['size']} bytes)"):
        if file_details['type'].startswith('text/') and file_details['content']:
            st.code(file_details['content'][:500] + "..." if len(file_details['content']) > 500 else file_details['content'])
        elif file_details['type'].startswith('image/'):
            st.image(f"data:{file_details['type']};base64,{file_details['content']}")
        else:
            st.info(f"File type: {file_details['type']}")

# Message utilities
def add_message(content: str, role: str, thread_id: str = None, attachments: List = None, parent_id: str = None):
    """Add a message to the current thread"""
    if thread_id is None:
        thread_id = st.session_state.current_thread
    
    message = Message(
        id=f"msg_{int(time.time() * 1000)}",
        content=content,
        role=role,
        timestamp=datetime.now(),
        thread_id=thread_id,
        attachments=attachments or [],
        parent_id=parent_id
    )
    
    if thread_id in st.session_state.threads:
        st.session_state.threads[thread_id].messages.append(message)
    else:
        # Create new thread if it doesn't exist
        new_thread = Thread(
            id=thread_id,
            name=f"Thread {len(st.session_state.threads) + 1}",
            messages=[message]
        )
        st.session_state.threads[thread_id] = new_thread

def create_new_thread(parent_message_id: str = None) -> str:
    """Create a new thread"""
    thread_id = f"thread_{int(time.time() * 1000)}"
    thread_name = f"Thread {len(st.session_state.threads) + 1}"
    
    new_thread = Thread(
        id=thread_id,
        name=thread_name,
        messages=[],
        parent_thread_id=st.session_state.current_thread if parent_message_id else None
    )
    
    st.session_state.threads[thread_id] = new_thread
    return thread_id

# Sidebar components
def render_sidebar():
    """Render the main sidebar with tabs"""
    with st.sidebar:
        st.markdown("# 🧠 Nested Minded Chat")
        st.markdown("---")
        
        # Tab selection
        tab = st.selectbox(
            "Navigation",
            ["🏠 Home", "💬 Conversations", "🧵 Nested Threads", "📁 Files", "⚙️ Settings"],
            key="sidebar_tab"
        )
        
        if tab == "🏠 Home":
            render_home_tab()
        elif tab == "💬 Conversations":
            render_conversations_tab()
        elif tab == "🧵 Nested Threads":
            render_threads_tab()
        elif tab == "📁 Files":
            render_files_tab()
        elif tab == "⚙️ Settings":
            render_settings_tab()

def render_home_tab():
    """Render home tab content"""
    st.markdown("### Welcome to Nested Chat!")
    st.markdown("""
    **Features:**
    - 💬 Multi-threaded conversations
    - 📎 File attachments
    - 🔗 Message linking
    - 🌓 Dark/Light themes
    - 📱 Responsive design
    """)
    
    # Quick stats
    total_messages = sum(len(thread.messages) for thread in st.session_state.threads.values())
    st.metric("Total Messages", total_messages)
    st.metric("Active Threads", len(st.session_state.threads))

def render_conversations_tab():
    """Render conversations tab"""
    st.markdown("### Recent Conversations")
    
    for thread_id, thread in st.session_state.threads.items():
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(f"📝 {thread.name}", key=f"thread_btn_{thread_id}"):
                    st.session_state.current_thread = thread_id
                    st.rerun()
            with col2:
                st.caption(f"{len(thread.messages)} msgs")

def render_threads_tab():
    """Render nested threads tab"""
    st.markdown("### Thread Hierarchy")
    
    def render_thread_tree(thread_id: str, level: int = 0):
        thread = st.session_state.threads[thread_id]
        indent = "  " * level
        
        is_current = thread_id == st.session_state.current_thread
        icon = "🟢" if is_current else "⚫"
        
        if st.button(f"{indent}{icon} {thread.name}", key=f"tree_{thread_id}_{level}"):
            st.session_state.current_thread = thread_id
            st.rerun()
        
        # Find child threads
        for tid, t in st.session_state.threads.items():
            if t.parent_thread_id == thread_id:
                render_thread_tree(tid, level + 1)
    
    # Render main threads (those without parents)
    for thread_id, thread in st.session_state.threads.items():
        if thread.parent_thread_id is None:
            render_thread_tree(thread_id)

def render_files_tab():
    """Render files tab"""
    st.markdown("### File Management")
    
    if st.session_state.uploaded_files:
        for i, file_details in enumerate(st.session_state.uploaded_files):
            with st.expander(f"📎 {file_details['name']}"):
                st.json(file_details)
                if st.button(f"Remove", key=f"remove_file_{i}"):
                    st.session_state.uploaded_files.pop(i)
                    st.rerun()
    else:
        st.info("No files uploaded yet")

def render_settings_tab():
    """Render settings tab"""
    st.markdown("### Application Settings")
    
    # Theme toggle
    current_theme = st.session_state.theme
    if st.button(f"🌓 Switch to {'Dark' if current_theme == 'light' else 'Light'} Mode"):
        toggle_theme()
        st.rerun()
    
    st.markdown(f"**Current Theme:** {current_theme.title()}")
    
    # Other settings
    st.markdown("### Chat Settings")
    auto_scroll = st.checkbox("Auto-scroll to latest message", value=True)
    show_timestamps = st.checkbox("Show message timestamps", value=True)
    
    # Export/Import
    st.markdown("### Data Management")
    if st.button("📥 Export Chat Data"):
        export_data = {
            "threads": {tid: asdict(thread) for tid, thread in st.session_state.threads.items()},
            "current_thread": st.session_state.current_thread
        }
        st.download_button(
            label="💾 Download JSON",
            data=json.dumps(export_data, indent=2, default=str),
            file_name=f"nested_chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )

# Main chat interface
def render_chat_interface():
    """Render the main chat interface"""
    current_thread = st.session_state.threads.get(st.session_state.current_thread)
    
    if not current_thread:
        st.error("Current thread not found!")
        return
    
    # Thread header
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.markdown(f"### 💬 {current_thread.name}")
    with col2:
        if st.button("🧵 New Thread"):
            new_thread_id = create_new_thread()
            st.session_state.current_thread = new_thread_id
            st.rerun()
    with col3:
        st.caption(f"{len(current_thread.messages)} messages")
    
    # Chat messages
    chat_container = st.container()
    
    with chat_container:
        for message in current_thread.messages:
            with st.chat_message(message.role):
                # Message content
                st.markdown(message.content)
                
                # Attachments
                if message.attachments:
                    for attachment in message.attachments:
                        display_file_preview(attachment)
                
                # Message metadata
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    if message.parent_id:
                        st.caption(f"↳ Reply to {message.parent_id}")
                with col2:
                    st.caption(message.timestamp.strftime("%H:%M"))
                with col3:
                    if st.button("🔗", key=f"link_{message.id}", help="Link to this message"):
                        st.session_state.link_parent = message.id
    
    # Input area
    render_input_area()

def render_input_area():
    """Render the message input area"""
    with st.container():
        st.markdown("---")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Attach file",
            type=['txt', 'py', 'md', 'json', 'csv', 'png', 'jpg', 'jpeg', 'gif'],
            key="message_file_uploader"
        )
        
        # Message input
        message_input = st.text_area(
            "Type your message...",
            height=100,
            placeholder="Enter your message here. Use Markdown for formatting!",
            key="message_input"
        )
        
        # Buttons row
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            send_clicked = st.button("📤 Send Message", type="primary", use_container_width=True)
        
        with col2:
            new_thread_clicked = st.button("🧵 New Thread", use_container_width=True)
        
        with col3:
            if hasattr(st.session_state, 'link_parent'):
                link_clicked = st.button(f"🔗 Link to Parent", use_container_width=True)
            else:
                st.button("🔗 Link (Select parent)", disabled=True, use_container_width=True)
                link_clicked = False
        
        with col4:
            clear_clicked = st.button("🗑️ Clear", use_container_width=True)
        
        # Handle button clicks
        if send_clicked and message_input.strip():
            attachments = []
            
            # Process uploaded file
            if uploaded_file:
                file_details = process_uploaded_file(uploaded_file)
                attachments.append(file_details)
                st.session_state.uploaded_files.append(file_details)
            
            # Add user message
            parent_id = getattr(st.session_state, 'link_parent', None)
            add_message(
                content=message_input,
                role="user",
                attachments=attachments,
                parent_id=parent_id
            )
            
            # Simulate assistant response
            assistant_response = f"Thank you for your message! I received: '{message_input[:50]}...'" if len(message_input) > 50 else f"Thank you for your message: '{message_input}'"
            
            if attachments:
                assistant_response += f"\n\nI also received {len(attachments)} file(s): {', '.join([att['name'] for att in attachments])}"
            
            add_message(
                content=assistant_response,
                role="assistant"
            )
            
            # Clear states
            if hasattr(st.session_state, 'link_parent'):
                delattr(st.session_state, 'link_parent')
            
            st.rerun()
        
        if new_thread_clicked:
            new_thread_id = create_new_thread()
            st.session_state.current_thread = new_thread_id
            st.rerun()
        
        if link_clicked and hasattr(st.session_state, 'link_parent'):
            st.success(f"Next message will be linked to: {st.session_state.link_parent}")
        
        if clear_clicked:
            st.session_state.threads[st.session_state.current_thread].messages.clear()
            if hasattr(st.session_state, 'link_parent'):
                delattr(st.session_state, 'link_parent')
            st.rerun()

# Main application
def main():
    """Main application entry point"""
    # Load custom CSS
    load_custom_css()
    
    # Initialize session state
    initialize_session_state()
    
    # Apply theme
    if st.session_state.theme == "dark":
        st.markdown('<div data-theme="dark">', unsafe_allow_html=True)
    
    # Render sidebar
    render_sidebar()
    
    # Main content area
    with st.container():
        render_chat_interface()
    
    # Close theme div
    if st.session_state.theme == "dark":
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()