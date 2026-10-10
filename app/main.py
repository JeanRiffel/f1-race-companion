"""Shared race selector, URL state, and navigation for the core views."""

from datetime import date

import streamlit as st

import services
from components.race_header import disclaimer_footer


def _query_int(name: str, default: int) -> int:
    try:
        return int(st.query_params.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def main() -> None:
    """Render the shared sidebar and execute the selected race view."""
    st.set_page_config(page_title="F1 Race Companion", page_icon="🏁", layout="wide")
    years = list(range(date.today().year, 2017, -1))
    previous = st.session_state.get("race_key")
    initial_year = previous[0] if previous else _query_int("year", years[0])
    year = st.session_state.get("selector_year", initial_year)
    if year not in years:
        year = years[0]
    with st.sidebar:
        st.header("F1 Race Companion")
        try:
            races = services.get_races(year)
            if races.empty:
                st.info(f"No completed races in {year} yet. Looking for an earlier season.")
                while races.empty and year > 2018:
                    year -= 1
                    races = services.get_races(year)
            if races.empty:
                st.info("No completed races are available. Please try again later.")
                disclaimer_footer()
                st.stop()
        except services.F1DataError as err:
            services.show_data_error(err)
        st.session_state["selector_year"] = year
        st.selectbox(
            "Year", years, key="selector_year", help="Lap data is available from 2018 onward."
        )
        rounds = races.RoundNumber.tolist()
        names = dict(zip(rounds, races.EventName, strict=True))
        default_round = previous[1] if previous and previous[0] == year else rounds[-1]
        if previous is None:
            default_round = _query_int("round", rounds[-1])
        if default_round not in rounds:
            default_round = rounds[-1]
        round_number = st.selectbox(
            "Race",
            rounds,
            index=rounds.index(default_round),
            format_func=lambda value: f"R{value}: {names[value]}",
            key=f"selector_round_{year}",
        )
        disclaimer_footer()
    race_key = (year, int(round_number))
    st.session_state["race_key"] = race_key
    query_snapshot = {name: st.query_params.get_all(name) for name in st.query_params}
    driver_query = {name: st.query_params[name] for name in ("d1", "d2") if name in st.query_params}
    if driver_query:
        st.session_state["driver_query"] = (race_key, driver_query)
    page = st.navigation(
        [
            st.Page("pages/recap.py", title="Recap", icon="🏁", default=True),
            st.Page("pages/strategy.py", title="Strategy", icon="🛞"),
            st.Page("pages/head_to_head.py", title="Head-to-head", icon="⚖️"),
        ]
    )
    st.query_params.update(query_snapshot)
    st.query_params["year"] = str(year)
    st.query_params["round"] = str(round_number)
    saved_query = st.session_state.get("driver_query")
    if saved_query and saved_query[0] == race_key:
        for name, driver in saved_query[1].items():
            if name not in st.query_params:
                st.query_params[name] = driver
    comparison = st.session_state.get("driver_selection")
    if comparison and comparison[0] == race_key:
        for name, driver in zip(("d1", "d2"), comparison[1:], strict=True):
            if name not in query_snapshot:
                st.query_params[name] = driver
    page.run()


main()
