"""
Decoder for Kenya Meteorological Department (KMD) KCSAP automatic weather
station minute files, delivered over FTP.

File format
-----------
One file per station per minute, named ``KMD_<stationID>_<YYYYMMDDHHMM>.csv``,
containing exactly two lines:

1. a short preview line: ``KMD,<stationID>,<YYYYMMDDHHMM>``
2. the real record: 32 comma-separated fields, e.g. ::

    KMD,001,202408241414, 1,13.39, 18.4, 62.0, 0.0,  80.6, 826.4,/////,
    //////,   0,////,...,2.47, 3.88,114.0,14:13:03,120.6,100.1,137.3

- Timestamps are UTC, minute resolution.
- Any field consisting of slashes (``////``, ``/////`` ...) is the feed's
  missing-value marker.
- Occasionally the feed glues two records into one line, joined by a literal
  ``?KMD`` marker; the decoder splits those back into two records.
- Wind speeds are reported in **knots**; ADL converts to m/s through the
  variable mapping's file unit.
- Field 29 (index 28) is an ``HH:MM:SS`` clock reading for when the minute's
  peak gust occurred. It is deliberately **not** emitted: gust speed and
  direction are period statistics of the minute ending at the record's
  timestamp and are stored at that timestamp, like every other field.
"""

import logging
from adl_ftp_plugin.registries import FTPDecoder
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

UTC = ZoneInfo("UTC")
N_FIELDS = 32
OBS_TIME_INDEX = 2  # 0-based position of the YYYYMMDDHHMM field

# Fixed raw-field layout for KMD/KCSAP AWS loggers. Checked against all 157
# stations in KMD's kcsap_pars.csv -- every one shares this exact
# column-index -> variable mapping, so it is hardcoded here rather than looked
# up per station. If a station is ever deployed with a different sensor
# package, this decoder will need to become station-aware instead.
#
# This list is the single source of truth: it drives both the record layout
# (index -> name) and ``get_variables()``, which lets the ADL FTP plugin
# pre-populate a connection's variable mappings.
#
#   index     0-based position in the 32-field raw record
#   name      key emitted in each decoded record (the "file variable name")
#   unit      pint symbol of the value as it appears in the file
#   label     human name used if ADL has to create a DataParameter for it
#   adl_unit  pint symbol for that auto-created DataParameter
VARIABLES = [
    {"index": 5, "name": "air_temperature_2m", "unit": "°C", "label": "Air Temperature 2m", "adl_unit": "°C"},
    {"index": 6, "name": "relative_humidity_2m", "unit": "%", "label": "Relative Humidity 2m", "adl_unit": "%"},
    {"index": 7, "name": "precipitation_1m", "unit": "mm", "label": "Precipitation 1m", "adl_unit": "mm",
     "custom_unit_context": "precipitation"},
    {"index": 8, "name": "total_radiation_1m", "unit": "W/m^2", "label": "Total Radiation 1m", "adl_unit": "W/m^2"},
    {"index": 9, "name": "air_pressure_2m", "unit": "hPa", "label": "Air Pressure 2m", "adl_unit": "hPa"},
    {"index": 11, "name": "evaporation_1m", "unit": "mm", "label": "Evaporation 1m", "adl_unit": "mm"},
    {"index": 12, "name": "leaf_wetness_2m", "unit": "1", "label": "Leaf Wetness 2m", "adl_unit": "1"},
    {"index": 13, "name": "soil_temperature_0.05m", "unit": "°C", "label": "Soil Temperature 0.05m", "adl_unit": "°C"},
    {"index": 14, "name": "soil_temperature_0.1m", "unit": "°C", "label": "Soil Temperature 0.1m", "adl_unit": "°C"},
    {"index": 15, "name": "soil_temperature_0.2m", "unit": "°C", "label": "Soil Temperature 0.2m", "adl_unit": "°C"},
    {"index": 16, "name": "soil_temperature_0.5m", "unit": "°C", "label": "Soil Temperature 0.5m", "adl_unit": "°C"},
    {"index": 17, "name": "soil_temperature_1m", "unit": "°C", "label": "Soil Temperature 1m", "adl_unit": "°C"},
    {"index": 18, "name": "soil_temperature_1.2m", "unit": "°C", "label": "Soil Temperature 1.2m", "adl_unit": "°C"},
    {"index": 19, "name": "soil_moisture_0.05m", "unit": "%", "label": "Soil Moisture 0.05m", "adl_unit": "%"},
    {"index": 20, "name": "soil_moisture_0.1m", "unit": "%", "label": "Soil Moisture 0.1m", "adl_unit": "%"},
    {"index": 21, "name": "soil_moisture_0.2m", "unit": "%", "label": "Soil Moisture 0.2m", "adl_unit": "%"},
    {"index": 22, "name": "soil_moisture_0.5m", "unit": "%", "label": "Soil Moisture 0.5m", "adl_unit": "%"},
    {"index": 23, "name": "soil_moisture_1m", "unit": "%", "label": "Soil Moisture 1m", "adl_unit": "%"},
    {"index": 24, "name": "soil_moisture_1.2m", "unit": "%", "label": "Soil Moisture 1.2m", "adl_unit": "%"},
    {"index": 25, "name": "wind_speed_2m", "unit": "knot", "label": "Wind Speed 2m", "adl_unit": "m/s"},
    {"index": 26, "name": "wind_gust_speed_2m", "unit": "knot", "label": "Wind Gust Speed 2m", "adl_unit": "m/s"},
    {"index": 27, "name": "wind_gust_direction_2m", "unit": "degree", "label": "Wind Gust Direction 2m",
     "adl_unit": "degree", "aggregation_method": "circular"},
    # index 28 (HH:MM:SS time of the peak gust) is discarded -- see module docstring
    {"index": 29, "name": "wind_direction_avg_2m", "unit": "degree", "label": "Wind Direction Avg 2m",
     "adl_unit": "degree", "aggregation_method": "circular"},
    {"index": 30, "name": "wind_direction_min_2m", "unit": "degree", "label": "Wind Direction Min 2m",
     "adl_unit": "degree", "aggregation_method": "circular"},
    {"index": 31, "name": "wind_direction_max_2m", "unit": "degree", "label": "Wind Direction Max 2m",
     "adl_unit": "degree", "aggregation_method": "circular"},
]

