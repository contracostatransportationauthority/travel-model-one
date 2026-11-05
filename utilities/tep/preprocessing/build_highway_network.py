"""Build the five-period, RTPC-tagged highway GeoPackage used by TEP metrics.

CUBE first exports all five final assignment networks as geometry shapefiles
and DBF tables. This script performs the remaining
portable preprocessing: it combines the periods, calculates passenger-vehicle
volumes, assigns RTPCs by link midpoint, and writes the metric-ready GeoPackage.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import warnings

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


def align_spatial_crs(
    geometry: gpd.GeoDataFrame,
    rtpc: gpd.GeoDataFrame,
    assumed_geometry_crs: str | None,
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    """Assign a configured CRS to a naive CUBE export and align RTPC polygons."""
    if geometry.crs is None:
        if not assumed_geometry_crs:
            raise ValueError(
                "CUBE highway geometry has no CRS. Set run.highway_geometry_crs "
                "to the native CRS of the model network."
            )
        geometry = geometry.set_crs(assumed_geometry_crs, allow_override=True)
        print(
            "CUBE highway geometry has no embedded CRS; "
            f"using configured CRS {geometry.crs}."
        )
    if rtpc.crs is None:
        raise ValueError(
            "RTPC boundaries have no CRS. Restore the .prj file alongside the "
            "configured RTPC shapefile."
        )

    rtpc = rtpc.to_crs(geometry.crs)
    gx_min, gy_min, gx_max, gy_max = geometry.total_bounds
    rx_min, ry_min, rx_max, ry_max = rtpc.total_bounds
    overlaps = gx_max >= rx_min and rx_max >= gx_min and gy_max >= ry_min and ry_max >= gy_min
    if not overlaps:
        raise ValueError(
            "Highway geometry and RTPC boundaries do not overlap after CRS alignment. "
            f"Highway bounds: {geometry.total_bounds.tolist()}; RTPC bounds: "
            f"{rtpc.total_bounds.tolist()}. Check run.highway_geometry_crs."
        )
    return geometry, rtpc


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

    geometry_frames = []
    for period in PERIODS:
        period_geometry = gpd.read_file(
            resolve_path(config, "highway_geometry", period=period)
        )
        require_columns(
            period_geometry,
            ["A", "B", "NAME", "ROADWAY", "geometry"],
            f"{period} CUBE highway geometry",
        )
        if period_geometry.crs is None:
            configured_crs = config["run"].get("highway_geometry_crs")
            if not configured_crs:
                raise ValueError(
                    "CUBE highway geometry has no CRS. Set run.highway_geometry_crs "
                    "to the native CRS of the model network."
                )
            period_geometry = period_geometry.set_crs(configured_crs)
        geometry_frames.append(
            period_geometry[["A", "B", "NAME", "ROADWAY", "geometry"]]
        )
    geometry = gpd.GeoDataFrame(
        pd.concat(geometry_frames, ignore_index=True),
        geometry="geometry",
        crs=geometry_frames[0].crs,
    ).drop_duplicates(["A", "B"], keep="first")

    rtpc = gpd.read_file(resolve_path(config, "rtpc_boundaries"))
    require_columns(rtpc, ["SUBAREA", "geometry"], "RTPC boundaries")
    geometry, rtpc = align_spatial_crs(
        geometry, rtpc, config["run"].get("highway_geometry_crs")
    )
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
    output = resolve_path(config, "rtpc_highway_network")
    output.parent.mkdir(parents=True, exist_ok=True)
    if final.geometry.isna().any():
        count = int(final.geometry.isna().sum())
        if count == len(final):
            raise ValueError("Prepared highway network has no links with geometry")
        audit_output = output.with_name(
            f"{output.stem}_links_without_geometry.csv"
        )
        final.loc[final.geometry.isna()].drop(columns="geometry").to_csv(
            audit_output, index=False
        )
        warnings.warn(
            f"Prepared highway network has {count} links omitted by all CUBE "
            "geometry exports. They are retained for non-spatial and countywide "
            f"metrics but excluded from spatial RTPC/school calculations. Audit: "
            f"{audit_output}",
            stacklevel=2,
        )

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
