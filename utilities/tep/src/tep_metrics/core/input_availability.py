"""Input availability checks shared by the metric and preprocessing runners."""

from pathlib import Path

from tep_metrics.core.config import resolve_path


def _transit_assignment_files(config, converted=False):
    directory = resolve_path(
        config, "transit_assignment_dir", iteration=config["run"]["iteration"]
    )
    suffix = "_converted.csv" if converted else ".csv"
    return [
        directory / f"trnlink{period.lower()}_{mode}{suffix}"
        for period in config["run"]["time_periods"]
        for mode in config["transit_modes"]
    ]


def _highway_assignment_files(config):
    return [
        resolve_path(
            config,
            "highway_assignment_file",
            iteration=config["run"]["iteration"],
            period=period,
        )
        for period in config["run"]["time_periods"]
    ]


def metric_input_paths(config):
    """Return direct input paths grouped by configured metric name."""
    common_trips = [
        resolve_path(config, "individual_trips"),
        resolve_path(config, "joint_trips"),
        resolve_path(config, "taz_filter"),
    ]
    network = [resolve_path(config, "rtpc_highway_network")]
    accessibility = [
        resolve_path(config, "scenario_taz_data"),
        resolve_path(config, "accessibility_time_skims"),
        resolve_path(config, "taz_filter"),
    ]
    transit_assignment = (
        _transit_assignment_files(config)
        + _transit_assignment_files(config, converted=True)
        + _highway_assignment_files(config)
        + [resolve_path(config, "transit_mode_line_lookup")]
    )
    return {
        "network_vmt": network,
        "freeway_delay": network,
        "freeway_speed": network,
        "school_area": network + [resolve_path(config, "school_locations")],
        "best_travel_time": common_trips + [
            resolve_path(config, "time_skims_by_period", period)
            for period in config["metrics"]["best_travel_time"]["periods"]
        ],
        "vmt_rates": [
            resolve_path(config, "vmt_home_work"),
            resolve_path(config, "persons_home_work"),
            resolve_path(config, "taz_filter"),
        ],
        "active_transportation": common_trips + [
            resolve_path(config, "nonmotorized_distance_matrix")
        ],
        "person_trip_mode_share": common_trips,
        "jobs_accessible_by_transit_45": accessibility,
        "population_to_coc_by_transit_45": accessibility,
        "transit_delay": transit_assignment,
        "transit_boarding": transit_assignment + [resolve_path(config, "stop_filter_file")],
        "transit_waiting": [
            resolve_path(config, "transit_waiting_time"),
            resolve_path(config, "scenario_taz_data"),
            resolve_path(config, "taz_filter"),
        ],
    }


def missing_metric_inputs(config):
    """Return missing direct files for each enabled metric."""
    requirements = metric_input_paths(config)
    return {
        name: [Path(path) for path in requirements.get(name, []) if not Path(path).exists()]
        for name, metric in config["metrics"].items()
        if metric.get("enabled") and any(
            not Path(path).exists() for path in requirements.get(name, [])
        )
    }


def preprocessing_group_paths(config):
    """Return output files used to decide whether preprocessing can be reused."""
    highway_geometries = [
        resolve_path(config, "highway_geometry", period=period)
        for period in config["run"]["time_periods"]
    ]
    return {
        "core_summaries": [
            resolve_path(config, "vmt_home_work"),
            resolve_path(config, "persons_home_work"),
        ],
        # CUBE's shapefile export has multiple required sidecars. A .prj is not
        # required because build_highway_network applies the configured CRS.
        "highway_exports": _highway_assignment_files(config) + [
            component
            for geometry in highway_geometries
            for component in (
                geometry, geometry.with_suffix(".dbf"), geometry.with_suffix(".shx")
            )
        ],
        "highway_network": [resolve_path(config, "rtpc_highway_network")],
        "transit_sequences": _transit_assignment_files(config, converted=True),
        "transit_waiting": [resolve_path(config, "transit_waiting_time")],
        "nonmotorized": [resolve_path(config, "nonmotorized_distance_matrix")],
    }
