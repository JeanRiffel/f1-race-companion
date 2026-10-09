"""FastF1 boundary: loading and friendly error translation."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date

import fastf1
import pandas as pd
from fastf1.exceptions import (
    DataNotLoadedError,
    InvalidSessionError,
    NoLapDataError,
    RateLimitExceededError,
)
from requests.exceptions import ConnectionError, Timeout

from .cache import enable_cache
from .errors import DataUnavailableError, F1DataError, RaceNotFoundError
from .models import RaceData, RaceInfo
from .normalize import (
    normalize_laps,
    normalize_race_control,
    normalize_results,
    normalize_schedule,
    normalize_telemetry,
    normalize_track_status,
)


def _get_session(year: int, round_number: int) -> fastf1.core.Session:
    return fastf1.get_session(year, round_number, "R")


def _get_schedule(year: int) -> pd.DataFrame:
    return fastf1.get_event_schedule(year, include_testing=False)


@contextmanager
def _translate(message: str, *, invalid_value: bool = False) -> Iterator[None]:
    try:
        yield
    except F1DataError:
        raise
    except InvalidSessionError as exc:
        raise RaceNotFoundError(message) from exc
    except ValueError as exc:
        if not invalid_value:
            raise
        raise RaceNotFoundError(message) from exc
    except RateLimitExceededError as exc:
        raise DataUnavailableError(
            "Data source is rate-limiting requests. Try again in a few minutes."
        ) from exc
    except (DataNotLoadedError, NoLapDataError) as exc:
        raise DataUnavailableError(
            "Lap data isn't available for this race yet. Try again later."
        ) from exc
    except (ConnectionError, Timeout) as exc:
        raise DataUnavailableError(
            "Cannot reach the data source. Check your connection and try again later."
        ) from exc


def list_races(year: int, *, today: date | None = None) -> pd.DataFrame:
    """List completed race dates in a season."""
    enable_cache()
    with _translate(f"No races found for {year}.", invalid_value=True):
        raw = _get_schedule(year)
    return normalize_schedule(raw, today if today is not None else date.today())


def _optional(session: fastf1.core.Session, name: str) -> pd.DataFrame | None:
    try:
        return getattr(session, name)
    except DataNotLoadedError:
        return None


def load_race(year: int, round_number: int) -> RaceData:
    """Load a race without the expensive telemetry payload."""
    enable_cache()
    message = f"No race found for round {round_number} of {year}."
    with _translate(message, invalid_value=True):
        session = _get_session(year, round_number)
    with _translate(message):
        session.load(laps=True, telemetry=False, weather=False, messages=True)
        if session.laps.empty:
            raise DataUnavailableError(
                "Lap data isn't available for this race yet. Try again later."
            )
        event = session.event
        info = RaceInfo(
            year,
            int(event["RoundNumber"]),
            str(event["EventName"]),
            str(event["Country"]),
            str(event["Location"]),
            pd.Timestamp(event["EventDate"]).date(),
        )
        return RaceData(
            info,
            normalize_laps(session.laps),
            normalize_results(session.results),
            normalize_track_status(_optional(session, "track_status")),
            normalize_race_control(_optional(session, "race_control_messages")),
        )


def load_fastest_lap_telemetry(year: int, round_number: int, driver: str) -> pd.DataFrame:
    """Load a driver's fastest valid lap as distance-indexed car samples."""
    enable_cache()
    message = f"No race found for round {round_number} of {year}."
    with _translate(message, invalid_value=True):
        session = _get_session(year, round_number)
    with _translate(message):
        session.load(laps=True, telemetry=True, weather=False, messages=False)
        lap = session.laps.pick_drivers(driver.upper()).pick_fastest()
        if lap is None:
            raise DataUnavailableError(f"No valid lap found for {driver} in this race.")
        out = normalize_telemetry(lap.get_car_data().add_distance())
        if out.empty:
            raise DataUnavailableError(f"Telemetry isn't available for {driver} in this race.")
        return out
