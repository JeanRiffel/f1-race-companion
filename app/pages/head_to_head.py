"""Compare two drivers' quickest race laps and car telemetry."""

import streamlit as st

import services
from components.race_header import race_header
from f1companion.analysis import compare_telemetry, driver_colors, fastest_laps, format_lap_time
from f1companion.charts import telemetry_chart


def render() -> None:
    """Render driver selection, valid fastest-lap metrics, and telemetry traces."""
    race_key = st.session_state["race_key"]
    try:
        race = services.get_race(*race_key)
    except services.F1DataError as err:
        services.show_data_error(err)
    race_header(race.info)
    st.subheader("Head-to-head")
    st.caption("Choose two drivers to compare their fastest valid laps of this race.")
    if race.results.empty:
        st.info("Driver classification is unavailable for this race.")
        return
    drivers = race.results.Driver.tolist()
    names = {row.Driver: row.FullName for row in race.results.itertuples()}
    saved = st.session_state.get("driver_selection")
    defaults = (
        saved[1:]
        if saved and saved[0] == race_key
        else (drivers[0], drivers[min(1, len(drivers) - 1)])
    )
    chosen = []
    for index, (label, param) in enumerate([("Driver A", "d1"), ("Driver B", "d2")]):
        default = st.query_params.get(param, defaults[index])
        if default not in drivers:
            default = drivers[min(index, len(drivers) - 1)]
        chosen.append(
            st.selectbox(
                label,
                drivers,
                index=drivers.index(default),
                format_func=lambda driver: f"{driver} — {names[driver]}",
                key=f"driver_{param}_{race_key[0]}_{race_key[1]}",
            )
        )
    driver_a, driver_b = chosen
    st.session_state["driver_selection"] = (race_key, driver_a, driver_b)
    st.query_params["d1"], st.query_params["d2"] = driver_a, driver_b
    if driver_a == driver_b:
        st.warning("Pick two different drivers.")
        return
    quickest = fastest_laps(race.laps)
    selected_laps = {}
    for driver, column in zip(chosen, st.columns(2), strict=True):
        with column:
            lap = quickest.loc[quickest.Driver.eq(driver)]
            if lap.empty:
                st.info(f"No valid timed lap is available for {driver}.")
            else:
                row = lap.iloc[0]
                selected_laps[driver] = row
                st.metric(f"{driver} fastest lap", format_lap_time(row.LapTimeSeconds))
                st.caption(f"Lap {row.LapNumber} · {row.Compound}")
    if len(selected_laps) == 2:
        gap = selected_laps[driver_b].LapTimeSeconds - selected_laps[driver_a].LapTimeSeconds
        st.caption(f"{driver_b} minus {driver_a}: {gap:+.3f} seconds.")
    st.subheader("Fastest-lap telemetry")
    st.caption(
        "Speed is in km/h; throttle is how far the accelerator is pressed; brake is on/off. "
        "These are each driver's fastest race laps, which may use different tyres and fuel loads. "
        "Timing metrics exclude inaccurate or deleted laps; telemetry uses the recorded "
        "personal-best lap, which can differ when timing data is incomplete."
    )
    if len(selected_laps) < 2:
        st.info("Telemetry comparison needs a valid timed lap for both drivers.")
        return
    samples = []
    failed = False
    for driver in chosen:
        try:
            samples.append(services.get_telemetry(*race_key, driver))
        except services.F1DataError as err:
            st.error(f"{driver}: {err}")
            failed = True
    if failed:
        st.caption("Try another driver or retry later when telemetry is available.")
        return
    comparison = compare_telemetry(*samples)
    if comparison.empty:
        st.info("There are too few telemetry samples to compare these laps.")
        return
    colors = driver_colors(race.results)
    st.plotly_chart(
        telemetry_chart(comparison, driver_a, driver_b, colors[driver_a], colors[driver_b]),
        width="stretch",
    )


render()
