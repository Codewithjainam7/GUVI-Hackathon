"""
Honeypot Dashboard
Visual Command Center for the Agentic Honeypot System
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
import time

# Configuration
API_URL = "http://localhost:8000"
HEADERS = {"X-API-Key": "change-me-in-production"}

st.set_page_config(
    page_title="Honeypot Dashboard",
    page_icon="🍯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=5)
def fetch_status():
    try:
        r = requests.get(f"{API_URL}/health", timeout=2)
        return r.json()
    except:
        return {"status": "offline"}

@st.cache_data(ttl=5)
def fetch_safety_status():
    try:
        r = requests.get(f"{API_URL}/api/v1/safety/status", headers=HEADERS, timeout=2)
        if r.status_code == 200:
            return r.json()['data']
    except:
        pass
    return {"kill_switch_active": False, "safety_mode": "Unknown"}

# Sidebar
with st.sidebar:
    st.header("Control Panel")
    status = fetch_status()
    if status.get("status") == "healthy":
        st.success("🟢 System Online")
    else:
        st.error("🔴 System Offline")
        
    safety = fetch_safety_status()
    kill_switch = safety.get("kill_switch_active", False)
    
    if kill_switch:
        st.error("⛔ KILL SWITCH ACTIVE")
        if st.button("Deactivate API"):
            requests.post(f"{API_URL}/api/v1/kill-switch/deactivate", headers=HEADERS)
            st.rerun()
    else:
        if st.button("⛔ EMERGENCY STOP"):
            requests.post(f"{API_URL}/api/v1/kill-switch/activate", headers=HEADERS)
            st.rerun()
            
    st.divider()
    st.info("Agent Status")
    st.write("🕵️ Classification: **Groq**")
    st.write("💬 Response: **Groq**")
    st.write("🔍 Extraction: **Local LLaMA**")

# Main Content
tab1, tab2, tab3 = st.tabs(["📊 Live Metrics", "🕸️ Scam Network", "💬 Conversation Log"])

with tab1:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Engagements", "12", "+3")
    col2.metric("Scams Blocked", "1,245", "+15%")
    col3.metric("Intel Extracted", "89 Entities", "+5")
    col4.metric("Avg Response Time", "850ms", "-12%")
    
    # Mock Data for charts
    chart_data = pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=24, freq="H"),
        "scams": [x * 10 for x in range(24)]
    })
    
    st.subheader("Traffic Analysis")
    st.area_chart(chart_data.set_index("time"))

with tab2:
    st.header("Scammer Network Graph")
    
    # Generate mock graph since real data might be empty
    G = nx.Graph()
    scammers = ["+91-9876543210", "+91-9988776655", "lottery_winner@gmail", "support@fake-bank"]
    entities = ["UPI: scam@upi", "Acc: 123456", "Link: bit.ly/scam", "UPI: fake@paytm"]
    
    for s in scammers:
        G.add_node(s, type="scammer", color="red")
    for e in entities:
        G.add_node(e, type="entity", color="blue")
        
    G.add_edge(scammers[0], entities[0])
    G.add_edge(scammers[0], entities[1])
    G.add_edge(scammers[1], entities[0]) # Shared UPI!
    G.add_edge(scammers[2], entities[2])
    G.add_edge(scammers[3], entities[3])
    
    # Plotly Graph
    pos = nx.spring_layout(G)
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines')

    node_x = []
    node_y = []
    node_text = []
    node_color = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
        node_color.append('crimson' if G.nodes[node].get('type') == 'scammer' else 'royalblue')

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=node_text,
        textposition="top center",
        marker=dict(
            showscale=False,
            color=node_color,
            size=20,
            line_width=2))

    fig = go.Figure(data=[edge_trace, node_trace],
                 layout=go.Layout(
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=0,l=0,r=0,t=0),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.caption("🔴 Red: Scammer | 🔵 Blue: Extracted Entity (Shared nodes indicate organized rings)")

with tab3:
    st.header("Recent Conversations")
    
    # Mock conversation
    st.chat_message("user").write("Hello, I am from Microsoft.")
    st.chat_message("assistant").write("Oh hello dear... Microsoft? Is that the computer company?")
    st.chat_message("user").write("Yes. Your PC has a virus.")
    st.chat_message("assistant").write("A virus?! Oh my goodness... will it make me sick? I am already taking pills for my heart...")
    
    st.info("Connect to live DB for real-time feed.")
