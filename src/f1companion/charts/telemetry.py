"""Distance-aligned speed, throttle, and brake comparison."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .theme import LEGEND, empty_chart


def telemetry_chart(
    comparison: pd.DataFrame, driver_a: str, driver_b: str, color_a: str, color_b: str
) -> go.Figure:
    """Plot three channels, distinguishing teammates with a dashed second driver."""
    if comparison.empty:
        return empty_chart(660)
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06)
    for row, (channel, title) in enumerate(
        [("Speed", "Speed (km/h)"), ("Throttle", "Throttle (%)"), ("Brake", "Brake (on/off)")], 1
    ):
        for suffix, driver, color in [("A", driver_a, color_a), ("B", driver_b, color_b)]:
            values = comparison[channel + suffix]
            if channel == "Brake":
                values = values.astype(int)
            fig.add_trace(
                go.Scatter(
                    x=comparison.Distance.tolist(),
                    y=values.tolist(),
                    mode="lines",
                    name=driver,
                    legendgroup=driver,
                    showlegend=row == 1,
                    line=dict(
                        color=color,
                        dash="dash" if suffix == "B" and color_a == color_b else "solid",
                        shape="hv" if channel == "Brake" else "linear",
                    ),
                    hovertemplate=driver + ": %{y}<extra></extra>",
                ),
                row=row,
                col=1,
            )
        fig.update_yaxes(title_text=title, row=row, col=1)
    fig.update_yaxes(tickvals=[0, 1], ticktext=["Off", "On"], range=[-0.1, 1.1], row=3, col=1)
    fig.update_xaxes(title_text="Distance along the lap (m)", row=3, col=1)
    fig.update_layout(
        height=660, hovermode="x unified", legend=LEGEND, margin=dict(l=50, r=10, t=20, b=80)
    )
    return fig