# (0-based index in the 32-field raw record, output field name)
FIELD_MAP = [(v["index"], v["name"]) for v in VARIABLES]


def _clean_field(v):
    """A field starting with '/' (any run length: '////', '/////', ...)
    is this feed's missing-value marker."""
    if v is None:
        return None
    v = v.strip()
    if v == "" or v.startswith("/"):
        return None
    return v


def _split_record(fields_str):
    """Split one comma-separated raw record string into 32 cleaned fields."""
    fields = [_clean_field(v) for v in fields_str.split(",")]
    if len(fields) != N_FIELDS:
        return None
    return fields


def _to_float(raw_val):
    if raw_val is None:
        return None
    try:
        return float(raw_val)
    except ValueError:
        return None


def _record_from_fields(fields):
    """
    Turn one cleaned 32-field raw record into a list holding a single output
    dict at the reported observation_time, with every VARIABLES entry as a
    float (or None when the field is missing/unparseable).

    Returns [] if the timestamp field is missing or malformed.

    observation_time is an aware UTC datetime. ADL's Plugin base class accepts
    aware datetimes as-is and localises them to the station link's configured
    timezone itself (see make_record_timezone_aware in adl.core.date_utils).
    """
    ts_raw = fields[OBS_TIME_INDEX]
    if ts_raw is None:
        return []
    try:
        obs_time_utc = datetime.strptime(ts_raw, "%Y%m%d%H%M").replace(tzinfo=UTC)
    except ValueError:
        return []
    
    record = {"observation_time": obs_time_utc}
    for idx, name in FIELD_MAP:
        record[name] = _to_float(fields[idx])
    
    return [record]


class KcsapDecoder(FTPDecoder):
    """
    Decoder for KCSAP/KMD automatic weather station minute files.

    Each raw file (KMD_<stationID>_<YYYYMMDDHHMM>.csv) has exactly 2 lines:
    a short preview line, then the real 32-field comma-separated record.
    Occasionally the feed glues two observations into one line, joined by
    a literal "?KMD" marker -- this decoder splits those back into two
    separate records.
    """
    
    type = "kcsap"
    compat_type = "kcsap"
    display_name = "KCSAP / KMD AWS"
    
    def get_variables(self):
        return [{k: v for k, v in variable.items() if k != "index"} for variable in VARIABLES]
    
    def decode(self, file_path):
        data = {"values": []}
        
        with open(file_path, "r", encoding="UTF-8", errors="replace") as f:
            lines = f.read().splitlines()
        
        if len(lines) != 2:
            logger.warning(f"{file_path}: expected 2 lines, found {len(lines)}. Skipping.")
            return data
        
        line = lines[1]
        kmd_count = line.count("KMD")
        has_qkmd = "?KMD" in line
        
        raw_records = []
        if kmd_count == 2 and has_qkmd:
            part1, part2 = line.split("?KMD", 1)
            raw_records.append(part1.replace("?", ""))
            raw_records.append("KMD" + part2)
        else:
            raw_records.append(line)
        
        for raw in raw_records:
            fields = _split_record(raw)
            if fields is None:
                logger.warning(f"{file_path}: wrong field count, skipping record: {raw[:50]}...")
                continue
            data["values"].extend(_record_from_fields(fields))
        
        return data
