"""Dashboard layout with dark theme and sidebar navigation."""
from __future__ import annotations

import streamlit as st


DARK_CSS = """
<style>
/* Base */
.stApp { background-color: #0f0f0f; color: #e8e6e3; }
h1, h2, h3, h4 { color: #f0c040 !important; font-weight: 600; }
h5, h6 { color: #b0a890 !important; }
p, label, span, div, li, td, th { color: #e8e6e3 !important; }

/* Sidebar */
[data-testid="stSidebar"] { background-color: #0d0d0d !important; border-right: 1px solid #2a2a2a; }
section[data-testid="stSidebar"] { background: #0d0d0d !important; }
.css-1d391kg { background: #0d0d0d !important; }

/* Metrics */
.stMetric { background-color: #1a1a1a !important; border-radius: 8px; padding: 12px 16px; }
.stMetric > div { background-color: transparent !important; }
.stMetric .css-1lcb7j4 { color: #e8e6e3 !important; }
.stMetric .css-1vkk5as { color: #f0c040 !important; font-size: 1.5em; }

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div:first-child > div,
.stNumberInput > div > div > input {
    background-color: #1a1a1a !important;
    color: #e8e6e3 !important;
    border-color: #333 !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #f0c040 !important;
}

/* Select boxes */
.stSelectbox > div:nth-child(2) > div { background-color: #1a1a1a !important; color: #e8e6e3 !important; }
.stSelectbox div[role="listbox"] { background-color: #1a1a1a !important; color: #e8e6e3 !important; }
.stSelectbox div[role="option"] { color: #e8e6e3 !important; }
.stSelectbox div[role="option"]:hover { background-color: #2a2a2a !important; }

/* Buttons */
.stButton > button {
    background-color: #f0c040 !important;
    color: #0d0d0d !important;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    padding: 8px 24px;
}
.stButton > button:hover { background-color: #e0b030 !important; transform: translateY(-1px); }
.stButton > button:disabled { background-color: #333 !important; color: #666 !important; }

/* Secondary buttons */
.stButton > button[kind="secondary"] {
    background-color: transparent !important;
    color: #f0c040 !important;
    border: 1px solid #f0c040 !important;
}
.stButton > button[kind="secondary"]:hover {
    background-color: rgba(240,192,64,0.1) !important;
}

/* Expander */
div[data-testid="stExpander"] {
    background-color: #1a1a1a !important;
    border-radius: 8px;
    border: 1px solid #2a2a2a !important;
}
div[data-testid="stExpander"] details { background: transparent !important; }
div[data-testid="stExpander"] summary { background: transparent !important; }

/* Code blocks */
.stCodeBlock { background-color: #1a1a1a !important; border-radius: 6px; }

/* Text inputs */
.streamlit-expanderHeader { background-color: #1a1a1a !important; }
.streamlit-expanderContent { background-color: transparent !important; }

/* Divider */
.stSlider > div > div > div { background-color: #333 !important; }
.stSlider > div > div > div > div { background-color: #f0c040 !important; }

/* Success/Error/WARNING banners */
.stAlert { border-radius: 8px; }
.stSuccess { background-color: rgba(76,175,80,0.15) !important; border: 1px solid #4caf50 !important; }
.stError { background-color: rgba(244,67,54,0.15) !important; border: 1px solid #f44336 !important; }
.stWarning { background-color: rgba(255,152,0,0.15) !important; border: 1px solid #ff9800 !important; }
.stInfo { background-color: rgba(33,150,243,0.15) !important; border: 1px solid #2196f3 !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0f0f0f; }
::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #555; }

/* File uploader */
.stFileUploader > div > div { background-color: #1a1a1a !important; }
.stFileUploader label { color: #e8e6e3 !important; }
</style>
"""


def inject_theme() -> None:
    st.markdown(DARK_CSS, unsafe_allow_html=True)


def render_sidebar() -> str:
    # App logo / header in sidebar
    st.sidebar.markdown("""
        <div style="text-align:center; padding:8px 0;">
            <div style="font-size:28px; font-weight:bold; color:#f0c040;">⚡ ArcadePilot</div>
            <div style="font-size:11px; color:#888; letter-spacing:2px;">CLOUD LAB ASSISTANT</div>
        </div>
    """, unsafe_allow_html=True)
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigate",
        ["📊 Overview", "🧪 Lab Assistant", "🌐 Browser", "💻 Terminal", "📈 Progress", "⚙️ Settings"],
        label_visibility="collapsed",
    )
    return page
