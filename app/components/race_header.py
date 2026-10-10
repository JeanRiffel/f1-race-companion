"""Race heading and shared disclaimer."""

import streamlit as st

from services import RaceInfo

DISCLAIMER = (
    "Unofficial project. Not associated with the Formula 1 companies. "
    "F1, FORMULA ONE and related marks are trademarks of Formula One Licensing B.V."
)


def race_header(info: RaceInfo) -> None:
    """Show the selected race's name, date, and location."""
    st.title(info.event_name)
    st.caption(
        f"{info.year} · Round {info.round_number} · {info.location}, {info.country} · "
        f"{info.date:%d %B %Y}"
    )


def disclaimer_footer() -> None:
    """Render the shared unofficial-project disclaimer."""
    st.caption(DISCLAIMER)
