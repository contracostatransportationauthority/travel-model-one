import pandas as pd
from core.constants import COUNTY_NODE_RANGES


def county_from_node(node):
    if pd.isna(node):
        return None
    node = int(node)
    for low, high, county in COUNTY_NODE_RANGES:
        if low <= node < high:
            return county
    return None
