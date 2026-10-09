"""Small source-shaped frames and fake sessions."""

import pandas as pd
import pytest


@pytest.fixture
def raw_laps():
    rows = []
    for lap in range(5, 0, -1):
        for driver, number in [("VER", "1"), ("HAM", "44"), ("LEC", "16")]:
            if driver == "LEC" and lap > 3:
                continue
            rows.append(
                dict(
                    Driver=driver,
                    DriverNumber=number,
                    Team="Team",
                    LapNumber=lap,
                    Position=None if driver == "LEC" else (1 if driver == "VER" else 2),
                    LapTime=pd.NaT if lap == 1 else pd.Timedelta(seconds=90 + lap),
                    Stint=1 if lap < 3 else 2,
                    Compound=None if lap == 1 else ("" if lap == 2 else "soft"),
                    TyreLife=float(lap),
                    FreshTyre=None if lap == 1 else True,
                    PitInTime=pd.Timedelta(seconds=200) if lap == 2 else pd.NaT,
                    PitOutTime=pd.Timedelta(seconds=220) if lap == 3 else pd.NaT,
                    TrackStatus="41" if lap == 3 else "1",
                    IsAccurate=None if lap == 1 else True,
                    Deleted=None if lap == 1 else False,
                )
            )
    return pd.DataFrame(rows)


@pytest.fixture
def raw_results():
    return pd.DataFrame(
        dict(
            DriverNumber=["16", "44", "1"],
            Abbreviation=["LEC", "HAM", "VER"],
            FullName=["Charles Leclerc", "Lewis Hamilton", "Max Verstappen"],
            TeamName=["Ferrari", "Mercedes", "Red Bull"],
            TeamColor=[None, "invalid", "ABCDEF"],
            GridPosition=[3, 0, 1],
            Position=[None, 2, 1],
            ClassifiedPosition=["R", "2", "1"],
            Status=["Retired", "Finished", "Finished"],
            Points=[None, 18, 25],
            Laps=[3, 5, 5],
        )
    )


@pytest.fixture
def raw_track():
    return pd.DataFrame(
        dict(
            Time=pd.to_timedelta([30, 0, 60], unit="s"),
            Status=["4", "1", "9"],
            Message=["SC", "Green", "Other"],
        )
    )


@pytest.fixture
def raw_control():
    return pd.DataFrame(
        dict(
            Time=pd.to_datetime(["2024-03-02 12:01", "2024-03-02 12:00"]),
            Lap=[2, 1],
            Category=["Flag", "Other"],
            Flag=["YELLOW", None],
            Message=["Yellow", "Start"],
        )
    )


@pytest.fixture
def raw_telemetry():
    return pd.DataFrame(
        dict(
            Distance=[100.0, 0.0],
            Speed=[200, 100],
            Throttle=[100, 50],
            Brake=[False, True],
            nGear=[5, 3],
        )
    )


@pytest.fixture
def raw_schedule():
    return pd.DataFrame(
        dict(
            RoundNumber=[3, 0, 2, 1],
            EventName=["Future", "Testing", "Boundary", "Past"],
            Country=["Country"] * 4,
            Location=["Track"] * 4,
            EventDate=pd.to_datetime(
                ["2024-03-10", "2024-01-01", "2024-03-02 15:00", "2024-02-01"], format="mixed"
            ),
        )
    )


class FakeCar:
    def __init__(self, raw):
        self.raw = raw

    def add_distance(self):
        return self.raw


class FakeLap:
    def __init__(self, raw):
        self.raw = raw

    def get_car_data(self):
        return FakeCar(self.raw)


class FakeLaps(pd.DataFrame):
    _metadata = ["selected", "fastest"]

    def pick_drivers(self, driver):
        self.selected = driver
        return self

    def pick_fastest(self):
        return self.fastest


class FakeSession:
    def __init__(self, laps, results, track, control, telemetry):
        self.laps = FakeLaps(laps)
        self.laps.fastest = FakeLap(telemetry)
        self.results = results
        self.track_status = track
        self.control = control
        self.event = dict(
            RoundNumber=1,
            EventName="Bahrain Grand Prix",
            Country="Bahrain",
            Location="Sakhir",
            EventDate=pd.Timestamp("2024-03-02"),
        )
        self.load_calls = []

    def load(self, **kwargs):
        self.load_calls.append(kwargs)

    @property
    def race_control_messages(self):
        if isinstance(self.control, Exception):
            raise self.control
        return self.control


@pytest.fixture
def session(raw_laps, raw_results, raw_track, raw_control, raw_telemetry):
    return FakeSession(raw_laps, raw_results, raw_track, raw_control, raw_telemetry)
