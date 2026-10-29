# import json
# from pathlib import Path


# def load_config(filename):
#     path = Path(filename).resolve()
#     with path.open("r", encoding="utf-8") as stream:
#         config = json.load(stream)
#     config["_config_dir"] = str(path.parent)
#     return config


# def resolve_model_path(config, key):
#     output_dir = Path(config["paths"]["output_dir"])

#     if not output_dir.is_absolute():
#         output_dir = (Path(config["_config_dir"]) / output_dir).resolve()

#     paths = config["paths"]

#     if key in paths["scenario_files"]:
#         return output_dir / paths["scenario_files"][key]

#     if key in paths["reference_files"]:
#         return Path(paths["reference_files"][key])

#     raise KeyError(f"Unknown path key: {key}")
