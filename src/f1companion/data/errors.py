"""Friendly errors for data consumers."""


class F1DataError(Exception):
    """Base error with a short message safe to display to users."""


class RaceNotFoundError(F1DataError):
    """The requested race does not exist."""


class DataUnavailableError(F1DataError):
    """The requested data is currently unavailable."""
