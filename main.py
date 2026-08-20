import os
import warnings
import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

# Suppress warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Load environment variables
load_dotenv()

# Define tools
@tool
def calculator(a: float, b: float) -> str:
    """Useful for performing basic arithmetic calculations (addition) with two numbers."""
    return f"The sum of {a} and {b} is {a + b}"

@tool
def say_hello(name: str) -> str:
    """Useful for greeting a user."""
    return f"Hello {name}, I hope you are well today!"

# Page configuration
st.set_page_config(
    page_title="Grok AI Assistant",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 Grok AI Assistant")
st.write("A simple LangGraph agent running on Groq.")

# Sidebar Configuration
st.sidebar.title("Configuration")

# Free tier models available on Groq
free_models = [
    "qwen/qwen3.6-27b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it"
]

env_default_model = os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b")
if env_default_model not in free_models:
    # Default to qwen/qwen3.6-27b if the env model is not in the free models list
    env_default_model = "qwen/qwen3.6-27b"

default_model_index = free_models.index(env_default_model)

selected_model = st.sidebar.selectbox("Select Model", free_models, index=default_model_index)
temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=2.0, value=0.0, step=0.1)

if st.sidebar.button("Clear Chat History", use_container_width=True):
    st.session_state.messages = []
    st.rerun()

# Verification of API Key
groq_key = os.getenv("GROQ_API_KEY")
if not groq_key:
    st.error("⚠️ GROQ_API_KEY is not set. Please update the key in your .env file.")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render existing conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "tools" in msg:
            for tool_info in msg["tools"]:
                with st.expander(f"🛠️ Tool Call: {tool_info['name']}", expanded=False):
                    st.code(tool_info["output"])

# Chat input and response logic
if user_input := st.chat_input("Ask Grok something..."):
    # Append and show User Message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
        
    # Generate Assistant Response
    with st.chat_message("assistant"):
        # Setup the LangGraph Agent executor
        model = ChatGroq(model=selected_model, temperature=temperature)
        tools = [calculator, say_hello]
        agent_executor = create_react_agent(model, tools)
        
        response_placeholder = st.empty()
        full_response = ""
        tool_records = []
        
        with st.spinner("Thinking..."):
            try:
                # Stream agent output
                for chunk in agent_executor.stream(
                    {"messages": [HumanMessage(content=user_input)]}
                ):
                    # Check for tool invocations
                    if "tools" in chunk and "messages" in chunk["tools"]:
                        for tool_msg in chunk["tools"]["messages"]:
                            tool_name = tool_msg.name
                            tool_content = tool_msg.content
                            tool_records.append({"name": tool_name, "output": tool_content})
                            
                            with st.status(f"Running tool: `{tool_name}`...", expanded=True) as status:
                                st.write(f"**Output:** {tool_content}")
                                status.update(label=f"Tool `{tool_name}` complete", state="complete")
                                
                    # Check for agent responses
                    if "agent" in chunk and "messages" in chunk["agent"]:
                        for agent_msg in chunk["agent"]["messages"]:
                            if agent_msg.content:
                                full_response += agent_msg.content
                                response_placeholder.markdown(full_response)
                                
            except Exception as e:
                st.error(f"Error during agent execution: {e}")
                full_response += f"\n\n*(Error encountered: {e})*"
                response_placeholder.markdown(full_response)
                
        if not full_response and not tool_records:
            full_response = "I ran the request but didn't receive any text response."
            response_placeholder.markdown(full_response)
            
        # Append assistant message to conversation history
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "tools": tool_records
        })