"""Transit boarding summaries for all stops and a configured stop subset."""

import pandas as pd


def _pivot_boardings(data, group_by, pivot_index):
    """Aggregate link boardings and return one flat column per time period."""
    grouped = (
        data.groupby(group_by, dropna=False, as_index=False)["Boardings"]
        .sum()
    )
    period_column = next(column for column in group_by if column not in pivot_index)
    result = grouped.pivot(
        index=pivot_index, columns=period_column, values="Boardings"
    ).fillna(0).reset_index()
    result.columns.name = None
    period_columns = [column for column in result.columns if column not in pivot_index]
    result["Daily"] = result[period_columns].sum(axis=1)
    return result


def calculate_boarding_summaries(data, group_by, pivot_index, selected_stops):
    """Return boarding summaries for all links and links at selected A nodes."""
    required = set(group_by) | set(pivot_index) | {"A", "Boardings"}
    missing = sorted(required.difference(data.columns))
    if missing:
        raise ValueError(f"Transit boarding data is missing columns: {missing}")

    all_boardings = _pivot_boardings(data, group_by, pivot_index)
    selected = data.loc[data["A"].isin(pd.Series(selected_stops).dropna().unique())]
    selected_boardings = _pivot_boardings(selected, group_by, pivot_index)
    return all_boardings, selected_boardings
