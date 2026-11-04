# TEP Metrics Output Data Dictionary

All enabled metrics write CSV files to `<scenario>/tep_metrics/`. Output names
are configurable in `config/scenario_metrics.json`; the names below are the
checked-in defaults.

## Output inventory

| Metric | Implementation origin | Default output | Row grain |
| --- | --- | --- | --- |
| Network VMT | CTP metric from `Future_No_Project_CombinedPerformanceMeasures.ipynb` | `network_vmt_by_rtpc.csv` | RTPC and countywide summary |
| Freeway Delay | CTP metric from `Future_No_Project_CombinedPerformanceMeasures.ipynb` | `freeway_delay_by_name.csv` | Freeway name |
| Freeway Speed | CTP metric from `Future_No_Project_CombinedPerformanceMeasures.ipynb` | `freeway_speed_by_link.csv` | Directed freeway mainline link |
| Best Travel Time | CTP metric from `Future_No_Project_CombinedPerformanceMeasures.ipynb` | `best_travel_time_{AM,MD,PM}.csv` | Key route and time period |
| School-Area VMT | CTP metric from `Future_No_Project_CombinedPerformanceMeasures.ipynb` | `school_area_vmt_by_rtpc.csv` | RTPC and countywide summary |
| School-Area Average Speed | CTP metric from `Future_No_Project_CombinedPerformanceMeasures.ipynb` | `school_area_average_speed_by_rtpc.csv` | RTPC and countywide summary |
| VMT Rates | CTP metric from `Future_No_Project_CombinedPerformanceMeasures.ipynb` | `vmt_rates_by_rtpc.csv` | RTPC |
| VMT Rate Detail | CTP metric from `Future_No_Project_CombinedPerformanceMeasures.ipynb` | `vmt_rates_by_taz.csv` | TAZ |
| Active Transportation | CTP metric from `Future_No_Project_CombinedPerformanceMeasures.ipynb` | `active_transportation_by_rtpc.csv` | RTPC/countywide and active mode |
| Combined Walk/Bike | CTP metric from `Future_No_Project_CombinedPerformanceMeasures.ipynb` | `combined_walk_bike_by_rtpc.csv` | RTPC and countywide summary |
| Person Trip Mode Share | CTP metric from `Future_No_Project_CombinedPerformanceMeasures.ipynb` | `person_trip_mode_share_by_rtpc.csv` | RTPC and countywide summary |
| Jobs Accessible by Transit | New TEP metric | `accessibility_jobs_transit_45.csv` | Origin TAZ |
| Population with Transit Access to COC | New TEP metric | `population_share_coc_transit_45.csv` | Origin TAZ |
| Transit In-Vehicle Delay | New TEP metric | `transit_in_vehicle_delay.csv` | County, agency, and time period |
| Transit Boardings | New TEP metric | `transit_boardings.csv` | County, agency, and technology |
| Transit Boardings at Selected Stops | New TEP metric | `transit_boardings_by_stops.csv` | County, agency, and technology |
| Transit Waiting Time | New TEP metric | `transit_waiting_time.csv` | County, transit mode, and access mode |

## Network VMT

File: `network_vmt_by_rtpc.csv`

Includes all prepared Contra Costa highway links. Freeway values include links
classified as `motorway` or `motorway_link`.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `RTPC` | text | — | RTPC name or the countywide summary label. |
| `PAX_VMT_DAILY` | number | vehicle-miles/day | Passenger-vehicle volume multiplied by link distance, summed across periods and links. |
| `TRUCK_VMT_DAILY` | number | vehicle-miles/day | Small- and heavy-truck volume multiplied by link distance, summed across periods and links. |
| `PAX_VMT_DAILY_FREEWAY` | number | vehicle-miles/day | Passenger VMT on freeway links only. |
| `TRUCK_VMT_DAILY_FREEWAY` | number | vehicle-miles/day | Truck VMT on freeway links only. |

## Freeway Delay

File: `freeway_delay_by_name.csv`

Includes `motorway` and `motorway_link` records. Passenger delay is calculated
from congested speed relative to free-flow speed and is clipped at zero.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `NAME` | text | — | Highway/freeway facility name. |
| `PAX_DELAY_{PERIOD}_HR` | number | passenger vehicle-hours | Period passenger delay summed across links with this name. One column for each model period. |
| `PAX_DELAY_DAILY_HR` | number | passenger vehicle-hours/day | Sum of the five period delay values. |

## Freeway Speed

File: `freeway_speed_by_link.csv`

Includes only links classified as freeway mainline (`motorway`).

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `A`, `B` | integer | — | Directed link node identifiers. |
| `NAME` | text | — | Highway/freeway facility name. |
| `RTPC` | text | — | RTPC containing the link midpoint. |
| `FFS` | number | miles/hour | Free-flow speed. |
| `CSPD_AM`, `CSPD_PM` | number | miles/hour | Congested AM or PM link speed. |
| `SPEED_RATIO_AM`, `SPEED_RATIO_PM` | number | ratio | Congested speed divided by free-flow speed. Values below 1 indicate slower-than-free-flow operation. |

