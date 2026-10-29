import json
from pathlib import Path


def load_config(filename):
    config_path = Path(filename).resolve()
    with config_path.open("r", encoding="utf-8") as stream:
        config = json.load(stream)
    base_dir = Path(config.get("paths", {}).get("base_dir", "."))
    if not base_dir.is_absolute():
        base_dir = config_path.parent / base_dir
    config["_base_dir"] = str(base_dir.resolve())
    return config


def resolve_path(config, value):
    """Resolve an input or output path against the configured base directory."""
    path = Path(value)
    if path.is_absolute():
        return path
    return (Path(config["_base_dir"]) / path).resolve()
