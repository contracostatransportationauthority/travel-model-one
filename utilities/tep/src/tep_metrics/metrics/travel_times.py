import numpy as np
import pandas as pd


MODE_MAP = {
    1: "da", 2: "daToll", 3: "s2", 4: "s2Toll", 5: "s3", 6: "s3Toll",
    9: "wTrnW", 10: "wTrnW", 11: "wTrnW", 12: "wTrnW", 13: "wTrnW",
    14: "dTrnW", 15: "dTrnW", 16: "dTrnW", 17: "dTrnW", 18: "dTrnW",
}
MODE_CATEGORIES = {
    "drive": ("da", "daToll", "s2", "s2Toll", "s3", "s3Toll"),
    "trn": ("wTrnW", "dTrnW"),
}


def build_route_pairs(taz_filters, route_definitions, taz_column="TAZ"):
    """Expand configured place flags into directed TAZ-pair-to-route records.

    This is the package equivalent of the notebook's ``tag_od_pairs`` helper.
    Instead of constructing an ``O-D`` string on every large input table, it
    builds the relatively small set of valid directed TAZ pairs once. Inner
    joins against that set drop unmapped TAZs and retain only configured routes.
    """
    parts = []
    for route in route_definitions:
        origins = taz_filters.loc[taz_filters[route["origin_flag"]].eq(1), taz_column]
        destinations = taz_filters.loc[taz_filters[route["destination_flag"]].eq(1), taz_column]
        if origins.empty or destinations.empty:
            continue
        pairs = pd.MultiIndex.from_product(
            [origins.astype(int), destinations.astype(int)], names=["orig", "dest"]
        ).to_frame(index=False)
        pairs["route"] = route["name"]
        parts.append(pairs)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(
        columns=["orig", "dest", "route"]
    )


def prepare_trip_mode_counts(individual, joint, route_pairs, start_hour, end_hour):
    """Count observed trip records by directed OD and skim mode."""
    frames = []
    for data in (individual, joint):
        selected = data.loc[
            data["depart_hour"].between(start_hour, end_hour, inclusive="left"),
            ["orig_taz", "dest_taz", "trip_mode"],
        ].rename(columns={"orig_taz": "orig", "dest_taz": "dest"})
        frames.append(selected)
    trips = pd.concat(frames, ignore_index=True)
    trips = trips.loc[trips["trip_mode"].isin(MODE_MAP)].copy()
    trips["mode"] = trips["trip_mode"].map(MODE_MAP)
    trips = trips.merge(route_pairs, on=["orig", "dest"], how="inner")
    return trips.groupby(["orig", "dest", "route", "mode"], as_index=False).size(
        ).rename(columns={"size": "trip_count"})


def calculate_best_travel_times(trip_counts, skims, route_pairs):
    """Calculate minimum skim time among modes with at least one observed trip."""
    tagged_skims = skims.merge(route_pairs, on=["orig", "dest"], how="inner")
    long_skims = tagged_skims.melt(
        id_vars=["orig", "dest", "route"], var_name="mode", value_name="travel_time"
    )
    long_skims["travel_time"] = long_skims["travel_time"].replace(-999, np.nan)
    observed = trip_counts.merge(
        long_skims, on=["orig", "dest", "route", "mode"], how="left"
    )

    rows = []
    for route, group in observed.groupby("route"):
        row = {"route": route, "trips_total": group["trip_count"].sum(),
               "minTT": group["travel_time"].min()}
        for category, modes in MODE_CATEGORIES.items():
            selected = group.loc[group["mode"].isin(modes)]
            row[f"{category}_trips_total"] = selected["trip_count"].sum()
            row[f"min_{category}TT"] = selected["travel_time"].min()
        rows.append(row)
    return pd.DataFrame(rows)