## Best Travel Time

Files: `best_travel_time_AM.csv`, `best_travel_time_MD.csv`, and
`best_travel_time_PM.csv`

Only modes observed in individual or joint trip records for a configured key
route are eligible for the minimum travel-time calculation.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `route` | text | — | Configured directed key route, such as Richmond–Downtown Oakland. |
| `TOD` | text | — | `AM`, `MD`, or `PM`. |
| `trips_total` | number | trip records | Observed trip records on the route using modes represented in the skim-mode mapping. Joint trips are records here, not expanded participants. |
| `minTT` | number | minutes | Minimum travel time among all observed eligible modes and route OD pairs. |
| `drive_trips_total` | number | trip records | Observed drive-mode trip records. |
| `min_driveTT` | number | minutes | Minimum travel time among observed drive modes. |
| `trn_trips_total` | number | trip records | Observed walk- or drive-access transit trip records. |
| `min_trnTT` | number | minutes | Minimum travel time among observed transit modes. |

## School-Area VMT

File: `school_area_vmt_by_rtpc.csv`

Links intersecting the configured school buffer—currently 0.5 mile—are
included. Freeway mainline links (`motorway`) are excluded from the spatial
selection.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `RTPC` | text | — | RTPC name or countywide summary label. |
| `PAX_VMT_DAILY` | number | vehicle-miles/day | Daily passenger VMT on selected school-area links. |
| `TRUCK_VMT_DAILY` | number | vehicle-miles/day | Daily small- plus heavy-truck VMT on selected school-area links. |

## School-Area Average Speed

File: `school_area_average_speed_by_rtpc.csv`

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `RTPC` | text | — | RTPC name or countywide summary label. |
| `AVG_SPEED_AM`, `AVG_SPEED_PM` | number | miles/hour | Passenger-VMT divided by passenger-VHT on valid school-area links; a volume-weighted harmonic speed. |

## VMT Rates

File: `vmt_rates_by_rtpc.csv`

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `RTPC` | text | — | RTPC associated with the home or workplace TAZ. |
| `total_resident_vmt` | number | vehicle-miles | VMT grouped by home TAZ and summed to RTPC. |
| `total_residents` | number | weighted persons | Person-frequency denominator grouped by home TAZ. |
| `total_employee_vmt` | number | vehicle-miles | VMT grouped by workplace TAZ and summed to RTPC. |
| `total_employees` | number | weighted persons/jobs | Person-frequency denominator grouped by workplace TAZ. |
| `residential_vmt_per_capita` | number | vehicle-miles/resident | `total_resident_vmt / total_residents`. |
| `vmt_per_employee` | number | vehicle-miles/employee | `total_employee_vmt / total_employees`. |

File: `vmt_rates_by_taz.csv`

Contains the same four totals before RTPC aggregation, plus `taz` and its
assigned `RTPC`. Rate columns are intentionally calculated only after RTPC
aggregation.

## Active Transportation

File: `active_transportation_by_rtpc.csv`

The checked-in distance threshold is 3 miles. `person_trips` counts individual
trips as one and joint trips by their number of participants.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `RTPC` | text | — | Origin RTPC or countywide summary label. |
| `Mode` | text | — | `Walk` or `Bike`. |
| `All_Person_Trips_Under_3_Miles` | number | person trips | All-mode person trips with general OD distance below 3 miles. Repeated for each active mode. |
| `Mode_Person_Trips_Under_3_Miles` | number | person trips | Walk or bike person trips with general OD distance below 3 miles. |
| `Mode_Share_Under_3_Miles_Pct` | number | percent | Mode person trips under 3 miles divided by all person trips under 3 miles. |
| `Number_of_Person_Trips` | number | person trips | All person trips using this active mode, regardless of distance. |
| `Average_Distance_Miles` | number | miles/trip | Person-trip-weighted walk or bike skim distance for records with valid distance. |
| `Trips_With_Valid_Distance` | number | person trips | Denominator used for average active-mode distance. |

File: `combined_walk_bike_by_rtpc.csv`

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `RTPC` | text | — | Origin RTPC or countywide summary label. |
| `All_Person_Trips_Under_3_Miles` | number | person trips | All-mode person trips below the distance threshold. |
| `Walk_Bike_Trips_Under_3_Miles` | number | person trips | Walk plus bike person trips below the threshold. |
| `Walk_Bike_Total_Person_Trips` | number | person trips | All walk plus bike person trips, regardless of distance. |
| `Walk_Bike_Share_Under_3_Miles_Pct` | number | percent | Walk/bike trips under 3 miles divided by all trips under 3 miles. |

## Person Trip Mode Share

File: `person_trip_mode_share_by_rtpc.csv`

