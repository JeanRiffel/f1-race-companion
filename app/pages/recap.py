"""Final classification, position history, and key race events."""

import streamlit as st

import services
from components.race_header import race_header
from f1companion.analysis import driver_colors, final_results, key_events, position_by_lap
from f1companion.charts import position_chart


def render() -> None:
    """Render the selected race recap, including explanations for casual fans."""
    try:
        race = services.get_race(*st.session_state["race_key"])
    except services.F1DataError as err:
        services.show_data_error(err)
    race_header(race.info)
    st.subheader("Final classification")
    st.caption(
        "Grid is the starting position; positions gained is grid minus finishing position. "
        "A dash in Grid means a pit-lane start or missing data."
    )
    if race.results.empty:
        st.info("Final classification is unavailable for this race.")
    else:
        st.dataframe(
            final_results(race.results),
            hide_index=True,
            column_config={
                "Points": st.column_config.NumberColumn("Points", format="%.0f"),
                "PositionsGained": st.column_config.NumberColumn("Positions gained", format="%+d"),
            },
        )
    st.subheader("How the race unfolded")
    st.caption(
        "Lines show each driver's position at the end of every lap; lap 0 is the starting grid."
    )
    if race.laps.empty:
        st.info("Lap-by-lap positions are unavailable for this race.")
    else:
        positions = position_by_lap(race.laps, race.results)
        if positions.empty:
            st.info("No recorded positions are available for this race.")
        else:
            st.plotly_chart(position_chart(positions, driver_colors(race.results)), width="stretch")
    st.subheader("Key events")
    st.caption("Events use approximate lap-level timing and recorded retirements.")
    events = key_events(race.laps, race.results)
    if events.empty:
        st.info("No safety cars or retirements recorded.")
    else:
        st.dataframe(events, hide_index=True)
    with st.expander("What do these mean?"):
        st.write("Safety Car: cars follow a safety vehicle while a hazard is cleared.")
        st.write("Virtual Safety Car: drivers slow to a controlled pace without a safety vehicle.")
        st.write("Red Flag: the session is stopped because the track is unsafe.")


render()
