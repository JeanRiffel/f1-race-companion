"""Pure tyre stints and pit-stop summaries."""

import pandas as pd

from f1companion.data.schema import empty_frame

STINTS = dict(
    Driver="string",
    Team="string",
    Stint="Int64",
    Compound="string",
    StartLap="Int64",
    EndLap="Int64",
    LapCount="Int64",
)
STOPS = dict(Driver="string", LapNumber="Int64", StopNumber="Int64")


def stints(laps: pd.DataFrame) -> pd.DataFrame:
    """Summarise stint boundaries and the first known compound in lap order."""
    rows = []
    valid = laps.dropna(subset=["Stint", "LapNumber"]).sort_values("LapNumber", kind="stable")
    for (driver, stint), group in valid.groupby(["Driver", "Stint"], sort=True):
        known = group.Compound.dropna()
        known = known.loc[known.ne("UNKNOWN")]
        start, end = int(group.LapNumber.min()), int(group.LapNumber.max())
        rows.append(
            dict(
                Driver=driver,
                Team=group.Team.iloc[0],
                Stint=stint,
                Compound=known.iloc[0] if not known.empty else "UNKNOWN",
                StartLap=start,
                EndLap=end,
                LapCount=end - start + 1,
            )
        )
    return pd.DataFrame(rows, columns=list(STINTS)).astype(STINTS) if rows else empty_frame(STINTS)


def pit_stops(laps: pd.DataFrame) -> pd.DataFrame:
    """Return pit in-laps numbered chronologically within each driver."""
    out = laps.loc[laps.IsPitInLap.fillna(False), ["Driver", "LapNumber"]].copy()
    out = out.sort_values(["Driver", "LapNumber"], kind="stable")
    out["StopNumber"] = out.groupby("Driver").cumcount() + 1
    return out.astype(STOPS).reset_index(drop=True)


def pit_stop_summary(stops: pd.DataFrame, results: pd.DataFrame) -> pd.DataFrame:
    """Return counts and stop laps in finishing order, including zero-stop drivers."""
    rows = []
    for driver in results.Driver:
        numbers = stops.loc[stops.Driver.eq(driver), "LapNumber"].dropna().tolist()
        rows.append(
            dict(Driver=driver, Stops=len(numbers), Laps=", ".join(map(str, numbers)) or "-")
        )
    return pd.DataFrame(rows, columns=["Driver", "Stops", "Laps"]).astype(
        dict(Driver="string", Stops="Int64", Laps="string")
    )