Rows are assigned by origin TAZ. Individual trips count as one person trip;
joint trips count by participants.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `RTPC` | text | — | Origin RTPC or countywide summary label. |
| `DA` | number | percent | Drive-alone share, including toll and non-toll modes. |
| `SR2` | number | percent | Two-person shared-ride share, including toll and non-toll modes. |
| `SR3+` | number | percent | Three-or-more-person shared-ride share, including toll and non-toll modes. |
| `Transit` | number | percent | Walk- and drive-access transit share. |
| `Nonmotorized` | number | percent | Walk plus bike share. |
| `Taxi/TNC` | number | percent | Taxi and transportation-network-company share. |
| `Total_Share` | number | percent | Sum of the six reported mode shares; expected to be approximately 100. |

## Jobs Accessible by Transit

File: `accessibility_jobs_transit_45.csv`

The checked-in metric uses walk-access transit time (`wTrnW`), a 45-minute
threshold, Contra Costa origins, and total employment (`TOTEMP`) at destinations.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `orig` | integer | TAZ | Origin TAZ. |
| `accessible_total` | number | jobs | Destination employment reachable within the configured threshold. |
| `origin_population` | number | persons | Population of the origin TAZ; available for population-weighted summaries. |
| `origin_filter` | text | — | Geography filter used to select origins. |
| `destination_measure` | text | — | Name of the zonal destination field; currently `TOTEMP`. |
| `skim_column` | text | — | Travel-time skim used; currently `wTrnW`. |
| `threshold` | number | minutes | Maximum eligible travel time; currently 45. |

## Population with Transit Access to Communities of Concern

File: `population_share_coc_transit_45.csv`

An origin is eligible when at least one destination flagged as a Community of
Concern can be reached by walk-access transit within 45 minutes.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `orig` | integer | TAZ | Origin TAZ. |
| `eligible_origin` | number | persons | Origin population when the origin is eligible; otherwise zero. |
| `origin_total` | number | persons | Total population in the configured origin geography, repeated on each row. |
| `origin_filter` | text | — | Geography filter used to select origins. |
| `destination_filter` | text | — | Destination binary filter; currently `CommunitiesOfConcern`. |
| `skim_column` | text | — | Travel-time skim used; currently `wTrnW`. |
| `threshold` | number | minutes | Maximum eligible travel time; currently 45. |

For a geography-level share, sum `eligible_origin` and divide by the single
`origin_total` value; do not sum the repeated denominator.

## Transit In-Vehicle Delay

File: `transit_in_vehicle_delay.csv`

The checked-in output is filtered to Contra Costa, Alameda, and San Francisco.
Expected bus travel time is estimated from highway free-flow time, distance,
facility type, area type, and BRT treatment; observed assigned transit time is
compared against that estimate.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `COUNTY` | text | — | County assigned from the highway link or node range. |
| `Agency` | text | — | Transit agency from `transitModeAndLine.csv`. |
| `timeperiod` | text | — | Model time period. |
| `Total In-Vehicle Hours of Delay` | number | passenger-hours | Link transit volume multiplied by observed-minus-expected in-vehicle time, summed to the row grain. |
| `Boardings` | number | boardings | Boardings carried through the same grouping for context. |

## Transit Boardings

Files: `transit_boardings.csv` and `transit_boardings_by_stops.csv`

The first file includes all eligible transit links. The second includes only
records whose `A` node appears in `transit_stops.csv`. Both are filtered to the
counties configured for the metric.

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `COUNTY` | text | — | County assigned from the highway link or node range. |
| `Agency` | text | — | Transit agency from `transitModeAndLine.csv`. |
| `Technology` | text | — | Transit technology; Cable Car is consolidated into Bus. |
| `{PERIOD}` | number | boardings | Total boardings for an available model period, normally `EA`, `AM`, `MD`, `PM`, and `EV`. |
| `Daily` | number | boardings/day | Sum of all period columns present in the output. |

## Transit Waiting Time

File: `transit_waiting_time.csv`

| Column | Type | Unit | Definition |
| --- | --- | --- | --- |
| `COUNTY` | text | — | County of the origin TAZ. |
| `Transit Mode` | text | — | Consolidated transit mode: Commuter Rail, Heavy Rail, Bus, or Light Rail. |
| `Access` | text | — | Access mode supplied by the CUBE summary, such as walk or drive access. |
| `{PERIOD} Init wait hours` | number | passenger-hours | Initial waiting hours for Daily or a model period. |
| `{PERIOD} Xfer wait hours` | number | passenger-hours | Transfer waiting hours for Daily or a model period. |
| `Total {PERIOD} Waiting Time (Hours)` | number | passenger-hours | Initial plus transfer waiting hours for Daily or a model period. |

The output includes `Daily`, `EA`, `AM`, `MD`, `PM`, and `EV` variants of the
waiting-time columns when those fields are present in the CUBE preprocessing
output.

## Highway geometry audit output

The highway network preprocessor may also write
`tep_metrics/intermediate/Cube_Network_RTPC_QAQC_links_without_geometry.csv`.
This is a
diagnostic file, not a metric output. It identifies highway records that have
traffic attributes but no usable map geometry from CUBE. Those records remain
available to calculations that do not require a location, but they cannot be
assigned to an RTPC or tested against school buffers.
