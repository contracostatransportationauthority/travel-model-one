"""One-time builder for the metric-ready TAZ geography filter.

The script reads ``config/taz_filter.csv``, preserves all of its existing
columns, and adds or replaces the following binary (0/1) columns:

Key O-D place flags, sourced from ``taz_city.csv``:

* ``KeyOD_Richmond``
* ``KeyOD_Downtown_Oakland``
* ``KeyOD_Walnut_Creek``
* ``KeyOD_Downtown_San_Francisco``
* ``KeyOD_Moraga``
* ``KeyOD_San_Ramon``
* ``KeyOD_Downtown_San_Jose``
* ``KeyOD_Brentwood``
* ``KeyOD_Dublin``

These flags identify the origin and destination TAZ groups used by the Best
Travel Time for Key O-D Pairs calculation.
The source ``BCMTAZID`` is zero-based, so the script adds 1 when matching it
to the model's one-based ``TAZ`` column.

RTPC flags, sourced from ``TAZ_RTPC_xwalk.csv``:

* ``RTPC_CENTRAL``
* ``RTPC_EAST``
* ``RTPC_WEST``
* ``RTPC_TRIVALLEY``
* ``RTPC_LAMORINDA``

These mutually exclusive flags provide the TAZ-to-RTPC geography used by the
VMT per Resident and Employee, Active Transportation, and Person Trip Mode
Share calculations. A row may contain all zeros when the TAZ is outside the
five CCTA RTPC areas, but it must not contain more than one RTPC flag equal to
1. The current test crosswalk has identical source counts for all five RTPCs;
the script warns about that pattern but continues so test data remain usable.

Running the script overwrites ``config/taz_filter.csv`` in place. Update the
path and source definitions immediately below if the production inputs move.
"""

import csv
import warnings
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
BASE_TAZ_FILTER = PROJECT_DIR / "config" / "taz_filter.csv"
OUTPUT_TAZ_FILTER = PROJECT_DIR / "config" / "taz_filter.csv"
TAZ_COLUMN = "TAZ"

SOURCES = {
    "key_od_place": {
        "path": PROJECT_DIR / "data_test" / "GIS_data" / "taz_city.csv",
        "taz_column": "BCMTAZID",
        "taz_offset": 1,
        "category_column": "City",
        "output_prefix": "KeyOD",
        "categories": [
            "Richmond", "Downtown Oakland", "Walnut Creek",
            "Downtown San Francisco", "Moraga", "San Ramon",
            "Downtown San Jose", "Brentwood", "Dublin",
        ],
    },
    "rtpc": {
        # Replace this test fixture with the production crosswalk before running.
        "path": PROJECT_DIR / "data_test" / "GIS_data" / "TAZ_RTPC_xwalk.csv",
        "taz_column": "BCM_TAZ",
        "category_column": "RTPC",
        "output_prefix": "RTPC",
        "categories": ["CENTRAL", "EAST", "WEST", "TRIVALLEY", "LAMORINDA"],
        "warn_equal_category_counts": True,
    },
}


def _read_csv(filename):
    with Path(filename).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def _slug(value):
    return str(value).strip().replace(" ", "_").replace("+", "Plus")


def build_taz_filters(
    input_path=BASE_TAZ_FILTER,
    output_path=OUTPUT_TAZ_FILTER,
    sources=SOURCES,
    taz_column=TAZ_COLUMN,
):
    input_path = Path(input_path)
    output_path = Path(output_path)
    rows = _read_csv(input_path)
    if not rows:
        raise ValueError("Base TAZ filter file is empty")
    if len({row[taz_column] for row in rows}) != len(rows):
        raise ValueError("Base TAZ filter contains duplicate TAZs")

    output_columns = list(rows[0])
    for source_name, source in sources.items():
        source_rows = _read_csv(source["path"])
        source_taz = source["taz_column"]
        category_column = source["category_column"]
        offset = int(source.get("taz_offset", 0))
        categories = source["categories"]
        prefix = source["output_prefix"]

        counts = {category: 0 for category in categories}
        category_by_taz = {}
        for source_row in source_rows:
            category = source_row.get(category_column)
            if category not in counts:
                continue
            taz = int(source_row[source_taz]) + offset
            previous = category_by_taz.get(taz)
            if previous is not None and previous != category:
                raise ValueError(f"TAZ {taz} has conflicting {source_name} categories")
            category_by_taz[taz] = category
            counts[category] += 1

        if source.get("warn_equal_category_counts", False):
            nonzero_counts = [count for count in counts.values() if count]
            if nonzero_counts and len(set(nonzero_counts)) == 1 and nonzero_counts[0] > 100:
                warnings.warn(
                    f"{source_name} source appears synthetic: every category has "
                    f"{nonzero_counts[0]} records; continuing because this may be test data",
                    stacklevel=2,
                )

        columns = [f"{prefix}_{_slug(category)}" for category in categories]
        for column in columns:
            if column not in output_columns:
                output_columns.append(column)
        for row in rows:
            category = category_by_taz.get(int(row[taz_column]))
            for expected, column in zip(categories, columns):
                row[column] = "1" if category == expected else "0"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=output_columns)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def main():
    output = build_taz_filters()
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
