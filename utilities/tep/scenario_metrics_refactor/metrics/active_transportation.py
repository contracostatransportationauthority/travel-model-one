import numpy as np
import pandas as pd

from core.geography import category_from_one_hot
from metrics.highway import COUNTYWIDE_LABEL
from metrics.mode_share import prepare_person_trips


ACTIVE_MODES = {7: "Walk", 8: "Bike"}


def calculate_active_transportation(individual, joint, taz_filters, distances, distance_limit=3.0):
    trips = prepare_person_trips(individual, joint)
    lookup = category_from_one_hot(taz_filters, "RTPC").rename(columns={"TAZ": "orig_taz"})
    trips = trips.merge(lookup, on="orig_taz", how="left", validate="many_to_one")
    trips = trips.merge(distances, on=["orig_taz", "dest_taz"], how="left", validate="many_to_one")
    trips["mode_distance_miles"] = np.select(
        [trips["trip_mode"].eq(7), trips["trip_mode"].eq(8)],
        [trips["walk_miles"], trips["bike_miles"]], default=np.nan)

    def summarize(all_trips, area):
        total_short = all_trips.loc[all_trips["distance_miles"].lt(distance_limit), "person_trips"].sum()
        rows = []
        for code, name in ACTIVE_MODES.items():
            mode = all_trips.loc[all_trips["trip_mode"].eq(code)]
            short = mode.loc[mode["distance_miles"].lt(distance_limit), "person_trips"].sum()
            valid = mode.loc[mode["mode_distance_miles"].notna()]
            weight = valid["person_trips"].sum()
            average = ((valid["mode_distance_miles"] * valid["person_trips"]).sum() / weight
                       if weight > 0 else np.nan)
            rows.append({"RTPC": area, "Mode": name,
                         "All_Person_Trips_Under_3_Miles": total_short,
                         "Mode_Person_Trips_Under_3_Miles": short,
                         "Mode_Share_Under_3_Miles_Pct": 100 * short / total_short if total_short else np.nan,
                         "Number_of_Person_Trips": mode["person_trips"].sum(),
                         "Average_Distance_Miles": average,
                         "Trips_With_Valid_Distance": weight})
        return rows

    rows = []
    mapped = trips.loc[trips["RTPC"].notna()]
    for area, group in mapped.groupby("RTPC"):
        rows.extend(summarize(group, area))
    rows.extend(summarize(mapped, COUNTYWIDE_LABEL))
    detail = pd.DataFrame(rows)
    combined = detail.groupby("RTPC", as_index=False).agg(
        All_Person_Trips_Under_3_Miles=("All_Person_Trips_Under_3_Miles", "first"),
        Walk_Bike_Trips_Under_3_Miles=("Mode_Person_Trips_Under_3_Miles", "sum"),
        Walk_Bike_Total_Person_Trips=("Number_of_Person_Trips", "sum"))
    combined["Walk_Bike_Share_Under_3_Miles_Pct"] = 100 * combined[
        "Walk_Bike_Trips_Under_3_Miles"] / combined["All_Person_Trips_Under_3_Miles"].replace(0, np.nan)
    return detail, combined
