import numpy as np
import pandas as pd

from tep_metrics.core.geography import category_from_one_hot
from tep_metrics.metrics.highway import COUNTYWIDE_LABEL


MODE_SHARE_MAP = {
    1: "DA", 2: "DA", 3: "SR2", 4: "SR2", 5: "SR3+", 6: "SR3+",
    7: "Nonmotorized", 8: "Nonmotorized",
    9: "Transit", 10: "Transit", 11: "Transit", 12: "Transit", 13: "Transit",
    14: "Transit", 15: "Transit", 16: "Transit", 17: "Transit", 18: "Transit",
    19: "Taxi/TNC", 20: "Taxi/TNC", 21: "Taxi/TNC",
}
MODE_ORDER = ("DA", "SR2", "SR3+", "Transit", "Nonmotorized", "Taxi/TNC")


def prepare_person_trips(individual, joint):
    indiv = individual[["orig_taz", "dest_taz", "trip_mode"]].copy()
    indiv["person_trips"] = 1.0
    joint_trips = joint[["orig_taz", "dest_taz", "trip_mode", "num_participants"]].copy()
    joint_trips["person_trips"] = pd.to_numeric(joint_trips["num_participants"], errors="raise")
    return pd.concat([indiv, joint_trips[indiv.columns]], ignore_index=True)


def calculate_mode_share(individual, joint, taz_filters):
    trips = prepare_person_trips(individual, joint)
    trips["Mode"] = trips["trip_mode"].map(MODE_SHARE_MAP)
    unmapped = sorted(trips.loc[trips["Mode"].isna(), "trip_mode"].dropna().unique())
    if unmapped:
        raise ValueError(f"Unmapped trip_mode codes: {unmapped}")
    lookup = category_from_one_hot(taz_filters, "RTPC").rename(columns={"TAZ": "orig_taz"})
    trips = trips.merge(lookup, on="orig_taz", how="left", validate="many_to_one")
    trips = trips.loc[trips["RTPC"].notna()]
    counts = trips.pivot_table(index="RTPC", columns="Mode", values="person_trips",
                               aggfunc="sum", fill_value=0).reindex(columns=MODE_ORDER, fill_value=0)
    shares = counts.div(counts.sum(axis=1).replace(0, np.nan), axis=0) * 100
    county = counts.sum(axis=0)
    shares.loc[COUNTYWIDE_LABEL] = county / county.sum() * 100
    result = shares.reset_index()
    result.columns.name = None
    result["Total_Share"] = result[list(MODE_ORDER)].sum(axis=1)
    return result
