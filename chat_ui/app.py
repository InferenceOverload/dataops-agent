"""
Streamlit Chat Interface for DataOps Agent

A simple, user-friendly chat interface for interacting with the DataOps Agent.
"""

import streamlit as st
import requests
from typing import Dict, Any, List, Optional
import os
from datetime import datetime
import json


# ============================================================================
# Configuration
# ============================================================================

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="DataOps Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================================
# Helper Functions
# ============================================================================

def call_chat_api(message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Call the chat API endpoint"""
    try:
        response = requests.post(
            f"{API_URL}/api/v1/chat",
            json={
                "message": message,
                "session_id": session_id
            },
            timeout=300  # 5 minute timeout for long workflows
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None


def get_workflows() -> List[Dict[str, Any]]:
    """Get list of available workflows"""
    try:
        response = requests.get(f"{API_URL}/api/v1/workflows", timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("workflows", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to load workflows: {str(e)}")
        return []


def get_session_history(session_id: str) -> List[Dict[str, Any]]:
    """Get conversation history for a session"""
    try:
        response = requests.get(
            f"{API_URL}/api/v1/sessions/{session_id}/history",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get("history", [])
    except requests.exceptions.RequestException:
        return []


def check_api_health() -> Dict[str, Any]:
    """Check API health status"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException:
        return {"status": "unavailable"}


# ============================================================================
# Session State Initialization
# ============================================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "api_available" not in st.session_state:
    health = check_api_health()
    st.session_state.api_available = health.get("status") in ["healthy", "degraded"]


# ============================================================================
# Sidebar
# ============================================================================

with st.sidebar:
    st.image("https://via.placeholder.com/300x100.png?text=DataOps+Agent", use_container_width=True)

    st.header("Session Info")

    # API Status
    if st.session_state.api_available:
        st.success("✅ API Connected")
        health = check_api_health()
        with st.expander("API Health Details"):
            st.json(health)
    else:
        st.error("❌ API Unavailable")
        if st.button("Retry Connection"):
            health = check_api_health()
            st.session_state.api_available = health.get("status") in ["healthy", "degraded"]
            st.rerun()

    # Session ID
    if st.session_state.session_id:
        st.text(f"Session: {st.session_state.session_id[:8]}...")
        if st.button("📋 Copy Session ID"):
            st.code(st.session_state.session_id)
    else:
        st.info("No active session")

    # New Session Button
    if st.button("🔄 New Session", use_container_width=True):
        st.session_state.session_id = None
        st.session_state.messages = []
        st.rerun()

    st.divider()

    # Workflows Section
    st.header("Available Workflows")
    if st.session_state.api_available:
        workflows = get_workflows()

        if workflows:
            for wf in workflows:
                with st.expander(f"📊 {wf.get('name', 'Unknown')}"):
                    st.write(f"**Description:** {wf.get('description', 'N/A')}")
                    st.write(f"**Category:** {wf.get('category', 'N/A')}")
                    st.write(f"**Version:** {wf.get('version', 'N/A')}")

                    capabilities = wf.get('capabilities', [])
                    if capabilities:
                        st.write("**Capabilities:**")
                        for cap in capabilities:
                            st.write(f"• {cap}")

                    inputs = wf.get('required_inputs', [])
                    if inputs:
                        st.write("**Required Inputs:**")
                        for inp in inputs:
                            required = "✓" if inp.get('required') else "○"
                            st.write(f"{required} `{inp.get('name')}` ({inp.get('type')})")
        else:
            st.info("No workflows available")
    else:
        st.warning("Connect to API to see workflows")

    st.divider()

    # Example Queries
    st.header("Example Queries")
    example_queries = [
        "What can you do?",
        "Parse this JIL file for dependencies",
        "Analyze Oracle package structure",
        "Research multi-agent systems"
    ]

    for query in example_queries:
        if st.button(f"💬 {query}", use_container_width=True, key=f"example_{hash(query)}"):
            st.session_state.example_query = query


# ============================================================================
# Main Chat Interface
# ============================================================================

st.title("🤖 DataOps Agent")
st.caption("AI-powered data engineering workflow orchestration")

# API Unavailable Warning
if not st.session_state.api_available:
    st.error(f"""
    ⚠️ **Cannot connect to API at {API_URL}**

    Please ensure:
    1. The API server is running
    2. The URL is correct
    3. Network connectivity is available
    """)
    st.stop()

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

        # Display metadata for assistant messages
        if message["role"] == "assistant" and "metadata" in message:
            metadata = message["metadata"]

            # Create columns for metadata display
            col1, col2, col3 = st.columns(3)

            with col1:
                workflow = metadata.get("workflow", "N/A")
                st.caption(f"**Workflow:** {workflow}")

            with col2:
                success = metadata.get("success", False)
                status = "✅ Success" if success else "❌ Failed"
                st.caption(f"**Status:** {status}")

            with col3:
                exec_metadata = metadata.get("execution_metadata", {})
                exec_time = exec_metadata.get("execution_time_seconds")
                if exec_time:
                    st.caption(f"**Time:** {exec_time:.2f}s")

            # Detailed metadata expander
            with st.expander("📊 Execution Details"):
                st.json(metadata)

# Handle example query from sidebar
if "example_query" in st.session_state:
    prompt = st.session_state.example_query
    del st.session_state.example_query
else:
    # Chat input
    prompt = st.chat_input("Ask me anything about your data workflows...")

if prompt:
    # Add user message to UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call API
    with st.chat_message("assistant"):
        with st.spinner("🤔 Processing your request..."):
            response_data = call_chat_api(prompt, st.session_state.session_id)

            if response_data:
                # Update session ID
                if not st.session_state.session_id:
                    st.session_state.session_id = response_data.get("session_id")

                # Display response
                response_text = response_data.get("response", "No response")
                st.markdown(response_text)

                # Display metadata
                metadata = response_data.get("metadata", {})

                # Create columns for metadata display
                col1, col2, col3 = st.columns(3)

                with col1:
                    workflow = metadata.get("workflow", "N/A")
                    st.caption(f"**Workflow:** {workflow}")

                with col2:
                    success = metadata.get("success", False)
                    status = "✅ Success" if success else "❌ Failed"
                    st.caption(f"**Status:** {status}")

                with col3:
                    exec_metadata = metadata.get("execution_metadata", {})
                    exec_time = exec_metadata.get("execution_time_seconds")
                    if exec_time:
                        st.caption(f"**Time:** {exec_time:.2f}s")

                # Detailed metadata expander
                with st.expander("📊 Execution Details"):
                    st.json(metadata)

                # Store assistant message
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_text,
                    "metadata": metadata
                })
            else:
                st.error("Failed to get response from API")


# ============================================================================
# Footer
# ============================================================================

st.divider()

footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption(f"**API:** {API_URL}")

with footer_col2:
    if st.session_state.session_id:
        st.caption(f"**Session:** {st.session_state.session_id[:12]}...")

with footer_col3:
    st.caption(f"**Messages:** {len(st.session_state.messages)}")
