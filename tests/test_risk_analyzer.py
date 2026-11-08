import unittest

from services.risk_analyzer import ActivityRiskAnalyzer


class FakeForecast:
    def __init__(self, **values):
        self.__dict__.update(values)


class TestActivityRiskAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = ActivityRiskAnalyzer()

    def forecast(self, **overrides):
        values = {
            "location": "Minna",
            "temperature": 25,
            "feels_like": 26,
            "humidity": 55,
            "wind_speed": 10,
            "precipitation": 0,
            "weather_code": 1,
            "forecast_times": [],
            "hourly_temperatures": [25, 26, 27, 26, 25, 24],
            "hourly_precipitation": [0, 0, 0, 0, 0, 0],
            "hourly_wind_speeds": [8, 10, 12, 10, 9, 8],
        }
        values.update(overrides)
        return FakeForecast(**values)

    def test_safe_conditions(self):
        result = self.analyzer.assess_risk(self.forecast(), "jogging")
        self.assertEqual(result["level"], "SAFE")
        self.assertEqual(result["score"], 0)
        self.assertTrue(result["reasons"])
        self.assertEqual(result["warnings"], [])

    def test_hot_conditions_increase_risk(self):
        result = self.analyzer.assess_risk(
            self.forecast(temperature=37, feels_like=38, hourly_temperatures=[37] * 6),
            "jogging",
        )
        self.assertIn(result["level"], {"MANAGEABLE", "RISKY", "AVOID"})
        self.assertGreater(result["score"], 0)
        self.assertTrue(any("heat" in reason.lower() or "temperature" in reason.lower() for reason in result["reasons"]))

    def test_thunderstorm_forces_avoid(self):
        result = self.analyzer.assess_risk(self.forecast(weather_code=95), "picnic")
        self.assertEqual(result["level"], "AVOID")
        self.assertGreaterEqual(result["score"], 65)
        self.assertTrue(result["warnings"])

    def test_very_heavy_rain_forces_avoid(self):
        result = self.analyzer.assess_risk(
            self.forecast(precipitation=22, hourly_precipitation=[22, 18, 8]),
            "football",
        )
        self.assertEqual(result["level"], "AVOID")

    def test_very_strong_wind_forces_avoid(self):
        result = self.analyzer.assess_risk(
            self.forecast(wind_speed=78, hourly_wind_speeds=[78, 60, 50]),
            "cycling",
        )
        self.assertEqual(result["level"], "AVOID")

    def test_rain_can_make_picnic_riskier_than_travel(self):
        wet_forecast = self.forecast(precipitation=6, hourly_precipitation=[6, 4, 1])
        picnic = self.analyzer.assess_risk(wet_forecast, "picnic")
        travel = self.analyzer.assess_risk(wet_forecast, "travelling")
        self.assertGreaterEqual(picnic["score"], travel["score"])

    def test_accepts_dictionary_forecast(self):
        result = self.analyzer.assess_risk(
            {
                "temperature": 24,
                "feels_like": 25,
                "humidity": 60,
                "wind_speed": 12,
                "precipitation": 0,
                "weather_code": 2,
            },
            "walking",
        )
        self.assertEqual(result["level"], "SAFE")

    def test_accepts_raw_open_meteo_hourly_shape(self):
        result = self.analyzer.assess_risk(
            {
                "current": {
                    "temperature_2m": 25,
                    "apparent_temperature": 26,
                    "relative_humidity_2m": 50,
                    "wind_speed_10m": 8,
                    "precipitation": 0,
                    "weather_code": 1,
                },
                "hourly": {
                    "temperature_2m": [25, 26, 27],
                    "precipitation": [0, 0, 0],
                    "wind_speed_10m": [8, 9, 10],
                },
            },
            "jogging",
        )
        self.assertEqual(result["level"], "SAFE")

    def test_missing_weather_data_does_not_claim_safe(self):
        result = self.analyzer.assess_risk({}, "picnic")
        self.assertEqual(result["level"], "MANAGEABLE")
        self.assertTrue(result["warnings"])

    def test_invalid_activity_raises_clear_error(self):
        with self.assertRaises(ValueError):
            self.analyzer.assess_risk(self.forecast(), "   ")

    def test_result_has_consistent_keys_and_valid_score(self):
        result = self.analyzer.assess_risk(self.forecast(), "unknown activity")
        self.assertEqual(set(result), {"level", "score", "reasons", "warnings"})
        self.assertIn(result["level"], {"SAFE", "MANAGEABLE", "RISKY", "AVOID"})
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)
        self.assertIsInstance(result["reasons"], list)
        self.assertIsInstance(result["warnings"], list)


if __name__ == "__main__":
    unittest.main()
