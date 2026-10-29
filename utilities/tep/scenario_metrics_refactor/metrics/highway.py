"""CTP highway performance measures.

The functions in this module are intentionally independent from file formats and
the travel-model repository.  Each accepts a prepared link-level DataFrame.
"""

import numpy as np
import pandas as pd


TOD_PERIODS = ("EA", "AM", "MD", "PM", "EV")
COUNTYWIDE_LABEL = "Contra Costa County"


def _summary_rows(data, value_columns, area_column="RTPC"):
    by_area = data.groupby(area_column, dropna=True)[value_columns].sum().reset_index()
    county = pd.DataFrame(
        [{area_column: COUNTYWIDE_LABEL, **data[value_columns].sum().to_dict()}]
    )
    return pd.concat([by_area, county], ignore_index=True)


def calculate_network_vmt(network, periods=TOD_PERIODS):
    """Return passenger/truck VMT by RTPC and countywide."""
    links = network.copy()
    for period in periods:
        links[f"PAX_VMT_{period}"] = (
            links["DISTANCE"] * links[f"VOL_PAX_VEH_{period}"]
        )
        links[f"TRUCK_VMT_{period}"] = links["DISTANCE"] * (
            links[f"VOL_SM_{period}"] + links[f"VOL_HV_{period}"]
        )

    pax_columns = [f"PAX_VMT_{period}" for period in periods]
    truck_columns = [f"TRUCK_VMT_{period}" for period in periods]
    links["PAX_VMT_DAILY"] = links[pax_columns].sum(axis=1)
    links["TRUCK_VMT_DAILY"] = links[truck_columns].sum(axis=1)

    value_columns = ["PAX_VMT_DAILY", "TRUCK_VMT_DAILY"]
    result = _summary_rows(links, value_columns)

    freeway = links.loc[links["ROADWAY"].isin(["motorway", "motorway_link"])]
    freeway_result = _summary_rows(freeway, value_columns).rename(
        columns={column: f"{column}_FREEWAY" for column in value_columns}
    )
    return result.merge(freeway_result, on="RTPC", how="left").fillna(0), links


def calculate_freeway_delay(network, periods=TOD_PERIODS):
    """Return nonnegative passenger vehicle-hours of delay by freeway name."""
    freeway = network.loc[
        network["ROADWAY"].isin(["motorway", "motorway_link"])
    ].copy()

    delay_columns = []
    for period in periods:
        column = f"PAX_DELAY_{period}_HR"
        speed = freeway[f"CSPD_{period}"]
        valid = speed.gt(0) & freeway["FFS"].gt(0)
        freeway[column] = np.where(
            valid,
            freeway[f"VOL_PAX_VEH_{period}"]
            * freeway["DISTANCE"]
            * (1 / speed - 1 / freeway["FFS"]),
            np.nan,
        )
        freeway[column] = freeway[column].clip(lower=0)
        delay_columns.append(column)

    freeway["PAX_DELAY_DAILY_HR"] = freeway[delay_columns].sum(axis=1, min_count=1)
    result = (
        freeway.groupby("NAME", dropna=False)[delay_columns + ["PAX_DELAY_DAILY_HR"]]
        .sum(min_count=1)
        .reset_index()
    )
    return result


def calculate_freeway_speed(network):
    """Return AM/PM congested-to-free-flow ratios for freeway mainline links."""
    result = network.loc[network["ROADWAY"].eq("motorway"), [
        "A", "B", "NAME", "RTPC", "FFS", "CSPD_AM", "CSPD_PM"
    ]].copy()
    valid_ffs = result["FFS"].gt(0)
    result["SPEED_RATIO_AM"] = np.where(valid_ffs, result["CSPD_AM"] / result["FFS"], np.nan)
    result["SPEED_RATIO_PM"] = np.where(valid_ffs, result["CSPD_PM"] / result["FFS"], np.nan)
    return result
