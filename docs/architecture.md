# Architecture

Three layers, with dependencies pointing one way only:

```
FastF1 API ──> data/ ──> analysis/ ──> charts/ ──> app/ (Streamlit pages)
```

| Layer | Location | Responsibility | May import |
|---|---|---|---|
| Data | `src/f1companion/data/` | Load FastF1 sessions, manage the cache, normalise into DataFrames | FastF1, pandas |
| Analysis | `src/f1companion/analysis/` | Pure functions: DataFrame in, DataFrame out | pandas, numpy |
| Charts | `src/f1companion/charts/` | Build Plotly figures from analysis output | plotly, pandas |
| UI | `app/` | Arrange charts, handle user input and URL state | everything above, Streamlit |

## Rules

- The UI never calls FastF1 directly; it goes through the data layer.
- Analysis functions have no network access and no Streamlit imports, so they are tested with small fixture data.
- Chart builders return figures; pages only lay them out.
- Cached FastF1 data lives in `data/`, which is gitignored.
