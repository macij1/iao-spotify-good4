import streamlit as st

from emo_core import init_session_state, load_css, render_header
from interface.ui import render_analyze_tab, render_compare_tab


# =========================================================
# Page config & global init
# =========================================================

st.set_page_config(
    page_title="EmoLyrics AI",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Ensure session_state keys exist
init_session_state()

# Load CSS once
load_css()


# =========================================================
# Main
# =========================================================

def main() -> None:
    """Main entrypoint for the Streamlit app."""
    render_header()

    tab_analyze, tab_compare = st.tabs(
        ["Analyze your lyrics", "Compare versions of lyrics"]
    )

    with tab_analyze:
        render_analyze_tab()

    with tab_compare:
        render_compare_tab()


if __name__ == "__main__":
    main()
