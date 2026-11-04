import argparse
import pandas as pd
from tep_metrics.core.config import load_config, resolve_path
from tep_metrics.io.loaders import (
    load_prepared_highway_network, load_prepared_highway_geodata,
    load_trip_tables, load_filtered_time_skims, load_active_distances,
)
from tep_metrics.metrics.highway import calculate_network_vmt, calculate_freeway_delay, calculate_freeway_speed
from tep_metrics.metrics.travel_times import build_route_pairs, prepare_trip_mode_counts, calculate_best_travel_times
from tep_metrics.metrics.schools import select_school_area_links, calculate_school_measures
from tep_metrics.metrics.vmt_rates import calculate_vmt_rates
from tep_metrics.metrics.active_transportation import calculate_active_transportation
from tep_metrics.metrics.mode_share import calculate_mode_share
from tep_metrics.core.input_availability import missing_metric_inputs


def get_high_frequency_transit_supplinks(trnline, trnlink, max_frequency=15, max_mode=10, max_node=6626, max_distance=0.5):
    high_freq_lines = trnline.loc[trnline['frequency'] <= max_frequency, 'name'].unique()
    high_freq_links = trnlink[trnlink['name'].isin(high_freq_lines)]
    high_freq_stop_nodes = pd.unique(pd.concat([high_freq_links.loc[high_freq_links['stopA'] == 1, 'A'], high_freq_links.loc[high_freq_links['stopB'] == 1, 'B']], ignore_index=True).dropna())
    return trnlink[(trnlink['B'].isin(high_freq_stop_nodes)) & (trnlink['mode'] <= max_mode) & (trnlink['A'] < max_node) & (trnlink['distance'] <= max_distance)].copy()


def calculate_population_share_transit_access(zonal_data, origin_filter, eligible_zones, zone_column='ZONE', population_column='TOTPOP'):
    eligible_population = zonal_data.loc[zonal_data[zone_column].isin(eligible_zones) & zonal_data[origin_filter].eq(1), population_column].sum()
    total_population = zonal_data.loc[zonal_data[origin_filter].eq(1), population_column].sum()
    population_share = eligible_population / total_population if total_population > 0 else 0
    return pd.DataFrame({'origin_filter': [origin_filter], 'eligible_population': [eligible_population], 'total_population': [total_population], 'population_share': [population_share]})


def metric_enabled(config, name):
    """Return the run switch stored with a named metric definition."""
    return config['metrics'].get(name, {}).get('enabled', False)


def disable_metrics_with_missing_inputs(config):
    """Disable only enabled metrics whose declared direct inputs are missing."""
    missing = missing_metric_inputs(config)
    for name, paths in missing.items():
        config['metrics'][name]['enabled'] = False
        print(f"SKIPPED {name}: {len(paths)} direct input file(s) missing")
        if len(paths) <= 3:
            for path in paths:
                print(f"  MISSING {path}")
    return missing


def write_result(data, filename):
    """Write a CTP result with the same visible logging as other metrics."""
    data.to_csv(filename, index=False)
    print(f"Wrote {filename}")


