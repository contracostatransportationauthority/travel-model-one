from pathlib import Path
import pandas as pd


def add_taz_filters(taz_data, filter_filename, zone_column="ZONE", filter_zone_column="TAZ", validate_binary=True):
    filters = pd.read_csv(filter_filename)
    if zone_column not in taz_data.columns:
        raise ValueError(f"{zone_column!r} is missing from taz_data")
    if filter_zone_column not in filters.columns:
        raise ValueError(f"{filter_zone_column!r} is missing from {Path(filter_filename).name}")
    if filters[filter_zone_column].duplicated().any():
        raise ValueError("The TAZ filter file contains duplicate zones")

    filter_columns = [c for c in filters.columns if c != filter_zone_column]
    if not filter_columns:
        raise ValueError("The TAZ filter file has no binary filter columns")

    filters[filter_columns] = filters[filter_columns].apply(pd.to_numeric, errors="coerce").fillna(0)
    if validate_binary:
        invalid = [c for c in filter_columns if not filters[c].isin([0, 1]).all()]
        if invalid:
            raise ValueError(f"Non-binary values found in filter columns: {invalid}")
    filters[filter_columns] = filters[filter_columns].astype("int8")
    filters = filters.rename(columns={filter_zone_column: zone_column})

    existing = [c for c in filter_columns if c in taz_data.columns]
    output = taz_data.drop(columns=existing).merge(filters, on=zone_column, how="left", validate="many_to_one")
    output[filter_columns] = output[filter_columns].fillna(0).astype("int8")
    return output, filter_columns


def apply_filters(data, filters):
    if not filters:
        return data.copy()
    mask = pd.Series(True, index=data.index)
    for column, values in filters.items():
        values = values if isinstance(values, list) else [values]
        mask &= data[column].isin(values)
    return data.loc[mask].copy()
