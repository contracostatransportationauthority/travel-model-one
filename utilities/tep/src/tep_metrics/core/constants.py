COUNTY_CODES = {
    1: "San Francisco", 2: "San Mateo", 3: "Santa Clara",
    4: "Alameda", 5: "Contra Costa", 6: "Solano",
    7: "Napa", 8: "Sonoma", 9: "Marin", 10: "San Joaquin",
}

COUNTY_NODE_RANGES = [
    (1000000, 1500000, "San Francisco"),
    (1500000, 2000000, "San Mateo"),
    (2000000, 2500000, "Santa Clara"),
    (2500000, 3000000, "Alameda"),
    (3000000, 3500000, "Contra Costa"),
    (3500000, 4000000, "Solano"),
    (4000000, 4500000, "Napa"),
    (4500000, 5000000, "Sonoma"),
    (5000000, 5500000, "Marin"),
]

ACCESS_MODES = list(range(1, 10))
FERRY_MODES = list(range(100, 110))
LIGHT_RAIL_MODES = list(range(110, 120))
HEAVY_RAIL_MODES = list(range(120, 130))
COMMUTER_RAIL_MODES = list(range(130, 140))
EXCLUDED_TRANSIT_MODES = ACCESS_MODES + FERRY_MODES + LIGHT_RAIL_MODES + HEAVY_RAIL_MODES + COMMUTER_RAIL_MODES