def run_ctp_metrics(config):
    """Run the metrics sourced from the CTP Jupyter notebook."""
    metrics = config['metrics']
    ctp_metric_names = [
        name for name, metric in metrics.items()
        if metric.get('metric_category') == 'ctp_metric'
    ]
    if not any(metric_enabled(config, name) for name in ctp_metric_names):
        return

    output_dir = resolve_path(config, 'metrics_output_dir')
    output_dir.mkdir(parents=True, exist_ok=True)

    network_metric_names = ('network_vmt', 'freeway_delay', 'freeway_speed', 'school_area')
    network = None
    if any(metric_enabled(config, name) for name in network_metric_names):
        network = load_prepared_highway_network(
            resolve_path(config, 'rtpc_highway_network'),
            config['run'].get('rtpc_highway_network_layer'),
        )

    if metric_enabled(config, 'network_vmt'):
        result, _ = calculate_network_vmt(network)
        write_result(result, output_dir / metrics['network_vmt']['output_file'])
    if metric_enabled(config, 'freeway_delay'):
        result = calculate_freeway_delay(network)
        write_result(result, output_dir / metrics['freeway_delay']['output_file'])
    if metric_enabled(config, 'freeway_speed'):
        result = calculate_freeway_speed(network)
        write_result(result, output_dir / metrics['freeway_speed']['output_file'])

    travel_config = metrics.get('best_travel_time', {})
    if metric_enabled(config, 'best_travel_time'):
        taz_filters = pd.read_csv(resolve_path(config, 'taz_filter'))
        route_pairs = build_route_pairs(taz_filters, travel_config['routes'])
        individual, joint = load_trip_tables(
            resolve_path(config, 'individual_trips'),
            resolve_path(config, 'joint_trips'),
            usecols=['orig_taz', 'dest_taz', 'depart_hour', 'trip_mode'],
        )
        for period, hours in travel_config['periods'].items():
            counts = prepare_trip_mode_counts(individual, joint, route_pairs, hours[0], hours[1])
            skim_path = resolve_path(config, 'time_skims_by_period', period)
            skims = load_filtered_time_skims(skim_path, route_pairs)
            result = calculate_best_travel_times(counts, skims, route_pairs)
            result.insert(1, 'TOD', period)
            write_result(result, output_dir / travel_config['output_file'].format(period=period))

    school_config = metrics.get('school_area', {})
    if metric_enabled(config, 'school_area'):
        roads = load_prepared_highway_geodata(
            resolve_path(config, 'rtpc_highway_network'),
            config['run'].get('rtpc_highway_network_layer'))
        schools = load_prepared_highway_geodata(resolve_path(config, 'school_locations'))
        school_links = select_school_area_links(roads, schools, school_config.get('buffer_miles', 0.5))
        vmt, speed = calculate_school_measures(network, school_links)
        write_result(vmt, output_dir / school_config['vmt_output_file'])
        write_result(speed, output_dir / school_config['speed_output_file'])

    rates_config = metrics.get('vmt_rates', {})
    if metric_enabled(config, 'vmt_rates'):
        vmt_data = pd.read_csv(resolve_path(config, 'vmt_home_work'))
        persons = pd.read_csv(resolve_path(config, 'persons_home_work'))
        taz_filters = pd.read_csv(resolve_path(config, 'taz_filter'))
        rates, detail = calculate_vmt_rates(vmt_data, persons, taz_filters)
        write_result(rates, output_dir / rates_config['output_file'])
        write_result(detail, output_dir / rates_config['detail_output_file'])

    active_config = metrics.get('active_transportation', {})
    if metric_enabled(config, 'active_transportation'):
        try:
            individual = pd.read_csv(resolve_path(config, 'individual_trips'),
                                     usecols=['orig_taz', 'dest_taz', 'trip_mode'])
            joint = pd.read_csv(resolve_path(config, 'joint_trips'),
                                usecols=['orig_taz', 'dest_taz', 'trip_mode', 'num_participants'])
            taz_filters = pd.read_csv(resolve_path(config, 'taz_filter'))
            distances = load_active_distances(resolve_path(config, 'nonmotorized_distance_matrix'))
            detail, combined = calculate_active_transportation(
                individual, joint, taz_filters, distances, active_config.get('distance_limit', 3.0))
            write_result(detail, output_dir / active_config['output_file'])
            write_result(combined, output_dir / active_config['combined_output_file'])
        except FileNotFoundError as exc:
            if config.get('missing_input_policy') != 'skip':
                raise
            print(f"SKIPPED Active Transportation: missing input {exc.filename}")

    mode_config = metrics.get('person_trip_mode_share', {})
    if metric_enabled(config, 'person_trip_mode_share'):
        individual = pd.read_csv(resolve_path(config, 'individual_trips'),
                                 usecols=['orig_taz', 'dest_taz', 'trip_mode'])
        joint = pd.read_csv(resolve_path(config, 'joint_trips'),
                            usecols=['orig_taz', 'dest_taz', 'trip_mode', 'num_participants'])
        taz_filters = pd.read_csv(resolve_path(config, 'taz_filter'))
        result = calculate_mode_share(individual, joint, taz_filters)
        write_result(result, output_dir / mode_config['output_file'])


