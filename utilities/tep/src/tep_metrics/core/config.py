import json
from pathlib import Path


def load_config(filename):
    config_path = Path(filename).resolve()
    with config_path.open("r", encoding="utf-8") as stream:
        config = json.load(stream)
    config["_config_dir"] = str(config_path.parent)
    scenario_dir = Path(config["paths"]["scenario_dir"])
    if not scenario_dir.is_absolute():
        scenario_dir = config_path.parent / scenario_dir
    config["_scenario_dir"] = str(scenario_dir.resolve())
    return config


def resolve_path(config, key, item=None, **format_values):
    """Resolve a named scenario or reference path using its declared root."""
    paths = config["paths"]
    if key in paths["scenario_files"]:
        value = paths["scenario_files"][key]
        root = Path(config["_scenario_dir"])
    elif key in paths["reference_files"]:
        value = paths["reference_files"][key]
        root = Path(config["_config_dir"])
    else:
        raise KeyError(f"Unknown configured path: {key}")
    if item is not None:
        value = value[item]
    value = str(value).format(**format_values)
    path = Path(value)
    if path.is_absolute():
        return path
    return (root / path).resolve()
