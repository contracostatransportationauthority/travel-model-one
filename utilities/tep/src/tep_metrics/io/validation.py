def require_columns(data, columns, dataset_name):
    missing = sorted(set(columns) - set(data.columns))
    if missing:
        raise ValueError(f"{dataset_name} is missing required columns: {missing}")
