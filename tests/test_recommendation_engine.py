"""Tests for services/recommendation_engine.py  (run: python -m unittest -v)"""

import os
import sys
import unittest
from datetime import datetime

# Works in three layouts (and on Pydroid, where __file__ is not reliable):
#   1) project/services/recommendation_engine.py + project/tests/this_file.py
#   2) both files in the SAME folder
#   3) run from the project folder
try:
    _here = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _here = os.getcwd()
for _p in (_here, os.path.dirname(_here), os.getcwd()):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from services.recommendation_engine import RecommendationEngine  # noqa: E402
except ImportError:
    from recommendation_engine import RecommendationEngine  # noqa: E402


def hour(h, temp=24, wind=10, rain=5, hum=60, cond="Clear", **extra):
    d = {"time": f"2026-11-05T{h:02d}:00", "temperature": temp, "wind_speed": wind,
         "rain_probability": rain, "humidity": hum, "condition": cond}
    d.update(extra)
    return d


def day_forecast():
    """Hot afternoon, stormy evening, pleasant early morning."""
    return [
        hour(5, temp=22, rain=5),
        hour(6, temp=23, rain=5),
        hour(7, temp=25, rain=5),
        hour(10, temp=29, rain=10),
        hour(13, temp=35, rain=10, uv_index=10),
        hour(16, temp=31, rain=40, cond="Light rain"),
        hour(18, temp=26, rain=90, wind=50, cond="Thunderstorm"),
    ]


