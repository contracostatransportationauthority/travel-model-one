from pathlib import Path
import sqlite3

import pandas as pd

from tep_metrics.core.config import resolve_path
from tep_metrics.io.validation import require_columns


def load_taz_data(config):
    return pd.read_csv(resolve_path(config, "scenario_taz_data"))


def load_time_skims(config):
    return pd.read_csv(resolve_path(config, "accessibility_time_skims"))


def load_transit_mode_line(config):
    return pd.read_csv(resolve_path(config, "transit_mode_line_lookup"))

def load_transit_line(config):
    return pd.read_csv(resolve_path(config, "trnline_file"))

def load_transit_link(config):
    return pd.read_csv(resolve_path(config, "trnlink_file"))

def load_transit_waiting(config):
    data = pd.read_csv(resolve_path(config, "transit_waiting_time"), low_memory=False)
    # CUBE text exports may include a DOS end-of-file marker as a final row.
    data["TAZ"] = pd.to_numeric(data["TAZ"], errors="coerce")
    return data.loc[data["TAZ"].notna()].copy()

def load_transit_stop_filter(config):
    return pd.read_csv(resolve_path(config, "stop_filter_file"))

def load_highway_network(config):
    # Keep this optional-format dependency lazy so CSV-only runs stay quiet.
    from simpledbf import Dbf5

    frames = []
    iteration = config["run"]["iteration"]
    for period in config["run"]["time_periods"]:
        template = config["paths"]["scenario_files"].get("highway_assignment_file")
        if template:
            filename = resolve_path(config, "highway_assignment_file",
                                    iteration=iteration, period=period)
        else:
            directory = resolve_path(config, "highway_assignment_dir",
                                     iteration=iteration)
            filename = directory / f"load{period}.dbf"
        frame = Dbf5(str(filename)).to_dataframe()[config["highway_columns"]].copy()
        frame["timeperiod"] = period
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def load_transit_links(config):
    names = ["A", "B", "time", "mode", "PLOT", "STOP_A", "STOP_B", "distance", "name", "OWNER", "AB_VOL", "Boardings", "AB_XITA", "AB_BRDB", "AB_XITB", "BA_VOL", "BA_BRDA", "BA_XITA", "BA_BRDB", "BA_XITB", "MATRIX"]
    usecols = ["A", "B", "time", "mode", "distance", "name", "AB_VOL", "Boardings"]
    frames = []
    iteration = config["run"]["iteration"]
    directory = resolve_path(config, "transit_assignment_dir", iteration=iteration)
    for period in config["run"]["time_periods"]:
        for mode in config["transit_modes"]:
            stem = f"trnlink{period.lower()}_{mode}"
            csv_file = directory / f"{stem}.csv"
            seq_file = directory / f"{stem}_converted.csv"
            frame = pd.read_csv(csv_file, names=names, usecols=usecols)
            sequence = pd.read_csv(seq_file, usecols=["SEQ"])
            frame["SEQ"] = sequence["SEQ"].to_numpy()[:len(frame)]
            frame["timeperiod"] = period
            frame = frame[~frame["name"].astype(str).str.contains("*", regex=False, na=False)]
            frames.append(frame)
    links = pd.concat(frames, ignore_index=True)
    return links.groupby(["A", "B", "name", "mode", "SEQ"], as_index=False).agg(time=("time", "mean"), distance=("distance", "mean"), AB_VOL=("AB_VOL", "sum"), Boardings=("Boardings", "sum"))


def load_prepared_highway_network(filename, layer=None):
    """Load the notebook's prepared link network from a GeoPackage or shapefile."""
    path = Path(filename)
    if path.suffix.lower() == ".gpkg":
        if not layer:
            raise ValueError("A GeoPackage layer name is required")
        with sqlite3.connect(path) as connection:
            columns = pd.read_sql_query(
                f'PRAGMA table_info("{layer}")', connection
            )["name"].tolist()
            selected = [name for name in columns if name not in {"fid", "geom"}]
            quoted = ", ".join(f'"{name}"' for name in selected)
            network = pd.read_sql_query(
                f'SELECT {quoted} FROM "{layer}"', connection
            )
    else:
        try:
            import geopandas as gpd
        except ImportError as exc:
            raise RuntimeError(
                "GeoPandas is required for prepared network formats other than GeoPackage."
            ) from exc
        network = gpd.read_file(path)
    periods = ("EA", "AM", "MD", "PM", "EV")
    required = ["A", "B", "DISTANCE", "FFS", "RTPC", "ROADWAY", "NAME"]
    for period in periods:
        required.extend([
            f"CSPD_{period}", f"VOL_PAX_VEH_{period}",
            f"VOL_SM_{period}", f"VOL_HV_{period}",
        ])
    require_columns(network, required, "prepared highway network")
    if network.duplicated(["A", "B"]).any():
        raise ValueError("Prepared highway network contains duplicate A-B links")
    return network


def load_trip_tables(individual_file, joint_file, usecols=None):
    return (
        pd.read_csv(individual_file, usecols=usecols),
        pd.read_csv(joint_file, usecols=usecols),
    )


def load_filtered_time_skims(filename, route_pairs, chunksize=250_000):
    """Read a large skim CSV and retain only configured route OD pairs."""
    mode_columns = [
        "da", "daToll", "s2", "s2Toll", "s3", "s3Toll", "wTrnW", "dTrnW"
    ]
    pairs = route_pairs[["orig", "dest"]].drop_duplicates()
    frames = []
    for chunk in pd.read_csv(filename, usecols=["orig", "dest"] + mode_columns,
                             chunksize=chunksize, skipinitialspace=True):
        selected = chunk.merge(pairs, on=["orig", "dest"], how="inner")
        if not selected.empty:
            frames.append(selected)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=["orig", "dest"] + mode_columns)


def load_prepared_highway_geodata(filename, layer=None):
    try:
        import geopandas as gpd
    except ImportError as exc:
        raise RuntimeError("GeoPandas is required for the school-area spatial metric") from exc
    kwargs = {"layer": layer} if layer else {}
    return gpd.read_file(filename, **kwargs)


def load_active_distances(filename):
    """Load a CUBE-exported nonmotorized distance table."""
    path = Path(filename)
    try:
        data = pd.read_csv(path)
    except (UnicodeDecodeError, pd.errors.ParserError):
        from simpledbf import Dbf5

        data = Dbf5(str(path)).to_dataframe()
    data.columns = [column.upper() for column in data.columns]
    required = ["ORIG", "DEST", "DIST", "DISTWALK", "DISTBIKE"]
    require_columns(data, required, "nonmotorized distance export")
    return data[required].rename(columns={
        "ORIG": "orig_taz", "DEST": "dest_taz", "DIST": "distance_miles",
        "DISTWALK": "walk_miles", "DISTBIKE": "bike_miles",
    })