def run_accessibility_and_transit_metrics(config):
    """Run the accessibility and transit metrics from the original package."""
    # These dependencies stay lazy so a new-metrics-only run does not require
    # DBF or transit-assignment packages and inputs.
    from tep_metrics.core.constants import COUNTY_CODES, EXCLUDED_TRANSIT_MODES
    from tep_metrics.core.filters import add_taz_filters, apply_filters
    from tep_metrics.io.loaders import (
        load_taz_data, load_time_skims, load_transit_mode_line,
        load_transit_waiting, load_highway_network, load_transit_links,
        load_transit_link, load_transit_line, load_transit_stop_filter,
    )
    from tep_metrics.io.outputs import write_metric
    from tep_metrics.io.validation import require_columns
    from tep_metrics.metrics.accessibility import calculate_accessibility, calculate_population_share
    from tep_metrics.metrics.transit_delay import calculate_link_ivd
    from tep_metrics.metrics.transit_waiting import calculate_waiting_time

    metrics = config['metrics']
    accessibility_metrics = [
        metric for metric in metrics.values()
        if metric.get('calculation_type') in {
            'accessibility', 'population_share',
            'population_share_transit_access',
        }
    ]
    selected_accessibility = [
        metric for metric in accessibility_metrics
        if metric_enabled(config, metric['name'])
    ]
    selected_transit = any(metric_enabled(config, name) for name in (
        'transit_delay', 'transit_boarding', 'transit_waiting'
    ))
    if not selected_accessibility and not selected_transit:
        return

    taz = None
    user_filter_columns = []
    county_filter_columns = list(COUNTY_CODES.values())
    zone_column = config['taz']['zone_column']
    if selected_accessibility or metric_enabled(config, 'transit_waiting'):
        taz = load_taz_data(config)
        require_columns(taz, [zone_column, config['taz']['county_code_column'], config['taz']['population_column'], config['taz']['employment_column']], 'TAZ data')
        taz[config['taz']['county_name_column']] = taz[config['taz']['county_code_column']].map(COUNTY_CODES)
        taz = pd.concat([taz, pd.get_dummies(taz[config['taz']['county_name_column']], dtype='int8')], axis=1)
        filter_file = resolve_path(config, 'taz_filter')
        taz, user_filter_columns = add_taz_filters(taz, filter_file, zone_column, config['taz']['filter_zone_column'], config['taz']['validate_binary_filters'])
    skims = load_time_skims(config) if selected_accessibility else None
    transit_access_cache = {}

    for metric in selected_accessibility:
        selector = metric['origin_filters']
        origin_filters = user_filter_columns if selector == 'ALL_BINARY_FILTERS' else county_filter_columns if selector == 'COUNTY_FILTERS' else selector
        results = []
        results_grouped = []

        if metric['calculation_type'] == 'population_share_transit_access':
            access_key = (metric.get('max_frequency', 15), metric.get('max_mode', 10), metric.get('max_node', 6626), metric.get('max_distance', 0.5))
            if access_key not in transit_access_cache:
                trnline = load_transit_line(config)
                trnlink = load_transit_link(config)
                require_columns(trnline, ['name', 'frequency'], 'Transit line data')
                require_columns(trnlink, ['name', 'A', 'B', 'stopA', 'stopB', 'mode', 'distance'], 'Transit link data')
                supplinks = get_high_frequency_transit_supplinks(trnline, trnlink, *access_key)
                transit_access_cache[access_key] = supplinks['A'].dropna().unique()
            eligible_zones = transit_access_cache[access_key]

        for origin_filter in origin_filters:
            if metric['calculation_type'] == 'accessibility':
                result = calculate_accessibility(skims, taz, origin_filter, metric['destination_measure'], metric['skim_column'], metric['threshold'], zone_column, metric['origin_weight'])
                grouped_result = result.copy()
                grouped_result['Population Weighted Employment'] = grouped_result['accessible_total'] * grouped_result['origin_population']
                grouped_result = grouped_result.groupby('origin_filter').agg({'Population Weighted Employment': 'sum', 'origin_population': 'sum', 'destination_measure': 'first', 'skim_column': 'first', 'threshold': 'first'}).reset_index()
                grouped_result = grouped_result.rename(columns={'origin_population': 'Total Population at Origin County'})
                grouped_result['Job Accesibility'] = grouped_result['Population Weighted Employment'] / grouped_result['Total Population at Origin County']
            elif metric['calculation_type'] == 'population_share':
                result = calculate_population_share(skims, taz, origin_filter, metric['destination_filter'], metric['origin_measure'], metric['skim_column'], metric['threshold'], zone_column)
                grouped_result = result.copy().groupby('origin_filter').agg({'eligible_origin': 'sum', 'origin_total': 'mean', 'destination_filter': 'first', 'skim_column': 'first', 'threshold': 'first'}).reset_index()
                grouped_result = grouped_result.rename(columns={'eligible_origin': 'Total At All Eligible Origin', 'origin_total': 'Total Population at Origin County'})
                grouped_result['Percent of Total'] = grouped_result['Total At All Eligible Origin'] / grouped_result['Total Population at Origin County']
            elif metric['calculation_type'] == 'population_share_transit_access':
                result = calculate_population_share_transit_access(taz, origin_filter, eligible_zones, metric.get('zone_column', zone_column), metric.get('population_column', config['taz']['population_column']))
                grouped_result = result.copy()
            else:
                raise ValueError(
                    f"Unknown metric type: {metric['calculation_type']}"
                )
            results.append(result)
            results_grouped.append(grouped_result)

        write_metric(pd.concat(results, ignore_index=True), config, metric['output_file'])
        if metric.get('grouped_output_file'):
            write_metric(pd.concat(results_grouped, ignore_index=True), config, metric['grouped_output_file'])

    delay_config = metrics['transit_delay']
    if metric_enabled(config, 'transit_delay'):
        transit_links = load_transit_links(config)
        highway = load_highway_network(config)
        mode_line = load_transit_mode_line(config)
        mode_line.loc[mode_line['Technology'].eq('Cable Car'), 'Technology'] = 'Bus'
        delay = calculate_link_ivd(EXCLUDED_TRANSIT_MODES, transit_links, highway, mode_line)
        delay = apply_filters(delay, delay_config.get('filters', {}))
        delay = delay.groupby(delay_config['group_by'], as_index=False).agg(**{'Total In-Vehicle Hours of Delay': ('Total In-Vehicle Hours of Delay', 'sum'), 'Boardings': ('Boardings', 'sum')})
        write_metric(delay, config, delay_config['output_file'])
    boarding_config = metrics['transit_boarding']
    if metric_enabled(config, 'transit_boarding'):
        transit_links = load_transit_links(config)
        highway = load_highway_network(config)
        mode_line = load_transit_mode_line(config)
        mode_line.loc[mode_line['Technology'].eq('Cable Car'), 'Technology'] = 'Bus'
        delay = calculate_link_ivd(EXCLUDED_TRANSIT_MODES, transit_links, highway, mode_line)
        stop_filter = load_transit_stop_filter(config)

        boardings = delay[boarding_config['group_by'] + ['name','Total Boardings']].drop_duplicates()
        boardings_grouped=boardings.groupby(boarding_config['group_by'], as_index=False).agg({'Total Boardings':'sum'}).reset_index()
        boardings_grouped_pivot=pd.pivot(index=boarding_config['pivot_index'],columns='timeperiod', values=['Total Boardings'], data=boardings_grouped)
        boardings_grouped_pivot['Daily'] = boardings_grouped_pivot.sum(axis=1)

        boardings_by_stop = boardings[boardings['A'].isin(stop_filter['stops'].unique())]
        boardings_by_stopgrouped=boardings_by_stop.groupby(boarding_config['group_by'], as_index=False).agg({'Total Boardings':'sum'}).reset_index()
        boardings_by_stopgrouped_pivot=pd.pivot(index=boarding_config['pivot_index'],columns='timeperiod', values=['Total Boardings'], data=boardings_by_stopgrouped)
        boardings_by_stopgrouped_pivot['Daily'] = boardings_by_stopgrouped_pivot.sum(axis=1)

        write_metric(boardings_grouped_pivot, config, boarding_config['boarding_output_file'])
        write_metric(boardings_by_stopgrouped_pivot, config, boarding_config['boarding_by_stops_output_file'])

    waiting_config = metrics['transit_waiting']
    if metric_enabled(config, 'transit_waiting'):
        waiting = calculate_waiting_time(load_transit_waiting(config), taz, waiting_config['group_by'], zone_column)
        waiting = apply_filters(waiting, waiting_config.get('filters', {}))
        write_metric(waiting, config, waiting_config['output_file'])


def run(config):
    """Run the new and original metrics from one configuration and entry point."""
    run_ctp_metrics(config)
    run_accessibility_and_transit_metrics(config)


def main():
    parser = argparse.ArgumentParser(description='Create configurable scenario metrics')
    parser.add_argument('--config', default='config/scenario_metrics.json')
    parser.add_argument(
        '--available-inputs-only', action='store_true',
        help='disable and report enabled metrics whose direct input files are missing',
    )
    args = parser.parse_args()
    config = load_config(args.config)
    if args.available_inputs_only or config.get('missing_input_policy') == 'skip':
        disable_metrics_with_missing_inputs(config)
    run(config)


if __name__ == '__main__':
    main()
