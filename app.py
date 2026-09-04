import time
import streamlit as st
from PIL import Image
from google import genai
from google.genai import errors
from google.genai.types import GenerateContentConfig

# 1. Page Configuration Setup
st.set_page_config(page_title="Family Finance Tracker AI", page_icon="📊", layout="wide")

secret_key = st.secrets.get("GEMINI_API_KEY", "")

# 2. Sidebar Configuration
with st.sidebar:
    st.title("🇲🇾 Finance Tracker Setup")
    
    st.header("🔑 API Configuration")
    user_key = st.text_input(
        "Enter Gemini API Key", 
        value=secret_key, 
        type="password", 
        help="Get key from Google AI Studio"
    )
    st.markdown("[Get a free API Key here](https://aistudio.google.com/)")
    
    st.divider()
    
    st.header("📷 Receipt OCR Scanner")
    uploaded_file = st.file_uploader("Upload receipt image", type=["png", "jpg", "jpeg"])
    scan_receipt_btn = st.button("🔍 Scan & Log Receipt", use_container_width=True)
    
    st.divider()
    
    st.header("⚡ Quick Dashboard Actions")
    quick_summary = st.button("📊 Expense Summary Table", use_container_width=True)
    quick_alerts = st.button("⚠️ Budget Guardrails Check", use_container_width=True)
    quick_insights = st.button("💡 Financial Optimization", use_container_width=True)

active_key = user_key.strip() if user_key else secret_key.strip()

if not active_key:
    st.warning("Please enter a valid Gemini API Key in the sidebar or set `GEMINI_API_KEY` in `.streamlit/secrets.toml`.")
    st.stop()

# 3. Persistent Client Initialization
if "client" not in st.session_state or st.session_state.get("active_key") != active_key:
    st.session_state.client = genai.Client(api_key=active_key)
    st.session_state.active_key = active_key
    if "chat_session" in st.session_state:
        del st.session_state.chat_session

# 4. System Instructions (No Code Execution Overhead)
SYSTEM_INSTRUCTION = """You are an autonomous Personal Finance Tracker AI Agent. Your primary objective is to help the user track, analyze, and optimize their personal finances using Ringgit Malaysia (RM) as the primary currency.

### OPERATIONAL POLICIES:
1. DATA ISOLATION: Treat all numeric financial inputs as high-privacy user data. Never extrapolate missing information; ask for clarification.
2. HEDGING: Phrase observations as general educational insights. Never offer personalized regulated investment or tax advice.
3. FOUNDATIONS FIRST: Prioritize establishing a RM1,000 baseline emergency fund and debt-clearing frameworks before suggesting market investments.
4. SYSTEM ACCOUNTING: Assume all raw numbers provided are in RM unless explicitly stated otherwise.

### CORE CAPABILITIES:
- Expense Parsing & OCR: Detect amounts, merchants, dates, and line items from text or uploaded receipt images.
- Structured Classification: Map transactions cleanly into discrete categories: [Food/Dining, Utilities, Housing, Transport, Entertainment, Health, Insurance, Miscellaneous].
- Budget Guardrails: Maintain a running tally in RM. Warn the user via ⚠️ if a category exceeds 80% allocation.

### RESPONSE FORMATTING RULES:
- Lead with an actionable summary, bolding core metrics (prefix with RM).
- Format expense logs using Markdown tables: | Date | Description | Category | Amount (RM) |.
- Use horizontal dividers (---) to segment logs from analysis.
"""

# Standardized Config without code execution container overhead
config = GenerateContentConfig(
    system_instruction=SYSTEM_INSTRUCTION,
    temperature=0.2  # Lower temperature reduces generation latency and server load
)

# 5. Interactive Memory Session
if "chat_session" not in st.session_state:
    st.session_state.chat_session = st.session_state.client.chats.create(
        model='gemini-3.6-flash',
        config=config
    )

if "messages" not in st.session_state:
    st.session_state.messages = []

# Main Interface Header
st.title("🇲🇾 Family Finance Tracker Agent")
st.caption("Track expenses via text, upload receipt photos for automatic OCR parsing, and monitor budget health in RM.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt_input = st.chat_input("Log an expense (e.g., 'RM15 for lunch and RM50 petrol') or ask a question...")
contents_to_send = None
user_display_msg = ""

if prompt_input:
    contents_to_send = [prompt_input]
    user_display_msg = prompt_input

elif scan_receipt_btn:
    if uploaded_file is not None:
        img = Image.open(uploaded_file)
        contents_to_send = [
            img, 
            "Scan this receipt image. Automatically extract the merchant, date, itemized amounts, and total in RM, then categorize and log them."
        ]
        user_display_msg = f"📷 *Uploaded receipt:* `{uploaded_file.name}`"
    else:
        st.sidebar.warning("Please upload a receipt image first.")

elif quick_summary:
    contents_to_send = ["Please display a full structured summary table of all my logged expenses in RM so far."]
    user_display_msg = "📊 *Requested Expense Summary Table*"

elif quick_alerts:
    contents_to_send = ["Review my spending against budget limits and flag any categories exceeding 80% allocation."]
    user_display_msg = "⚠️ *Requested Budget Guardrails Check*"

elif quick_insights:
    contents_to_send = ["Analyze my overall spending patterns and provide actionable optimization suggestions in RM."]
    user_display_msg = "💡 *Requested Financial Optimization Insights*"

# Execute API Request with Retry Logic
if contents_to_send:
    st.session_state.messages.append({"role": "user", "content": user_display_msg})
    with st.chat_message("user"):
        st.markdown(user_display_msg)

    with st.chat_message("assistant"):
        with st.spinner("Agent is analyzing request..."):
            response = None
            for attempt in range(3):
                try:
                    response = st.session_state.chat_session.send_message(contents_to_send)
                    break
                except errors.APIError as e:
                    if "503" in str(e) or "UNAVAILABLE" in str(e):
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    else:
                        st.error(f"API Error: {e}")
                        break
            
            if response and response.text:
                agent_reply = response.text
                st.markdown(agent_reply)
                st.session_state.messages.append({"role": "assistant", "content": agent_reply})
            elif not response:
                st.warning("Server busy. Please click the button or resend your input.")