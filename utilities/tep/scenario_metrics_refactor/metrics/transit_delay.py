import numpy as np
import pandas as pd
from metrics.common import county_from_node


def calculate_link_ivd(excluded_modes, transit_links, highway_links, transit_mode_line):
    df = transit_links.loc[~transit_links["mode"].isin(excluded_modes)].copy()
    df = df.groupby(["A", "B", "name", "mode"], as_index=False).agg(time=("time", "first"), distance=("distance", "first"), AB_VOL=("AB_VOL", "sum"), Boardings=("Boardings", "sum"))
    df[["operator", "route", "timeperiod", "direction"]] = df["name"].str.rsplit("_", n=3, expand=True)
    df[["operator", "route", "direction"]] = df[["operator", "route", "direction"]].apply(pd.to_numeric, errors="coerce")
    df = df.merge(highway_links, on=["A", "B", "timeperiod"], how="left").merge(transit_mode_line, left_on=["operator", "mode"], right_on=["Operator", "Mode"], how="left")
    missing_county = df["COUNTY"].isna() | df["COUNTY"].isin([0, "0"])
    df.loc[missing_county, "COUNTY"] = df.loc[missing_county, "A"].map(county_from_node).fillna(df.loc[missing_county, "B"].map(county_from_node))
    df["delay_factor"] = np.select([df["FT"].isin([1, 2, 3, 8]), df["AT"].isin([0, 1]), df["AT"].isin([2, 3]), df["AT"].eq(4), df["AT"].eq(5)], [0, 2.00, 1.74, 1.14, 0.08], default=1.0)
    standard = df["FFT"] + df["delay_factor"] * df["DISTANCE"] * 0.5
    shoulder = np.minimum(df["FFT"], df["DISTANCE"] / (35.0 / 60.0))
    other = df["FFT"] + df["delay_factor"] * df["DISTANCE"]
    df["FFT_BUS_TIME"] = np.select([df["BRT"].lt(3), df["BRT"].eq(3)], [standard, shoulder], default=other)
    df["Total Delay (Hours)"] = (df["time"] - df["FFT_BUS_TIME"]) / 60
    df["Total In-Vehicle Hours of Delay"] = df["AB_VOL"] * df["Total Delay (Hours)"]
    return df
