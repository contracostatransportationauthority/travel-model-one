import pandas as pd


def calculate_accessibility(time_skims, zonal_data, origin_filter, destination_measure, skim_column, threshold, zone_column="ZONE", population_column="TOTPOP"):
    skim = time_skims[["orig", "dest", skim_column]].copy()
    skim[skim_column] = skim[skim_column].replace(-999.0, pd.NA)
    destinations = zonal_data[[zone_column, destination_measure]].rename(columns={zone_column: "dest"})
    origins = zonal_data.loc[zonal_data[origin_filter].eq(1), [zone_column, population_column]].rename(columns={zone_column: "orig", population_column: "origin_population"})
    result = skim.merge(destinations, on="dest", how="left").merge(origins, on="orig", how="inner")
    result["accessible_total"] = result[destination_measure].where(result[skim_column].le(threshold), 0).fillna(0)
    result = result.groupby("orig", as_index=False).agg(accessible_total=("accessible_total", "sum"), origin_population=("origin_population", "first"))
    result["origin_filter"] = origin_filter
    result["destination_measure"] = destination_measure
    result["skim_column"] = skim_column
    result["threshold"] = threshold
    return result


def calculate_population_share(time_skims, zonal_data, origin_filter, destination_filter, origin_measure, skim_column, threshold, zone_column="ZONE"):
    selected_destinations = zonal_data.loc[zonal_data[destination_filter].eq(1), zone_column]
    origins = zonal_data.loc[zonal_data[origin_filter].eq(1), [zone_column, origin_measure]].rename(columns={zone_column: "orig"})
    skim = time_skims.loc[time_skims["dest"].isin(selected_destinations), ["orig", "dest", skim_column]].copy()
    skim[skim_column] = skim[skim_column].replace(-999.0, pd.NA)
    result = skim.merge(origins, on="orig", how="inner")
    result["eligible_origin"] = result[origin_measure].where(result[skim_column].le(threshold), 0).fillna(0)
    result = result.groupby("orig", as_index=False).agg(eligible_origin=("eligible_origin", "max"))
    result["origin_total"] = origins[origin_measure].sum()
    result["origin_filter"] = origin_filter
    result["destination_filter"] = destination_filter
    result["skim_column"] = skim_column
    result["threshold"] = threshold
    return result

def get_high_frequency_transit_supplinks(trnline, trnlink, max_frequency=15, max_mode=10, max_node=6626, max_distance=0.5):
    high_freq_lines = trnline.loc[trnline['frequency'] <= max_frequency, 'name'].unique()

    high_freq_links = trnlink[trnlink['name'].isin(high_freq_lines)]

    high_freq_stop_nodes = pd.unique(pd.concat([
        high_freq_links.loc[high_freq_links['stopA'] == 1, 'A'],
        high_freq_links.loc[high_freq_links['stopB'] == 1, 'B']
    ], ignore_index=True).dropna())

    supplinks = trnlink[
        (trnlink['B'].isin(high_freq_stop_nodes)) &
        (trnlink['mode'] <= max_mode) &
        (trnlink['A'] < max_node) &
        (trnlink['distance'] <= max_distance)
    ].copy()

    return supplinks

def calculate_population_share_transit_access(zonal_data, origin_filter, eligible_zones, zone_column="ZONE", population_column="TOTPOP"):
    # eligible_zones = transit_link_file['A'].dropna().unique()
    eligible_population = zonal_data.loc[zonal_data[zone_column].isin(eligible_zones) & zonal_data[origin_filter].eq(1), population_column].sum()
    total_population = zonal_data.loc[zonal_data[origin_filter].eq(1), population_column].sum()
    population_share = eligible_population / total_population if total_population > 0 else 0
    return pd.DataFrame({'origin_filter': [origin_filter], 'eligible_population': [eligible_population], 'total_population': [total_population], 'population_share': [population_share]})