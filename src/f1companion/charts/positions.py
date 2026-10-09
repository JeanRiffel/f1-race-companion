"""Lap-by-lap position chart."""

import pandas as pd
import plotly.graph_objects as go

from .theme import DEFAULT_TEAM_COLOR, LEGEND, empty_chart


def position_chart(positions: pd.DataFrame, colors: dict[str, str]) -> go.Figure:
    """Plot race positions with the leader at the top and dashed teammates."""
    if positions.empty:
        return empty_chart()
    fig = go.Figure()
    used = set()
    for driver, group in positions.groupby("Driver", sort=True):
        group = group.sort_values("LapNumber")
        color = colors.get(driver, DEFAULT_TEAM_COLOR)
        fig.add_trace(
            go.Scatter(
                x=group.LapNumber.tolist(),
                y=group.Position.tolist(),
                mode="lines",
                name=driver,
                line=dict(color=color, dash="dash" if color in used else "solid"),
                hovertemplate=driver + "<br>Lap %{x}<br>Position %{y}<extra></extra>",
            )
        )
        used.add(color)
    fig.update_layout(
        height=480,
        legend=LEGEND,
        margin=dict(l=40, r=10, t=20, b=100),
        xaxis=dict(title="Lap (0 = starting grid)", dtick=1),
        yaxis=dict(
            title="Position",
            dtick=1,
            autorange="reversed",
            range=[float(positions.Position.max()) + 0.5, 0.5],
        ),
    )
    return fig
