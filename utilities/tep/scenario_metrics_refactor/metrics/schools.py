import numpy as np
import pandas as pd

from metrics.highway import COUNTYWIDE_LABEL, TOD_PERIODS


def select_school_area_links(roads, schools, buffer_miles=0.5):
    """Return A-B links intersecting school buffers, excluding mainline freeways."""
    if roads.crs is None or schools.crs is None:
        raise ValueError("Road and school layers must have a projected CRS")
    roads = roads.loc[~roads["ROADWAY"].eq("motorway")].copy()
    schools = schools.to_crs(roads.crs)
    try:
        unit_name = roads.crs.axis_info[0].unit_name.lower()
    except (AttributeError, IndexError):
        unit_name = ""
    if "foot" in unit_name:
        distance = buffer_miles * 5280
    elif "metre" in unit_name or "meter" in unit_name:
        distance = buffer_miles * 1609.344
    else:
        raise ValueError(f"Unsupported CRS distance unit: {unit_name or 'unknown'}")
    school_area = schools.geometry.buffer(distance).union_all()
    return roads.loc[roads.geometry.intersects(school_area), ["A", "B"]].drop_duplicates()


def calculate_school_measures(network, school_links, periods=TOD_PERIODS):
    school = network.merge(school_links, on=["A", "B"], how="inner").copy()
    for period in periods:
        school[f"PAX_VMT_{period}"] = school["DISTANCE"] * school[f"VOL_PAX_VEH_{period}"]
        school[f"TRUCK_VMT_{period}"] = school["DISTANCE"] * (
            school[f"VOL_SM_{period}"] + school[f"VOL_HV_{period}"]
        )
    school["PAX_VMT_DAILY"] = school[[f"PAX_VMT_{p}" for p in periods]].sum(axis=1)
    school["TRUCK_VMT_DAILY"] = school[[f"TRUCK_VMT_{p}" for p in periods]].sum(axis=1)
    vmt = school.groupby("RTPC")[["PAX_VMT_DAILY", "TRUCK_VMT_DAILY"]].sum().reset_index()
    county = pd.DataFrame([{"RTPC": COUNTYWIDE_LABEL,
                            "PAX_VMT_DAILY": school["PAX_VMT_DAILY"].sum(),
                            "TRUCK_VMT_DAILY": school["TRUCK_VMT_DAILY"].sum()}])
    vmt = pd.concat([vmt, county], ignore_index=True)

    speed_rows = []
    groups = list(school.groupby("RTPC")) + [(COUNTYWIDE_LABEL, school)]
    for area, group in groups:
        row = {"RTPC": area}
        for period in ("AM", "PM"):
            valid = (group[f"CSPD_{period}"] > 0) & (group["DISTANCE"] > 0) & (
                group[f"VOL_PAX_VEH_{period}"] > 0)
            vmt_period = (group.loc[valid, f"VOL_PAX_VEH_{period}"] * group.loc[valid, "DISTANCE"]).sum()
            vht = (group.loc[valid, f"VOL_PAX_VEH_{period}"] * group.loc[valid, "DISTANCE"] /
                   group.loc[valid, f"CSPD_{period}"]).sum()
            row[f"AVG_SPEED_{period}"] = vmt_period / vht if vht > 0 else np.nan
        speed_rows.append(row)
    return vmt, pd.DataFrame(speed_rows)
