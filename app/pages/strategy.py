"""Tyre strategy and pit-stop counts for the selected race."""

import streamlit as st

import services
from components.race_header import race_header
from f1companion.analysis import pit_stop_summary, pit_stops, stints
from f1companion.charts import strategy_chart


def render() -> None:
    """Render stint timelines and pit-stop summaries without page-level wrangling."""
    try:
        race = services.get_race(*st.session_state["race_key"])
    except services.F1DataError as err:
        services.show_data_error(err)
    race_header(race.info)
    st.subheader("Tyre strategy")
    st.caption(
        "Each bar is a stint on one set of tyres: soft is fastest but wears quickest; "
        "hard is slower but lasts longer."
    )
    if race.laps.empty:
        st.info("Tyre and pit-stop data are unavailable for this race.")
        return
    stint_data = stints(race.laps)
    if stint_data.empty:
        st.info("No tyre stints are recorded for this race.")
    else:
        driver_order = (
            race.results.Driver.tolist()
            if not race.results.empty
            else stint_data.Driver.unique().tolist()
        )
        st.plotly_chart(strategy_chart(stint_data, driver_order), width="stretch")
    st.subheader("Pit stops")
    st.caption(
        "Stop laps identify when drivers entered the pits; counts include drivers with no stops."
    )
    if race.results.empty:
        st.info(
            "Driver classification is unavailable, so a complete pit-stop summary cannot be shown."
        )
    else:
        st.dataframe(pit_stop_summary(pit_stops(race.laps), race.results), hide_index=True)


render()