class TestRecommendBestTime(unittest.TestCase):
    def setUp(self):
        self.engine = RecommendationEngine()

    def test_jogging_picks_cool_calm_morning(self):
        r = self.engine.recommend_best_time(day_forecast(), "jogging")
        self.assertIn(r["best_time"], ("2026-11-05T06:00", "2026-11-05T07:00", "2026-11-05T05:00"))
        self.assertGreaterEqual(r["score"], 80)
        self.assertEqual(r["risk_level"], "low")
        self.assertTrue(r["advice"])

    def test_storm_hour_never_recommended(self):
        r = self.engine.recommend_best_time(day_forecast(), "football")
        self.assertNotEqual(r["best_time"], "2026-11-05T18:00")
        for alt in r["alternatives"]:
            self.assertNotEqual(alt["time"], "2026-11-05T18:00")

    def test_all_activities_work(self):
        for act in ("jogging", "football", "farming", "travelling", "picnic"):
            r = self.engine.recommend_best_time(day_forecast(), act)
            self.assertEqual(r["activity"], act)
            self.assertIsNotNone(r["best_time"], act)

    def test_aliases(self):
        self.assertEqual(self.engine.recommend_best_time(day_forecast(), "Running")["activity"], "jogging")
        self.assertEqual(self.engine.recommend_best_time(day_forecast(), "soccer")["activity"], "football")
        self.assertEqual(self.engine.recommend_best_time(day_forecast(), "TRAVEL")["activity"], "travelling")

    def test_picnic_window_excludes_early_morning(self):
        r = self.engine.recommend_best_time(day_forecast(), "picnic")
        self.assertNotIn(r["best_time"], ("2026-11-05T05:00", "2026-11-05T06:00", "2026-11-05T07:00"))

    def test_farming_prefers_morning_over_hot_afternoon(self):
        r = self.engine.recommend_best_time(day_forecast(), "farming")
        self.assertLess(int(r["best_time"][11:13]), 12)

    def test_all_bad_weather_returns_none(self):
        bad = [hour(h, temp=24, wind=55, rain=95, cond="Thunderstorm") for h in range(6, 18)]
        r = self.engine.recommend_best_time(bad, "jogging")
        self.assertIsNone(r["best_time"])
        self.assertIn("postpon", r["message"].lower())
        self.assertIn(r["risk_level"], ("high", "extreme"))

    def test_extreme_heat_blocks_jogging(self):
        hot = [hour(h, temp=39, hum=40) for h in range(6, 18)]
        r = self.engine.recommend_best_time(hot, "jogging")
        self.assertIsNone(r["best_time"])

    # ---- risk assessment ----
    def test_external_high_risk_blocks_everything(self):
        # Calm forecast, so the external assessment is the only risk source.
        calm = [hour(6), hour(7), hour(8)]
        r = self.engine.recommend_best_time(calm, "jogging", risk_assessment="high")
        self.assertIsNone(r["best_time"])
        self.assertEqual(r["risk_level"], "high")
        # Same with a stormy day: the worst hour (extreme) is what gets reported.
        r = self.engine.recommend_best_time(day_forecast(), "jogging", risk_assessment="high")
        self.assertIsNone(r["best_time"])
        self.assertEqual(r["risk_level"], "extreme")

    def test_external_risk_dict_and_object(self):
        r = self.engine.recommend_best_time(day_forecast(), "jogging", risk_assessment={"level": "extreme"})
        self.assertIsNone(r["best_time"])

        class Risk:
            level = "high"

        r = self.engine.recommend_best_time(day_forecast(), "jogging", risk_assessment=Risk())
        self.assertIsNone(r["best_time"])

    def test_moderate_risk_lowers_score_but_still_recommends(self):
        base = self.engine.recommend_best_time(day_forecast(), "jogging")
        mod = self.engine.recommend_best_time(day_forecast(), "jogging", risk_assessment="moderate")
        self.assertIsNotNone(mod["best_time"])
        self.assertLess(mod["score"], base["score"])
        self.assertEqual(mod["risk_level"], "moderate")

    def test_risk_inside_forecast_dict_and_constructor(self):
        fc = {"hourly": day_forecast(), "risk": {"risk_level": "high"}}
        self.assertIsNone(self.engine.recommend_best_time(fc, "jogging")["best_time"])
        eng = RecommendationEngine(risk_assessment="extreme")
        self.assertIsNone(eng.recommend_best_time(day_forecast(), "jogging")["best_time"])

    def test_method_risk_overrides_nothing_lower(self):
        eng = RecommendationEngine(risk_assessment="low")
        r = eng.recommend_best_time(day_forecast(), "jogging", risk_assessment="high")
        self.assertIsNone(r["best_time"])

    # ---- input handling ----
    def test_alternatives_sorted_and_limited(self):
        r = self.engine.recommend_best_time(day_forecast(), "jogging")
        self.assertLessEqual(len(r["alternatives"]), 3)
        scores = [a["score"] for a in r["alternatives"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(all(s <= r["score"] for s in scores))

    def test_flexible_keys_and_time_formats(self):
        fc = [
            {"time": datetime(2026, 11, 5, 6), "temp": 22, "wind": 8, "pop": 0.05, "description": "clear sky"},
            {"time": 7, "temp_c": 23, "wind_kph": 8, "chance_of_rain": 5, "weather": "sunny"},
            {"time": "08:00", "temp": 24},
        ]
        r = self.engine.recommend_best_time(fc, "jogging")
        self.assertIsNotNone(r["best_time"])

    def test_missing_fields_do_not_crash(self):
        r = self.engine.recommend_best_time([{"time": "09:00"}], "picnic")
        self.assertIsNotNone(r["best_time"])

    def test_empty_and_none_forecast(self):
        for fc in ([], None, {"hourly": []}):
            r = self.engine.recommend_best_time(fc, "jogging")
            self.assertIsNone(r["best_time"])
            self.assertIn("No forecast", r["message"])

    def test_bad_activity_raises(self):
        for bad in ("skydiving", "", None, 5):
            with self.assertRaises(ValueError):
                self.engine.recommend_best_time(day_forecast(), bad)

    def test_bad_forecast_type_raises(self):
        with self.assertRaises(TypeError):
            self.engine.recommend_best_time("not a forecast", "jogging")

    def test_non_dict_entries_ignored(self):
        fc = ["junk", None, hour(7)]
        self.assertEqual(self.engine.recommend_best_time(fc, "jogging")["best_time"], "2026-11-05T07:00")

    def test_forecast_not_mutated(self):
        fc = day_forecast()
        import copy
        snapshot = copy.deepcopy(fc)
        self.engine.recommend_best_time(fc, "jogging")
        self.engine.generate_checklist(fc, "jogging")
        self.assertEqual(fc, snapshot)

    def test_low_visibility_hurts_travelling(self):
        fc = [hour(6, visibility=0.5, cond="Fog"), hour(9, visibility=10)]
        r = self.engine.recommend_best_time(fc, "travelling")
        self.assertEqual(r["best_time"], "2026-11-05T09:00")


class TestBriefVocabularyAndOpenMeteo(unittest.TestCase):
    def setUp(self):
        self.engine = RecommendationEngine()

    def test_safe_manageable_risky_avoid_words(self):
        calm = [hour(6), hour(7)]
        self.assertIsNotNone(self.engine.recommend_best_time(calm, "jogging", risk_assessment="safe")["best_time"])
        r = self.engine.recommend_best_time(calm, "jogging", risk_assessment="manageable")
        self.assertEqual(r["risk_level"], "moderate")
        self.assertIsNone(self.engine.recommend_best_time(calm, "jogging", risk_assessment="risky")["best_time"])
        self.assertIsNone(self.engine.recommend_best_time(calm, "jogging", risk_assessment={"level": "avoid"})["best_time"])

    def open_meteo(self):
        return {"latitude": 9.0, "hourly": {
            "time": ["2026-11-05T06:00", "2026-11-05T09:00", "2026-11-05T15:00"],
            "temperature_2m": [22, 27, 31],
            "relative_humidity_2m": [70, 60, 80],
            "precipitation_probability": [5, 10, 95],
            "wind_speed_10m": [8, 12, 50],
            "uv_index": [1, 5, 9],
            "visibility": [24140, 24140, 800],
            "weather_code": [0, 1, 95],
        }}

    def test_open_meteo_raw_response(self):
        r = self.engine.recommend_best_time(self.open_meteo(), "jogging")
        self.assertIn(r["best_time"], ("2026-11-05T06:00", "2026-11-05T09:00"))
        self.assertNotIn("2026-11-05T15:00", [a["time"] for a in r["alternatives"]])

    def test_open_meteo_hourly_block_only_and_storm_code(self):
        r = self.engine.recommend_best_time(self.open_meteo()["hourly"], "football")
        self.assertIsNotNone(r["best_time"])
        cl = self.engine.generate_checklist(self.open_meteo(), "football")
        self.assertIn("thunderstorm", " ".join(cl["safety"]).lower())

    def test_open_meteo_metres_visibility(self):
        fc = {"hourly": {"time": ["2026-11-05T06:00", "2026-11-05T09:00"],
                         "visibility": [300, 20000], "weather_code": [45, 0]}}
        self.assertEqual(self.engine.recommend_best_time(fc, "travelling")["best_time"], "2026-11-05T09:00")


class TestGenerateChecklist(unittest.TestCase):
    def setUp(self):
        self.engine = RecommendationEngine()

    def flat(self, cl):
        return " | ".join(cl["essentials"] + cl["weather_gear"] + cl["safety"]).lower()

    def test_structure(self):
        cl = self.engine.generate_checklist(day_forecast(), "jogging")
        for key in ("activity", "essentials", "weather_gear", "safety", "risk_level", "summary"):
            self.assertIn(key, cl)
        self.assertIn("running shoes", self.flat(cl))

    def test_rain_adds_umbrella(self):
        fc = [hour(9, rain=70, cond="Rain")]
        self.assertIn("umbrella", self.flat(self.engine.generate_checklist(fc, "picnic")))

    def test_dry_weather_no_umbrella(self):
        fc = [hour(9, rain=5)]
        self.assertNotIn("umbrella", self.flat(self.engine.generate_checklist(fc, "picnic")))

    def test_heat_adds_water_sunscreen(self):
        fc = [hour(12, temp=34, uv_index=9)]
        text = self.flat(self.engine.generate_checklist(fc, "football"))
        self.assertIn("water", text)
        self.assertIn("sunscreen", text)

    def test_cold_adds_jacket(self):
        fc = [hour(7, temp=12)]
        self.assertIn("jacket", self.flat(self.engine.generate_checklist(fc, "jogging")))

    def test_activity_specific_items(self):
        fc = [hour(9, rain=60, cond="Rain")]
        self.assertIn("studded boots", self.flat(self.engine.generate_checklist(fc, "football")))
        self.assertIn("rubber boots", self.flat(self.engine.generate_checklist(fc, "farming")))
        self.assertIn("documents", self.flat(self.engine.generate_checklist(fc, "travelling")))

    def test_harmattan_adds_mask(self):
        fc = [hour(9, cond="Harmattan haze")]
        self.assertIn("mask", self.flat(self.engine.generate_checklist(fc, "jogging")))

    def test_risk_adds_safety_advice(self):
        cl = self.engine.generate_checklist([hour(9)], "jogging", risk_assessment="high")
        self.assertEqual(cl["risk_level"], "high")
        self.assertIn("postponing", self.flat(cl))

    def test_storm_adds_shelter_warning(self):
        fc = [hour(9, cond="Thunderstorm", rain=90)]
        self.assertIn("thunderstorm", self.flat(self.engine.generate_checklist(fc, "football")))

    def test_no_duplicates(self):
        cl = self.engine.generate_checklist(day_forecast(), "farming")
        for key in ("essentials", "weather_gear", "safety"):
            self.assertEqual(len(cl[key]), len(set(cl[key])))

    def test_all_activities_and_empty_forecast(self):
        for act in ("jogging", "football", "farming", "travelling", "picnic"):
            self.assertTrue(self.engine.generate_checklist([], act)["essentials"])

    def test_night_hours_ignored_for_checklist(self):
        fc = [hour(2, temp=8), hour(9, temp=26)]
        cl = self.engine.generate_checklist(fc, "picnic")
        self.assertNotIn("warm layers", self.flat(cl))

    def test_bad_activity_raises(self):
        with self.assertRaises(ValueError):
            self.engine.generate_checklist(day_forecast(), "skydiving")

    def test_format_checklist(self):
        text = RecommendationEngine.format_checklist(self.engine.generate_checklist(day_forecast(), "jogging"))
        self.assertIn("[ ]", text)
        self.assertIn("Essentials", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
