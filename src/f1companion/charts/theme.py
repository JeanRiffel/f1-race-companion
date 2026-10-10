"""Shared chart colours and responsive layout defaults."""

import plotly.graph_objects as go

DEFAULT_TEAM_COLOR = "#888888"
COMPOUND_COLORS = {
    "SOFT": "#e53935",
    "MEDIUM": "#fbc02d",
    "HARD": "#eeeeee",
    "INTERMEDIATE": "#43a047",
    "WET": "#1e88e5",
    "UNKNOWN": "#888888",
}
LEGEND = dict(orientation="h", y=-0.2, x=0)


def empty_chart(height: int = 420) -> go.Figure:
    """Return a theme-neutral figure explaining that data is unavailable."""
    fig = go.Figure()
    fig.add_annotation(
        text="No data to show", x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False
    )
    fig.update_layout(height=height, legend=LEGEND)
    return fig
