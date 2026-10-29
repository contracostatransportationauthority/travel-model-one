import pandas as pd


def category_from_one_hot(data, prefix, taz_column="TAZ", output_column="RTPC"):
    """Convert prefixed one-hot columns into a TAZ-to-category lookup.

    Rows with no selected category remain unmapped. Rows with more than one
    selected category are invalid because the categories are mutually exclusive.
    """
    columns = [column for column in data.columns if column.startswith(f"{prefix}_")]
    if not columns:
        raise ValueError(f"No {prefix}_* columns found in TAZ filters")
    flags = data[columns].apply(pd.to_numeric, errors="raise")
    if not flags.isin([0, 1]).all().all():
        raise ValueError(f"{prefix}_* columns must contain only 0 or 1")
    selected = flags.sum(axis=1)
    if selected.gt(1).any():
        bad = data.loc[selected.gt(1), taz_column].head(10).tolist()
        raise ValueError(f"TAZs have multiple {prefix} assignments: {bad}")
    labels = flags.idxmax(axis=1).str.removeprefix(f"{prefix}_")
    labels = labels.where(selected.eq(1))
    return pd.DataFrame({taz_column: data[taz_column], output_column: labels})
