"""Dashboard layout with dark theme and sidebar navigation."""
from __future__ import annotations

import streamlit as st


DARK_CSS = """
<style>
[data-testid="stSidebar"] { background-color: #0d0d0d; }
[data-testid="stHeader"] { background-color: transparent; }
.stApp { background-color: #0f0f0f; }
section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0d0d0d 0%, #1a1a1a 100%); }
h1, h2, h3 { color: #f0c040; }
.stMetric > div { background-color: #1a1a1a !important; border-radius: 8px; }
.stTextInput > div > div > input { background-color: #1a1a1a; color: #e8e6e3; border-color: #333; }
.stSelectbox > div > div { background-color: #1a1a1a; color: #e8e6e3; }
.stButton > button { background-color: #f0c040; color: #0d0d0d; font-weight: bold; border: none; border-radius: 4px; }
.stButton > button:hover { background-color: #e0b030; }
.stCheckbox > label { color: #e8e6e3; }
div[data-testid="stExpander"] { background-color: #1a1a1a; border-radius: 6px; }
"""


def inject_theme() -> None:
    st.markdown(DARK_CSS, unsafe_allow_html=True)


def render_sidebar() -> str:
    st.sidebar.image(
        "https://www.gstatic.com/devrel-devsite/prod/v29d53788b4ac13e5a60eea3ad82e0ed8e33e922c1d01a47a4f6be9e0c321ae3d/cloud/images/logo-cloud.svg",
        use_container_width=True,
    )
    st.sidebar.markdown("### ArcadePilot")
    st.sidebar.markdown("*Cloud Lab Assistant*")
    st.sidebar.markdown("---")

    page = st.sidebar.radio("Navigate", ["Overview", "Lab Assistant", "Browser", "Terminal", "Progress", "Settings"])
    return page
