import pandas as pd


def calculate_waiting_time(waiting_taz, taz_data, group_by, zone_column="ZONE"):
    data = waiting_taz.loc[waiting_taz["Access"].notna()].copy()
    zone_lookup = taz_data.set_index(zone_column)["County Name"]
    data["COUNTY"] = data["TAZ"].map(zone_lookup)
    data["Transit Mode"] = data["Mode"].map({"com": "Commuter Rail", "hvy": "Heavy Rail", "exp": "Bus", "lrf": "Light Rail", "loc": "Bus"})
    value_columns = [c for c in data.columns if c.endswith("Init wait hours") or c.endswith("Xfer wait hours")]
    grouped = data.groupby(group_by, dropna=False)[value_columns].sum().reset_index()
    for period in ["Daily", "EA", "AM", "MD", "PM", "EV"]:
        columns = [f"{period} Init wait hours", f"{period} Xfer wait hours"]
        if all(c in grouped.columns for c in columns):
            grouped[f"Total {period} Waiting Time (Hours)"] = grouped[columns].sum(axis=1)
    return grouped
