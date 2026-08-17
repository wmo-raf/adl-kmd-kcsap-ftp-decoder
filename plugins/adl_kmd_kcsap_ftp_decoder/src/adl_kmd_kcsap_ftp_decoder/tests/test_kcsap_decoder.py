"""
Tests for the KCSAP / KMD AWS decoder, driven by the two real sample files in
``fixtures/`` plus synthetic edge cases. No database is needed.
"""

import os
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

from adl_ftp_plugin.registries import ftp_decoder_registry
from adl_kmd_kcsap_ftp_decoder.decoders import KcsapDecoder
from adl_kmd_kcsap_ftp_decoder.decoders.kcsap import FIELD_MAP, N_FIELDS, VARIABLES

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
UTC = ZoneInfo("UTC")

RECORD_1414 = (
    "KMD,001,202408241414, 1,13.39, 18.4, 62.0, 0.0,  80.6, 826.4,/////,//////,   0,"
    "////,////,////,////,////,////,/////,/////,/////,/////,/////,/////, 2.47, 3.88,114.0,"
    "14:13:03,120.6,100.1,137.3"
)
RECORD_1415 = (
    "KMD,001,202408241415, 1,13.37, 18.4, 62.0, 0.0,  78.8, 826.4,/////,//////,   0,"
    "////,////,////,////,////,////,/////,/////,/////,/////,/////,/////, 3.13, 4.73,145.0,"
    "14:14:12,124.6, 92.9,140.3"
)


def fixture(name):
    return os.path.join(FIXTURES, name)


class KcsapDecoderTestBase(SimpleTestCase):
    def setUp(self):
        self.decoder = KcsapDecoder()
        self._temp_files = []

    def tearDown(self):
        for path in self._temp_files:
            try:
                os.unlink(path)
            except OSError:
                pass

    def write_temp(self, content):
        fd, path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        self._temp_files.append(path)
        return path


class SampleFileTests(KcsapDecoderTestBase):
    def test_decodes_1414_sample(self):
        data = self.decoder.decode(fixture("KMD_001_202408241414.csv"))
        values = data["values"]
        self.assertEqual(len(values), 1)
        record = values[0]

        obs_time = record["observation_time"]
        self.assertEqual(obs_time, datetime(2024, 8, 24, 14, 14, tzinfo=UTC))
        self.assertIsNotNone(obs_time.utcoffset())
        self.assertEqual(obs_time.utcoffset().total_seconds(), 0)

        self.assertEqual(record["air_temperature_2m"], 18.4)
        self.assertEqual(record["relative_humidity_2m"], 62.0)
        self.assertEqual(record["precipitation_1m"], 0.0)
        self.assertEqual(record["total_radiation_1m"], 80.6)
        self.assertEqual(record["air_pressure_2m"], 826.4)
        self.assertEqual(record["leaf_wetness_2m"], 0.0)
        self.assertEqual(record["wind_speed_2m"], 2.47)
        self.assertEqual(record["wind_gust_speed_2m"], 3.88)
        self.assertEqual(record["wind_gust_direction_2m"], 114.0)
        self.assertEqual(record["wind_direction_avg_2m"], 120.6)
        self.assertEqual(record["wind_direction_min_2m"], 100.1)
        self.assertEqual(record["wind_direction_max_2m"], 137.3)

        # slash-runs are missing values
        self.assertIsNone(record["evaporation_1m"])
        self.assertIsNone(record["soil_temperature_0.05m"])
        self.assertIsNone(record["soil_moisture_1.2m"])

        # gust time is discarded; the record carries exactly the declared variables
        expected_keys = {"observation_time"} | {name for _, name in FIELD_MAP}
        self.assertEqual(set(record.keys()), expected_keys)
        self.assertNotIn("14:13:03", [str(v) for v in record.values()])

    def test_decodes_1415_sample(self):
        data = self.decoder.decode(fixture("KMD_001_202408241415.csv"))
        self.assertEqual(len(data["values"]), 1)
        record = data["values"][0]
        self.assertEqual(record["observation_time"], datetime(2024, 8, 24, 14, 15, tzinfo=UTC))
        self.assertEqual(record["wind_speed_2m"], 3.13)
        self.assertEqual(record["wind_gust_speed_2m"], 4.73)
        self.assertEqual(record["wind_gust_direction_2m"], 145.0)
        self.assertEqual(record["total_radiation_1m"], 78.8)


