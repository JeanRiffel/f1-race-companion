"""Horizontal tyre-stint timelines."""

import pandas as pd
import plotly.graph_objects as go

from .theme import COMPOUND_COLORS, LEGEND, empty_chart


def strategy_chart(stints: pd.DataFrame, driver_order: list[str]) -> go.Figure:
    """Plot one coloured bar per stint with drivers in finishing order."""
    if stints.empty:
        return empty_chart()
    fig = go.Figure()
    for compound, group in stints.groupby("Compound", sort=False):
        fig.add_trace(
            go.Bar(
                orientation="h",
                name=compound,
                base=(group.StartLap - 1).tolist(),
                x=group.LapCount.tolist(),
                y=group.Driver.tolist(),
                text=[str(compound)[0]] * len(group),
                textposition="inside",
                customdata=group[["StartLap", "EndLap"]].to_numpy(),
                marker=dict(
                    color=COMPOUND_COLORS.get(compound, COMPOUND_COLORS["UNKNOWN"]),
                    line=dict(color="#333333", width=1),
                ),
                hovertemplate="%{y}<br>"
                + str(compound)
                + "<br>Laps %{customdata[0]}-%{customdata[1]}<extra></extra>",
            )
        )
    fig.update_layout(
        height=max(420, 26 * len(driver_order) + 160),
        barmode="overlay",
        legend=LEGEND,
        margin=dict(l=40, r=10, t=20, b=90),
        xaxis=dict(title="Lap", dtick=5),
        yaxis=dict(
            title="Driver", categoryorder="array", categoryarray=driver_order, autorange="reversed"
        ),
    )
    return fig
