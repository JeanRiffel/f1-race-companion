"""Pure race classification, position history, and approximate events."""

import pandas as pd

from f1companion.data.schema import empty_frame

POSITIONS = dict(Driver="string", LapNumber="Int64", Position="Int64")
EVENTS = dict(Type="string", StartLap="Int64", EndLap="Int64", Description="string")
CLASSIFICATION = dict(
    Position="string",
    Driver="string",
    FullName="string",
    Team="string",
    Grid="Int64",
    PositionsGained="Int64",
    Status="string",
    Points="float64",
)


def position_by_lap(laps: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    """Return lap-end positions with lap zero for known starting grid positions."""
    history = laps.loc[laps.Position.notna(), list(POSITIONS)].copy()
    grid = results.loc[results.GridPosition.notna(), ["Driver", "GridPosition"]].rename(
        columns={"GridPosition": "Position"}
    )
    grid = grid.assign(LapNumber=0)
    return (
        pd.concat([grid, history], ignore_index=True)[list(POSITIONS)]
        .astype(POSITIONS)
        .sort_values(["Driver", "LapNumber"], kind="stable")
        .reset_index(drop=True)
    )


def final_results(results: pd.DataFrame) -> pd.DataFrame:
    """Return classification and positions gained in the supplied finishing order."""
    out = (
        results[
            ["ClassifiedPosition", "Driver", "FullName", "Team", "GridPosition", "Status", "Points"]
        ]
        .rename(columns={"ClassifiedPosition": "Position", "GridPosition": "Grid"})
        .copy()
    )
    out["PositionsGained"] = results.GridPosition - results.Position
    return out[list(CLASSIFICATION)].astype(CLASSIFICATION)


def key_events(laps: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    """Return neutralisations and retirements; lap status is approximate.

    A condition starting mid-lap marks that entire lap.
    """
    rows = []
    for label, pattern in [("Safety Car", "4"), ("Virtual Safety Car", "[67]"), ("Red Flag", "5")]:
        numbers = sorted(
            laps.loc[laps.TrackStatus.str.contains(pattern, na=False), "LapNumber"]
            .dropna()
            .unique()
        )
        ranges = []
        for number in numbers:
            number = int(number)
            if ranges and number == ranges[-1][1] + 1:
                ranges[-1][1] = number
            else:
                ranges.append([number, number])
        for start, end in ranges:
            span = f"lap {start}" if start == end else f"laps {start}-{end}"
            rows.append(
                dict(Type=label, StartLap=start, EndLap=end, Description=f"{label} on {span}")
            )
    for row in results.loc[results.ClassifiedPosition.eq("R").fillna(False)].itertuples():
        lap = 1 if pd.isna(row.LapsCompleted) else max(int(row.LapsCompleted), 1)
        rows.append(
            dict(
                Type="Retirement",
                StartLap=lap,
                EndLap=lap,
                Description=f"{row.FullName} ({row.Team}) retired after lap {lap}: {row.Status}",
            )
        )
    if not rows:
        return empty_frame(EVENTS)
    return (
        pd.DataFrame(rows)
        .astype(EVENTS)
        .sort_values(["StartLap", "Type"], kind="stable")
        .reset_index(drop=True)
    )


def driver_colors(results: pd.DataFrame) -> dict[str, str]:
    """Map driver abbreviations to the supplied team colours."""
    return dict(zip(results.Driver, results.TeamColor, strict=True))