class EdgeCaseTests(KcsapDecoderTestBase):
    def test_glued_qkmd_line_yields_two_records(self):
        glued = RECORD_1414 + "?" + RECORD_1415
        path = self.write_temp("KMD,001,202408241414\n" + glued + "\n")
        values = self.decoder.decode(path)["values"]
        self.assertEqual(len(values), 2)
        self.assertEqual(values[0]["observation_time"], datetime(2024, 8, 24, 14, 14, tzinfo=UTC))
        self.assertEqual(values[1]["observation_time"], datetime(2024, 8, 24, 14, 15, tzinfo=UTC))
        self.assertEqual(values[0]["wind_speed_2m"], 2.47)
        self.assertEqual(values[1]["wind_speed_2m"], 3.13)

    def test_one_line_file_returns_empty(self):
        path = self.write_temp(RECORD_1414 + "\n")
        self.assertEqual(self.decoder.decode(path), {"values": []})

    def test_three_line_file_returns_empty(self):
        path = self.write_temp("KMD,001,202408241414\n" + RECORD_1414 + "\n" + RECORD_1415 + "\n")
        self.assertEqual(self.decoder.decode(path), {"values": []})

    def test_wrong_field_count_is_skipped(self):
        truncated = ",".join(RECORD_1414.split(",")[:20])
        path = self.write_temp("KMD,001,202408241414\n" + truncated + "\n")
        self.assertEqual(self.decoder.decode(path), {"values": []})

    def test_bad_timestamp_is_skipped(self):
        fields = RECORD_1414.split(",")
        fields[2] = "2024-08-24"
        path = self.write_temp("KMD,001,202408241414\n" + ",".join(fields) + "\n")
        self.assertEqual(self.decoder.decode(path), {"values": []})

    def test_non_numeric_value_becomes_none(self):
        fields = RECORD_1414.split(",")
        fields[5] = "abc"
        path = self.write_temp("KMD,001,202408241414\n" + ",".join(fields) + "\n")
        record = self.decoder.decode(path)["values"][0]
        self.assertIsNone(record["air_temperature_2m"])
        self.assertEqual(record["relative_humidity_2m"], 62.0)


class VariablesContractTests(SimpleTestCase):
    def test_variables_cover_the_expected_layout(self):
        indices = [v["index"] for v in VARIABLES]
        self.assertEqual(len(indices), 25)
        self.assertEqual(indices, sorted(indices))
        self.assertTrue(all(0 <= i < N_FIELDS for i in indices))
        self.assertNotIn(28, indices)  # gust time
        self.assertEqual(len({v["name"] for v in VARIABLES}), len(VARIABLES))

    def test_get_variables_is_field_map_minus_index(self):
        variables = KcsapDecoder().get_variables()
        self.assertEqual([v["name"] for v in variables], [name for _, name in FIELD_MAP])
        for variable in variables:
            self.assertNotIn("index", variable)
            for key in ("name", "unit", "label", "adl_unit"):
                self.assertIn(key, variable)

        by_name = {v["name"]: v for v in variables}
        for name in ("wind_speed_2m", "wind_gust_speed_2m"):
            self.assertEqual(by_name[name]["unit"], "knot")
            self.assertEqual(by_name[name]["adl_unit"], "m/s")
        self.assertEqual(by_name["leaf_wetness_2m"]["unit"], "1")
        self.assertEqual(by_name["wind_direction_avg_2m"]["aggregation_method"], "circular")
        self.assertEqual(by_name["precipitation_1m"]["custom_unit_context"], "precipitation")

    def test_declared_units_are_valid_pint_symbols(self):
        from adl.core.units import units

        for variable in VARIABLES:
            for key in ("unit", "adl_unit"):
                units(variable[key])  # raises if undefined

    def test_registered_in_ftp_decoder_registry(self):
        self.assertIsInstance(ftp_decoder_registry.get("kcsap"), KcsapDecoder)
