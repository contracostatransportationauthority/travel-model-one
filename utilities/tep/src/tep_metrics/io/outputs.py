from pathlib import Path
from tep_metrics.core.config import resolve_path


def write_metric(data, config, filename):
    output_dir = resolve_path(config, "metrics_output_dir")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_file = Path(output_dir) / filename
    data.to_csv(output_file, index=False)
    print(f"Wrote {output_file}")
    return output_file
