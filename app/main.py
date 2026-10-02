"""Streamlit entry point for F1 Race Companion."""

import streamlit as st

DISCLAIMER = (
    "Unofficial project. Not associated with the Formula 1 companies. "
    "F1, FORMULA ONE and related marks are trademarks of Formula One Licensing B.V."
)


def main() -> None:
    """Render the landing page."""
    st.set_page_config(page_title="F1 Race Companion", page_icon="🏁", layout="wide")
    st.title("F1 Race Companion")
    st.write(
        "Pick a race and understand it in under a minute: what happened, why, and who was fastest."
    )
    st.info("Coming soon: race recap, tire strategy, and head-to-head comparisons.")
    st.caption(DISCLAIMER)


main()
