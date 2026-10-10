"""Figure structure, ordering, colours, and empty inputs."""

import pytest
from factories import race_data, telemetry
from pandas.testing import assert_frame_equal

from f1companion.analysis import compare_telemetry, driver_colors, position_by_lap, stints
from f1companion.charts import position_chart, strategy_chart, telemetry_chart
from f1companion.charts.theme import COMPOUND_COLORS, DEFAULT_TEAM_COLOR


def test_positions():
    race = race_data()
    positions = position_by_lap(race.laps, race.results)
    before = positions.copy(deep=True)
    fig = position_chart(positions, driver_colors(race.results))
    assert [trace.name for trace in fig.data] == ["AAA", "BBB", "CCC", "DDD"]
    assert fig.data[0].line.color == "#112233"
    assert fig.data[1].line.dash == "dash"
    assert fig.data[2].line.dash == "solid"
    assert fig.layout.yaxis.autorange == "reversed"
    assert fig.layout.yaxis.range == (4.5, 0.5)
    assert fig.layout.yaxis.dtick == 1
    assert_frame_equal(positions, before)


def test_position_fallback():
    race = race_data()
    fig = position_chart(position_by_lap(race.laps, race.results), {})
    assert fig.data[0].line.color == DEFAULT_TEAM_COLOR


def test_strategy():
    race = race_data()
    data = stints(race.laps)
    before = data.copy(deep=True)
    order = race.results.Driver.tolist()
    fig = strategy_chart(data, order)
    assert [trace.name for trace in fig.data] == ["SOFT", "HARD"]
    assert list(fig.data[0].base) == [0, 0, 0, 0]
    assert list(fig.data[0].x) == [2, 2, 2, 2]
    assert list(fig.data[1].base) == [2, 2, 2, 2]
    assert list(fig.data[1].x) == [4, 4, 4, 2]
    assert fig.data[0].marker.color == COMPOUND_COLORS["SOFT"]
    assert fig.data[1].marker.line.width == 1
    assert list(fig.layout.yaxis.categoryarray) == order
    assert fig.layout.yaxis.autorange == "reversed"
    assert_frame_equal(data, before)


@pytest.mark.parametrize("same_color", [False, True])
def test_telemetry(same_color):
    comparison = compare_telemetry(telemetry(), telemetry())
    before = comparison.copy(deep=True)
    fig = telemetry_chart(
        comparison, "AAA", "BBB", "#112233", "#112233" if same_color else "#445566"
    )
    assert len(fig.data) == 6
    assert [t.yaxis for t in fig.data] == ["y", "y", "y2", "y2", "y3", "y3"]
    assert [t.showlegend for t in fig.data] == [True, True, False, False, False, False]
    assert fig.data[1].line.dash == ("dash" if same_color else "solid")
    assert fig.data[4].line.shape == "hv"
    assert set(fig.data[4].y) == {0, 1}
    assert fig.layout.hovermode == "x unified"
    assert fig.layout.xaxis3.title.text == "Distance along the lap (m)"
    assert_frame_equal(comparison, before)


@pytest.mark.parametrize("kind", ["positions", "strategy", "telemetry"])
@pytest.mark.parametrize("empty", [False, True])
def test_layout_and_empty(kind, empty):
    race = race_data()
    if kind == "positions":
        frame = position_by_lap(race.laps, race.results)
        fig = position_chart(frame.iloc[:0] if empty else frame, {})
    elif kind == "strategy":
        frame = stints(race.laps)
        fig = strategy_chart(frame.iloc[:0] if empty else frame, race.results.Driver.tolist())
    else:
        frame = compare_telemetry(telemetry(), telemetry())
        fig = telemetry_chart(
            frame.iloc[:0] if empty else frame, "AAA", "BBB", "#112233", "#445566"
        )
    assert fig.layout.width is None
    assert fig.layout.legend.orientation == "h"
    assert fig.layout.legend.y == -0.2
    assert fig.layout.paper_bgcolor is None
    assert fig.layout.plot_bgcolor is None
    if empty:
        assert len(fig.data) == 0
        assert fig.layout.annotations[0].text == "No data to show"
