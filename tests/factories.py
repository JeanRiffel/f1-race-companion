"""Small project-schema race fixtures shared by core-view tests."""

from datetime import date

import pandas as pd

from f1companion.data import RaceData, RaceInfo, schema


def race_data() -> RaceData:
    """Build four drivers, six laps, three teams, a pit-lane start, and a retirement."""
    drivers = ["AAA", "BBB", "CCC", "DDD"]
    teams = ["Team One", "Team One", "Team Two", "Team Three"]
    results = pd.DataFrame(
        [
            dict(
                DriverNumber=str(i + 1),
                Driver=d,
                FullName=f"Driver {d}",
                Team=teams[i],
                TeamColor=["#112233", "#112233", "#445566", "#778899"][i],
                GridPosition=[2, 1, pd.NA, 4][i],
                Position=[1, 2, 3, pd.NA][i],
                ClassifiedPosition=["1", "2", "3", "R"][i],
                Status="Retired" if i == 3 else "Finished",
                Points=float(25 - i * 5),
                LapsCompleted=4 if i == 3 else 6,
            )
            for i, d in enumerate(drivers)
        ]
    ).astype(schema.RESULTS)
    rows = []
    for i, d in enumerate(drivers):
        for lap in range(1, 5 if i == 3 else 7):
            rows.append(
                dict(
                    Driver=d,
                    DriverNumber=str(i + 1),
                    Team=teams[i],
                    LapNumber=lap,
                    Position=pd.NA if i == 3 else i + 1,
                    LapTimeSeconds=90 + i + lap / 10,
                    Stint=1 if lap <= 2 else 2,
                    Compound="UNKNOWN" if lap == 1 else ("SOFT" if lap <= 2 else "HARD"),
                    TyreLife=float(lap),
                    FreshTyre=lap == 1,
                    IsPitInLap=i < 2 and lap == 2,
                    IsPitOutLap=i < 2 and lap == 3,
                    TrackStatus="41" if lap in (3, 4) else ("67" if lap == 6 else "1"),
                    IsAccurate=lap != 1,
                    Deleted=False,
                )
            )
    laps = (
        pd.DataFrame(rows)
        .astype(schema.LAPS)
        .sort_values(["LapNumber", "Driver"])
        .reset_index(drop=True)
    )
    return RaceData(
        RaceInfo(2023, 5, "Fixture Grand Prix", "Country", "Circuit", date(2023, 5, 7)),
        laps,
        results,
        schema.empty_frame(schema.TRACK_STATUS),
        schema.empty_frame(schema.RACE_CONTROL),
    )


def telemetry() -> pd.DataFrame:
    """Build two distance samples with known interpolation values."""
    return pd.DataFrame(
        dict(
            Distance=[0.0, 100.0],
            Speed=[100.0, 200.0],
            Throttle=[0.0, 100.0],
            Brake=[False, True],
            Gear=[2, 5],
        )
    ).astype(schema.TELEMETRY)
