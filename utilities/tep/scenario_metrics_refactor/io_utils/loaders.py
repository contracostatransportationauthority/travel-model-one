from pathlib import Path
import pandas as pd
from simpledbf import Dbf5
from core.config import resolve_model_path


def load_taz_data(config):
    return pd.read_csv(resolve_model_path(config, key="taz_data"))


def load_time_skims(config):
    return pd.read_csv(resolve_model_path(config, key="time_skims"))


def load_transit_mode_line(config):
    return pd.read_csv(resolve_model_path(config, key="transit_mode_line"))

def load_transit_line(config):
    return pd.read_csv(resolve_model_path(config, key="trnline_file"))

def load_transit_link(config):
    return pd.read_csv(resolve_model_path(config, key="trnlink_file"))

def load_transit_waiting(config):
    return pd.read_csv(resolve_model_path(config, key="transit_waiting_time"))

def load_transit_stop_filter(config):
    return pd.read_csv(resolve_model_path(config, key="stop_filter_file"))

def load_highway_network(config):
    frames = []
    iteration = config["run"]["iteration"]
    directory = resolve_model_path(config, key="highway_assignment_dir").format(iteration=iteration)
    for period in config["run"]["time_periods"]:
        filename = resolve_model_path(config, str(Path(directory) / f"load{period}.dbf"))
        frame = Dbf5(str(filename)).to_dataframe()[config["highway_columns"]].copy()
        frame["timeperiod"] = period
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


def load_transit_links(config):
    names = ["A", "B", "time", "mode", "PLOT", "STOP_A", "STOP_B", "distance", "name", "OWNER", "AB_VOL", "Boardings", "AB_XITA", "AB_BRDB", "AB_XITB", "BA_VOL", "BA_BRDA", "BA_XITA", "BA_BRDB", "BA_XITB", "MATRIX"]
    usecols = ["A", "B", "time", "mode", "distance", "name", "AB_VOL", "Boardings"]
    frames = []
    iteration = config["run"]["iteration"]
    directory = resolve_model_path(config, key="transit_assignment_dir").format(iteration=iteration)
    for period in config["run"]["time_periods"]:
        for mode in config["transit_modes"]:
            stem = f"trnlink{period.lower()}_{mode}"
            csv_file = resolve_model_path(config, str(Path(directory) / f"{stem}.csv"))
            seq_file = resolve_model_path(config, str(Path(directory) / f"{stem}_converted.csv"))
            frame = pd.read_csv(csv_file, names=names, usecols=usecols)
            sequence = pd.read_csv(seq_file, usecols=["SEQ"])
            frame["SEQ"] = sequence["SEQ"].to_numpy()[:len(frame)]
            frame["timeperiod"] = period
            frame = frame[~frame["name"].astype(str).str.contains("*", regex=False, na=False)]
            frames.append(frame)
    links = pd.concat(frames, ignore_index=True)
    return links.groupby(["A", "B", "name", "mode", "SEQ"], as_index=False).agg(time=("time", "mean"), distance=("distance", "mean"), AB_VOL=("AB_VOL", "sum"), Boardings=("Boardings", "sum"))
