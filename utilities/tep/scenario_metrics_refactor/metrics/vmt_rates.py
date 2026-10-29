import numpy as np
import pandas as pd

from core.geography import category_from_one_hot


def calculate_vmt_rates(vmt_data, persons_data, taz_filters):
    """Calculate residential VMT/resident and workplace VMT/employee by RTPC."""
    residence = vmt_data.groupby("taz", as_index=False)["vmt"].sum().rename(
        columns={"vmt": "total_resident_vmt"})
    residents = persons_data.groupby("taz", as_index=False)["freq"].sum().rename(
        columns={"freq": "total_residents"})
    workplace = vmt_data.groupby("WorkLocation", as_index=False)["vmt"].sum().rename(
        columns={"WorkLocation": "taz", "vmt": "total_employee_vmt"})
    employees = persons_data.groupby("WorkLocation", as_index=False)["freq"].sum().rename(
        columns={"WorkLocation": "taz", "freq": "total_employees"})
    detail = residence.merge(residents, on="taz", how="outer").merge(
        workplace, on="taz", how="outer").merge(employees, on="taz", how="outer")
    lookup = category_from_one_hot(taz_filters, "RTPC").rename(columns={"TAZ": "taz"})
    detail = detail.merge(lookup, on="taz", how="left", validate="many_to_one")
    totals = detail.groupby("RTPC", dropna=True, as_index=False)[
        ["total_resident_vmt", "total_residents", "total_employee_vmt", "total_employees"]
    ].sum()
    totals["residential_vmt_per_capita"] = totals["total_resident_vmt"].div(
        totals["total_residents"].replace(0, np.nan))
    totals["vmt_per_employee"] = totals["total_employee_vmt"].div(
        totals["total_employees"].replace(0, np.nan))
    return totals, detail
