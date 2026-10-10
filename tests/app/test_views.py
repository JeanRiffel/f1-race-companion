"""Render real navigation, URL state, and partial-data paths using AppTest."""

from datetime import date

import pandas as pd
import pytest
from conftest import APP
from factories import race_data, telemetry
from streamlit.testing.v1 import AppTest


def param(app, name):
    """Return a query param as a list; AppTest returns a bare string in older Streamlit."""
    value = app.query_params[name]
    return [value] if isinstance(value, str) else list(value)


def shell(**query):
    app = AppTest.from_file(str(APP / "main.py"), default_timeout=15)
    app.query_params.update(query)
    return app.run()


@pytest.mark.parametrize(
    "page,heading",
    [
        ("recap", "Final classification"),
        ("strategy", "Tyre strategy"),
        ("head_to_head", "Head-to-head"),
    ],
)
def test_each_page(app_services, page, heading):
    app = shell(year="2023", round="5")
    if page != "recap":
        app.switch_page(f"pages/{page}.py").run()
    assert not app.exception
    assert app.title[0].value == "Fixture Grand Prix"
    assert heading in [item.value for item in app.subheader]
    if page == "recap":
        assert len(app.dataframe) == 2
    elif page == "strategy":
        assert app.dataframe[0].value.Stops.tolist() == [1, 1, 0, 0]
    else:
        assert len(app.metric) == 2
        assert len(app.get("plotly_chart")) == 1


@pytest.mark.parametrize("year,round_number", [("abc", "999"), ("2017", "abc"), ("9999", "-1")])
def test_bad_query_falls_back(app_services, year, round_number):
    app = shell(year=year, round=round_number, custom="kept")
    assert not app.exception
    assert app.session_state["race_key"] == (date.today().year, 5)
    assert param(app, "custom") == ["kept"]


def test_query_round_trip(app_services):
    app = shell(year="2023", round="1", d1="CCC", d2="BBB")
    assert app.session_state["race_key"] == (2023, 1)
    app.switch_page("pages/head_to_head.py").run()
    assert not app.exception
    assert app.session_state["driver_selection"] == ((2023, 1), "CCC", "BBB")
    copied = dict(app.query_params)
    second = AppTest.from_file(str(APP / "main.py"), default_timeout=15)
    second.query_params.update(copied)
    second.run().switch_page("pages/head_to_head.py").run()
    assert not second.exception
    assert second.session_state["race_key"] == (2023, 1)
    assert second.session_state["driver_selection"] == ((2023, 1), "CCC", "BBB")


def test_selection_survives_navigation_and_param_clear(app_services):
    app = shell(year="2023", round="1")
    app.switch_page("pages/head_to_head.py").run()
    for widget in app.selectbox:
        if widget.label == "Driver A":
            widget.set_value("CCC")
    app.run()
    app.query_params.clear()
    app.switch_page("pages/strategy.py").run()
    assert not app.exception
    assert app.session_state["race_key"] == (2023, 1)
    app.query_params.clear()
    app.switch_page("pages/head_to_head.py").run()
    assert not app.exception
    assert app.session_state["driver_selection"] == ((2023, 1), "CCC", "BBB")
    assert param(app, "d1") == ["CCC"]


def test_shell_restores_params_after_clear(app_services):
    app = shell(year="2023", round="1", custom=["one", "two"])
    app.session_state["driver_selection"] = ((2023, 1), "CCC", "BBB")
    app.query_params.clear()
    app.run()
    assert not app.exception
    assert param(app, "year") == ["2023"]
    assert param(app, "round") == ["1"]
    assert param(app, "d1") == ["CCC"]
    assert param(app, "d2") == ["BBB"]


def test_shell_preserves_other_params(app_services):
    app = shell(year="2023", round="1", custom=["one", "two"])
    app.selectbox(key="selector_round_2023").set_value(5).run()
    assert not app.exception
    assert param(app, "custom") == ["one", "two"]


def test_year_and_round_changes(app_services):
    app = shell(year="2023", round="1")
    app.selectbox(key="selector_year").set_value(2022).run()
    assert not app.exception
    assert app.session_state["race_key"] == (2022, 5)
    app.selectbox(key="selector_round_2022").set_value(1).run()
    assert app.session_state["race_key"] == (2022, 1)
    assert param(app, "round") == ["1"]


