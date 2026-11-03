"""Build the five-period, RTPC-tagged highway GeoPackage used by TEP metrics.

CUBE first exports the final AM network as a geometry shapefile and all five
final assignment networks as DBF tables. This script performs the remaining
portable preprocessing: it combines the periods, calculates passenger-vehicle
volumes, assigns RTPCs by link midpoint, and writes the metric-ready GeoPackage.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import pandas as pd

from tep_metrics.core.config import load_config, resolve_path
from tep_metrics.io.validation import require_columns


PERIODS = ("EA", "AM", "MD", "PM", "EV")
PAX_VOLUME_COLUMNS = (
    "VOL_DA", "VOL_S2", "VOL_S3", "VOL_DAT", "VOL_S2T", "VOL_S3T",
    "VOL_DAAV", "VOL_S2AV", "VOL_S3AV",
)
STATIC_COLUMNS = ("FT", "DISTANCE", "FFS")
DYNAMIC_COLUMNS = ("CSPD", "VOL_SM", "VOL_HV")


def combine_highway_periods(period_frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Combine five CUBE link tables into one wide A-B link table."""
    if set(period_frames) != set(PERIODS):
        raise ValueError(f"Expected period tables for {PERIODS}")

    prepared = {}
    static_frames = []
    required = ["A", "B", *STATIC_COLUMNS, *DYNAMIC_COLUMNS, *PAX_VOLUME_COLUMNS]
    for period in PERIODS:
        frame = period_frames[period].copy()
        require_columns(frame, required, f"{period} highway network")
        if "COUNTY" in frame:
            frame = frame.loc[frame["COUNTY"].eq("Contra Costa")].copy()
        if frame.duplicated(["A", "B"]).any():
            raise ValueError(f"{period} highway network contains duplicate A-B links")

        frame["VOL_PAX_VEH"] = frame[list(PAX_VOLUME_COLUMNS)].sum(axis=1)
        static_frames.append(frame[["A", "B", *STATIC_COLUMNS]])
        dynamic = frame[["A", "B", *DYNAMIC_COLUMNS, "VOL_PAX_VEH"]].copy()
        prepared[period] = dynamic.rename(columns={
            column: f"{column}_{period}"
            for column in (*DYNAMIC_COLUMNS, "VOL_PAX_VEH")
        })

    static = pd.concat(static_frames, ignore_index=True).drop_duplicates(["A", "B"])
    combined = static
    for period in PERIODS:
        combined = combined.merge(prepared[period], on=["A", "B"], how="outer",
                                  validate="one_to_one")
    return combined


def build_highway_network(config: dict) -> Path:
    """Create the configured RTPC highway GeoPackage and return its path."""
    iteration = config["run"]["iteration"]
    period_frames = {}
    read_columns = [
        "A", "B", "COUNTY", *STATIC_COLUMNS, *DYNAMIC_COLUMNS,
        *PAX_VOLUME_COLUMNS,
    ]
    for period in PERIODS:
        filename = resolve_path(
            config, "highway_assignment_file", iteration=iteration, period=period
        )
        period_frames[period] = pd.DataFrame(
            gpd.read_file(filename, columns=read_columns, engine="pyogrio")
        )

    combined = combine_highway_periods(period_frames)

    geometry = gpd.read_file(resolve_path(config, "highway_geometry"))
    require_columns(geometry, ["A", "B", "NAME", "ROADWAY", "geometry"],
                    "CUBE highway geometry")
    geometry = geometry[["A", "B", "NAME", "ROADWAY", "geometry"]].drop_duplicates(
        ["A", "B"], keep="first"
    )

    rtpc = gpd.read_file(resolve_path(config, "rtpc_boundaries"))
    require_columns(rtpc, ["SUBAREA", "geometry"], "RTPC boundaries")
    rtpc = rtpc.to_crs(geometry.crs)
    centers = gpd.GeoDataFrame(
        geometry=geometry.geometry.interpolate(0.5, normalized=True),
        crs=geometry.crs,
        index=geometry.index,
    )
    joined = gpd.sjoin(
        centers, rtpc[["SUBAREA", "geometry"]], how="left", predicate="within"
    )
    geometry["RTPC"] = joined.groupby(level=0)["SUBAREA"].first()

    final = gpd.GeoDataFrame(
        combined.merge(geometry, on=["A", "B"], how="left", validate="one_to_one"),
        geometry="geometry",
        crs=geometry.crs,
    )
    if final.geometry.isna().any():
        count = int(final.geometry.isna().sum())
        raise ValueError(f"Prepared highway network has {count} links without geometry")

    output = resolve_path(config, "rtpc_highway_network")
    output.parent.mkdir(parents=True, exist_ok=True)
    final.to_file(
        output,
        layer=config["run"]["rtpc_highway_network_layer"],
        driver="GPKG",
    )
    print(f"Wrote {len(final):,} highway links to {output}")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/scenario_metrics.json")
    args = parser.parse_args()
    build_highway_network(load_config(args.config))


if __name__ == "__main__":
    main()