def test_empty_season_fallback(app_services, monkeypatch):
    current = date.today().year
    monkeypatch.setattr(
        app_services,
        "get_races",
        lambda year: (
            pd.DataFrame({"RoundNumber": [], "EventName": []})
            if year == current
            else pd.DataFrame({"RoundNumber": [5], "EventName": ["Fixture Grand Prix"]})
        ),
    )
    app = shell()
    assert not app.exception
    assert app.session_state["race_key"] == (current - 1, 5)
    assert app.selectbox(key="selector_year").value == current - 1
    assert app.info


def test_all_empty_seasons(app_services, monkeypatch):
    monkeypatch.setattr(
        app_services, "get_races", lambda year: pd.DataFrame({"RoundNumber": [], "EventName": []})
    )
    app = shell()
    assert not app.exception
    assert any("No completed races are available" in item.value for item in app.info)


@pytest.mark.parametrize("page", ["recap", "strategy", "head_to_head"])
def test_friendly_race_error(app_services, monkeypatch, page):
    app = shell()

    def fail(*args):
        raise app_services.F1DataError("Race data unavailable")

    monkeypatch.setattr(app_services, "get_race", fail)
    if page != "recap":
        app.switch_page(f"pages/{page}.py")
    app.run()
    assert not app.exception
    assert app.error[0].value == "Race data unavailable"


def test_calendar_error(app_services, monkeypatch):
    def fail(*args):
        raise app_services.F1DataError("Calendar unavailable")

    monkeypatch.setattr(app_services, "get_races", fail)
    app = shell()
    assert not app.exception
    assert app.error[0].value == "Calendar unavailable"


def test_same_driver_stops_telemetry(app_services, monkeypatch):
    app = shell().switch_page("pages/head_to_head.py").run()

    def forbidden(*args):
        raise AssertionError("telemetry should not be loaded")

    monkeypatch.setattr(app_services, "get_telemetry", forbidden)
    for widget in app.selectbox:
        if widget.label == "Driver B":
            widget.set_value("AAA")
    app.run()
    assert not app.exception
    assert app.warning[0].value == "Pick two different drivers."
    assert len(app.get("plotly_chart")) == 0


@pytest.mark.parametrize("failed_driver", ["AAA", "BBB"])
def test_telemetry_error_per_driver(app_services, monkeypatch, failed_driver):
    seen = []

    def load(year, round_number, driver):
        seen.append(driver)
        if driver == failed_driver:
            raise app_services.F1DataError("Telemetry unavailable")
        return telemetry()

    monkeypatch.setattr(app_services, "get_telemetry", load)
    app = shell().switch_page("pages/head_to_head.py").run()
    assert not app.exception
    assert seen == ["AAA", "BBB"]
    assert app.error[0].value == f"{failed_driver}: Telemetry unavailable"
    assert len(app.get("plotly_chart")) == 0


@pytest.mark.parametrize("page", ["recap", "strategy", "head_to_head"])
def test_partial_data(app_services, monkeypatch, page):
    race = race_data()
    partial = app_services.RaceData(
        race.info, race.laps.iloc[:0], race.results.iloc[:0], race.track_status, race.race_control
    )
    monkeypatch.setattr(app_services, "get_race", lambda *args: partial)
    app = shell()
    if page != "recap":
        app.switch_page(f"pages/{page}.py").run()
    assert not app.exception
    assert app.info
    assert len(app.get("plotly_chart")) == 0


def test_no_valid_lap(app_services, monkeypatch):
    race = race_data()
    race.laps.loc[race.laps.Driver.eq("AAA"), "IsAccurate"] = False
    monkeypatch.setattr(app_services, "get_race", lambda *args: race)
    app = shell().switch_page("pages/head_to_head.py").run()
    assert not app.exception
    assert any("No valid timed lap" in item.value for item in app.info)
    assert len(app.get("plotly_chart")) == 0


def test_one_driver(app_services, monkeypatch):
    race = race_data()
    partial = app_services.RaceData(
        race.info, race.laps, race.results.iloc[:1], race.track_status, race.race_control
    )
    monkeypatch.setattr(app_services, "get_race", lambda *args: partial)
    app = shell().switch_page("pages/head_to_head.py").run()
    assert not app.exception
    assert app.warning[0].value == "Pick two different drivers."
