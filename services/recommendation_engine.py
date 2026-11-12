"""
Activity Recommendation Engine
==============================

Part of the Real-Time Weather Information System.

Given an hourly weather forecast and an outdoor activity, this module:

  * recommends the best time of day to do the activity
    (``RecommendationEngine.recommend_best_time``), and
  * builds a packing / preparation checklist
    (``RecommendationEngine.generate_checklist``).

Supported activities: jogging, football, farming, travelling, picnic
(plus common aliases such as "running", "soccer", "travel", "trip").

Forecast format
---------------
The forecast is a list of hourly entries (or a dict with an "hourly" list).
Each entry is a dict. Key names are flexible; the first one found is used:

    time          : "2026-11-05T06:00", "06:00", a datetime, or an int hour
    temperature   : degrees Celsius          (aliases: temp, temp_c)
    humidity      : percent                  (aliases: humidity_percent)
    wind_speed    : km/h                     (aliases: wind_kph, wind)
    rain_probability : percent 0-100         (aliases: pop, precipitation_probability,
                                              chance_of_rain)
    condition     : text, e.g. "Clear", "Light rain", "Thunderstorm"
                                             (aliases: description, weather, summary)
    uv_index      : optional                 (alias: uv)
    visibility    : km, optional

Open-Meteo's raw response also works: pass the whole JSON (or just its "hourly"
block). Field names temperature_2m, relative_humidity_2m, wind_speed_10m,
precipitation_probability, uv_index, visibility (metres) and weather_code (WMO
numbers) are understood.

Missing values are tolerated: a missing field simply does not affect the score.

Risk assessment
---------------
The risk assessment module is owned by a teammate, so this engine accepts its
output in a flexible way. ``risk_assessment`` can be:

    * a string:   "low" | "moderate" | "high" | "extreme"
                  (also "safe" | "manageable" | "risky" | "avoid")
    * a dict:     {"level": "high", ...}   (aliases: risk_level, overall)
    * an object with a ``.level`` / ``.risk_level`` attribute

It can be passed to the constructor, to either method, or placed in the
forecast dict under the key "risk". The engine ALSO computes its own
per-hour risk so it works standalone. The effective risk of an hour is the
higher of the two:

    low       -> no penalty
    moderate  -> score penalty + warning
    high      -> hour is excluded (not recommended)
    extreme   -> hour is excluded (not recommended)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------
# Risk levels
# --------------------------------------------------------------------------

RISK_ORDER = {"low": 0, "moderate": 1, "high": 2, "extreme": 3}
RISK_NAMES = {v: k for k, v in RISK_ORDER.items()}

# --------------------------------------------------------------------------
# Activity profiles
# --------------------------------------------------------------------------
# temp_ideal / temp_hard are in degrees C, wind in km/h, rain in %.
# hours = (first_hour, last_hour) the activity can sensibly START (24h clock).
# rain_weight scales rain penalties (farming tolerates more rain than a picnic).

ACTIVITY_PROFILES: Dict[str, Dict[str, Any]] = {
    "jogging": {
        "temp_ideal": (16, 27),
        "temp_hard": (5, 34),
        "wind_ideal_max": 20,
        "wind_hard_max": 40,
        "rain_ideal_max": 20,
        "humidity_ideal_max": 75,
        "uv_ideal_max": 6,
        "heat_risk_temp": 32,
        "hours": (5, 20),
        "rain_weight": 1.0,
        "tips": [
            "Warm up for 5 minutes before you start and cool down after.",
            "Run in a safe, well-lit area and tell someone your route.",
            "Drink water before and after your run.",
        ],
    },
    "football": {
        "temp_ideal": (15, 28),
        "temp_hard": (5, 35),
        "wind_ideal_max": 25,
        "wind_hard_max": 45,
        "rain_ideal_max": 25,
        "humidity_ideal_max": 80,
        "uv_ideal_max": 7,
        "heat_risk_temp": 33,
        "hours": (6, 20),
        "rain_weight": 0.8,
        "tips": [
            "Stretch properly to avoid muscle injuries.",
            "Take water breaks every 15-20 minutes.",
            "Wet pitches are slippery: wear studs and avoid hard tackles.",
        ],
    },
    "farming": {
        "temp_ideal": (18, 30),
        "temp_hard": (8, 37),
        "wind_ideal_max": 15,
        "wind_hard_max": 40,
        "rain_ideal_max": 30,
        "humidity_ideal_max": 90,
        "uv_ideal_max": 7,
        "heat_risk_temp": 34,
        "hours": (5, 17),
        "rain_weight": 0.5,
        "tips": [
            "Start early: the morning is cooler and easier on your body.",
            "Avoid spraying chemicals when it is windy or about to rain.",
            "Take shade breaks and drink water regularly.",
        ],
    },
    "travelling": {
        "temp_ideal": (15, 32),
        "temp_hard": (0, 40),
        "wind_ideal_max": 30,
        "wind_hard_max": 55,
        "rain_ideal_max": 30,
        "humidity_ideal_max": 95,
        "uv_ideal_max": 9,
        "heat_risk_temp": 36,
        "hours": (5, 21),
        "rain_weight": 1.0,
        "visibility_min": 4,
        "tips": [
            "Check the vehicle (tyres, fuel, lights) before leaving.",
            "Leave earlier than needed if roads may be wet or busy.",
            "Share your route and expected arrival time with someone.",
        ],
    },
    "picnic": {
        "temp_ideal": (20, 29),
        "temp_hard": (12, 35),
        "wind_ideal_max": 18,
        "wind_hard_max": 35,
        "rain_ideal_max": 10,
        "humidity_ideal_max": 75,
        "uv_ideal_max": 6,
        "heat_risk_temp": 33,
        "hours": (9, 17),
        "rain_weight": 1.3,
        "tips": [
            "Pick a shaded spot and keep food covered.",
            "Keep perishable food in a cooler and eat it within 2 hours.",
            "Carry a bag to take all your rubbish home.",
        ],
    },
}

ACTIVITY_ALIASES = {
    "jog": "jogging", "jogging": "jogging", "run": "jogging", "running": "jogging",
    "football": "football", "soccer": "football", "footballing": "football",
    "farm": "farming", "farming": "farming", "farm work": "farming",
    "agriculture": "farming",
    "travel": "travelling", "travelling": "travelling", "traveling": "travelling",
    "trip": "travelling", "journey": "travelling", "road trip": "travelling",
    "picnic": "picnic", "picnicking": "picnic",
}

SEVERE_KEYWORDS = ("thunder", "storm", "tornado", "hail", "lightning", "cyclone", "squall")
HEAVY_RAIN_KEYWORDS = ("heavy rain", "downpour", "torrential", "violent rain", "flood")
RAIN_KEYWORDS = ("rain", "drizzle", "shower")
DUST_KEYWORDS = ("harmattan", "dust", "haze", "smoke", "fog", "mist")

# Open-Meteo returns numeric WMO weather codes; translate them to text.
WMO_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "fog",
    51: "light drizzle", 53: "drizzle", 55: "dense drizzle",
    56: "freezing drizzle", 57: "freezing drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    66: "freezing rain", 67: "heavy freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "light rain showers", 81: "rain showers", 82: "violent rain showers",
    85: "snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with hail",
}

MIN_RECOMMENDED_SCORE = 50


class RecommendationEngine:
    """Recommends the best time for an outdoor activity and builds checklists."""

    def __init__(self, risk_assessment: Any = None):
        """
        Parameters
        ----------
        risk_assessment:
            Optional default risk assessment (see module docstring) used when
            a method call does not supply its own.
        """
        self.default_risk = risk_assessment

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def supported_activities(self) -> List[str]:
        return sorted(ACTIVITY_PROFILES)

    def recommend_best_time(self, forecast, activity, risk_assessment=None) -> Dict[str, Any]:
        """
        Find the most suitable hour for ``activity`` in the hourly ``forecast``.

        Returns a dict:
            activity        normalised activity name
            best_time       label of the best hour (None if nothing is suitable)
            score           0-100 suitability score of that hour
            rating          "Excellent" | "Good" | "Fair" | "Poor"
            risk_level      effective risk of the chosen hour (or overall risk
                            if nothing is suitable)
            reasons         why the hour is good
            warnings        things to watch out for
            alternatives    up to 3 next-best hours: [{"time", "score", "rating"}]
            advice          activity-specific tips
            message         one-line human readable summary
        """
        name, profile = self._resolve_activity(activity)
        hours = self._normalise_forecast(forecast)
        external = self._external_risk(forecast, risk_assessment)

        scored = [self._score_hour(h, profile, external) for h in hours]
        in_window = [s for s in scored if self._in_window(s["hour"], profile)]
        candidates = [s for s in in_window if not s["excluded"]]
        candidates.sort(key=lambda s: (-s["score"], s["index"]))

        result: Dict[str, Any] = {
            "activity": name,
            "best_time": None,
            "score": 0,
            "rating": "Poor",
            "risk_level": RISK_NAMES[external],
            "reasons": [],
            "warnings": [],
            "alternatives": [],
            "advice": list(profile["tips"]),
        }

        if not hours:
            result["message"] = "No forecast data available, so no time can be recommended."
            return result

        if not in_window:
            result["message"] = (
                f"The forecast has no hours inside the sensible window for {name}."
            )
            return result

        best = candidates[0] if candidates else None
        if best is None or best["score"] < MIN_RECOMMENDED_SCORE:
            worst_risk = max(s["risk"] for s in in_window)
            result["risk_level"] = RISK_NAMES[max(worst_risk, external)]
            result["warnings"] = self._collect_warnings(in_window)
            if external >= RISK_ORDER["high"]:
                result["warnings"].insert(
                    0, f"The overall risk assessment is {RISK_NAMES[external]}."
                )
            result["message"] = (
                f"No safe or comfortable time for {name} in this forecast. "
                f"Consider postponing."
            )
            return result

        result["best_time"] = best["label"]
        result["score"] = best["score"]
        result["rating"] = self._rating(best["score"])
        result["risk_level"] = RISK_NAMES[best["risk"]]
        result["reasons"] = best["reasons"]
        result["warnings"] = best["warnings"]
        result["alternatives"] = [
            {"time": s["label"], "score": s["score"], "rating": self._rating(s["score"])}
            for s in candidates[1:4]
            if s["score"] >= MIN_RECOMMENDED_SCORE
        ]
        result["message"] = (
            f"Best time for {name}: {best['label']} "
            f"({result['rating']}, score {best['score']}/100)."
        )
        return result

    def generate_checklist(self, forecast, activity, risk_assessment=None) -> Dict[str, Any]:
        """
        Build a packing checklist for ``activity`` based on the forecast.

        The weather used is the forecast hours inside the activity's sensible
        window (so a jogger's checklist is not driven by 2 a.m. weather).

        Returns a dict:
            activity       normalised activity name
            essentials     items always needed for the activity
            weather_gear   items driven by the expected weather
            safety         safety items / precautions (includes risk-driven ones)
            risk_level     overall risk level used
            summary        short description of the expected weather
        """
        name, profile = self._resolve_activity(activity)
        hours = self._normalise_forecast(forecast)
        
        external_source = risk_assessment

        if external_source is None and isinstance(forecast, dict):
            external_source = (
                forecast.get("risk")
                or forecast.get("risk_assessment")
            )

        if external_source is None:
            external_source = self.default_risk

        external = self._risk_to_int(external_source)
        has_external_assessment = external_source is not None

        window = [h for h in hours if self._in_window(h["hour"], profile)] or hours

        essentials = list(self._essentials(name))
        weather_gear: List[str] = []
        safety: List[str] = list(self._safety(name))

        stats = self._weather_stats(window)

        hour_risk = max(
            (self._hour_risk(h, profile)[0] for h in window),
            default=0
        )

        # Use the official risk analyzer's result when available.
        # Otherwise, fall back to the recommendation engine's own assessment.
        overall = external if has_external_assessment else hour_risk

        if stats["max_rain"] is not None and stats["max_rain"] >= 30:
            weather_gear += ["Umbrella or raincoat", "Waterproof bag or plastic cover for phone and documents"]
            if name in ("jogging", "football"):
                weather_gear.append("Spare dry clothes and towel")
            if name == "football":
                weather_gear.append("Studded boots for a wet pitch")
            if name == "farming":
                weather_gear.append("Rubber boots")
            if name == "picnic":
                weather_gear.append("Waterproof ground sheet and a canopy or tarp")
            if name == "travelling":
                weather_gear.append("Windscreen wipers and tyres in good condition")
        if stats["max_temp"] is not None and stats["max_temp"] >= 29:
            weather_gear += ["Extra water (at least 1-2 litres per person)", "Cap or wide-brim hat"]
            weather_gear.append("Light, breathable clothing")
        if stats["max_temp"] is not None and stats["max_temp"] >= 32:
            safety.append("Take regular rest in the shade and watch for signs of heat exhaustion (dizziness, headache, nausea).")
            weather_gear.append("Electrolyte drink or oral rehydration salts")
        if stats["max_uv"] is not None and stats["max_uv"] >= 6:
            weather_gear += ["Sunscreen (SPF 30+)", "Sunglasses"]
        if stats["min_temp"] is not None and stats["min_temp"] <= 18:
            weather_gear.append("Light jacket or sweater for the cooler hours")
        if stats["min_temp"] is not None and stats["min_temp"] <= 10:
            weather_gear += ["Warm layers", "Gloves"]
        if stats["max_wind"] is not None and stats["max_wind"] >= 25:
            weather_gear.append("Windbreaker")
            if name == "picnic":
                weather_gear.append("Weights or clips to hold down blankets and food covers")
            if name == "farming":
                safety.append("Do not spray chemicals in strong wind.")
        if stats["max_humidity"] is not None and stats["max_humidity"] >= 85:
            weather_gear.append("Quick-dry clothing and a small towel")
        if stats["min_visibility"] is not None and stats["min_visibility"] < 5:
            safety.append("Visibility may be low: use headlights/reflective gear and move slowly.")
            weather_gear.append("Reflective vest or bright clothing")
        if stats["dusty"]:
            weather_gear.append("Face mask or scarf (dust/harmattan)")
            weather_gear.append("Lip balm and moisturiser for dry air")

        if overall >= RISK_ORDER["moderate"]:
            safety.append("Check the latest weather update before you leave and again during the activity.")
        if overall >= RISK_ORDER["high"]:
            safety.append("Risk is HIGH: strongly consider postponing or choosing a safer time.")
            safety.append("Have a plan to take shelter quickly and keep your phone charged.")
        if stats["severe"]:
            safety.append("Thunderstorm/severe weather is possible: do not stay in open fields or under tall trees.")

        return {
            "activity": name,
            "essentials": self._dedupe(essentials),
            "weather_gear": self._dedupe(weather_gear),
            "safety": self._dedupe(safety),
            "risk_level": RISK_NAMES[overall],
            "summary": self._summary(stats),
        }

    @staticmethod
    def format_checklist(checklist: Dict[str, Any]) -> str:
        """Render a checklist dict as plain text (handy for the GUI or console)."""
        lines = [f"Checklist for {checklist['activity']} (risk: {checklist['risk_level']})"]
        if checklist.get("summary"):
            lines.append(checklist["summary"])
        for title, key in (("Essentials", "essentials"),
                           ("Weather gear", "weather_gear"),
                           ("Safety", "safety")):
            items = checklist.get(key) or []
            if items:
                lines.append(f"\n{title}:")
                lines += [f"  [ ] {item}" for item in items]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Activity helpers
    # ------------------------------------------------------------------

    def _resolve_activity(self, activity):
        if not isinstance(activity, str) or not activity.strip():
            raise ValueError(
                f"Activity must be a non-empty string. Supported: {', '.join(self.supported_activities)}"
            )
        key = ACTIVITY_ALIASES.get(activity.strip().lower())
        if key is None:
            raise ValueError(
                f"Unsupported activity '{activity}'. Supported: {', '.join(self.supported_activities)}"
            )
        return key, ACTIVITY_PROFILES[key]

    @staticmethod
    def _essentials(name):
        return {
            "jogging": ["Running shoes", "Light sportswear", "Water bottle", "Phone with ID", "Reflective item or light if it is dark"],
            "football": ["Football", "Boots/cleats", "Shin guards", "Jersey and shorts", "Water bottle", "Towel", "First-aid kit"],
            "farming": ["Hoe/cutlass or required tools", "Gloves", "Farm boots", "Water", "Snacks", "Hat", "First-aid kit"],
            "travelling": ["ID and travel documents", "Phone and power bank", "Cash and cards", "Water and snacks", "Small first-aid kit"],
            "picnic": ["Blanket or mat", "Food and drinks", "Cooler with ice packs", "Plates, cups and cutlery", "Refuse bags", "Hand sanitiser or wipes"],
        }[name]

    @staticmethod
    def _safety(name):
        return {
            "jogging": ["Warm up before and stretch after."],
            "football": ["Warm up and stretch before playing."],
            "farming": ["Wear protective footwear to avoid cuts and snake bites."],
            "travelling": ["Check vehicle condition and fuel before leaving."],
            "picnic": ["Keep food covered and perishables cold."],
        }[name]

    @staticmethod
    def _in_window(hour, profile):
        if hour is None:
            return True  # unknown hour: do not discard
        start, end = profile["hours"]
        return start <= hour <= end

    # ------------------------------------------------------------------
    # Forecast normalisation
    # ------------------------------------------------------------------

    
    def _normalise_forecast(self, forecast) -> List[Dict[str, Any]]:
        if forecast is None:
            return []

        entries = forecast

        if isinstance(forecast, dict):
            # Handle the format returned by our WeatherClient.
            if isinstance(forecast.get("forecast_times"), list):
                times = forecast.get("forecast_times", [])
                temperatures = forecast.get("hourly_temperatures", [])
                winds = forecast.get("hourly_wind_speeds", [])
                humidity = forecast.get("hourly_humidity", [])
                weather_codes = forecast.get("hourly_weather_codes", [])
                rain_probability = forecast.get(
                    "hourly_precipitation_probability", []
                )

                entries = []

                for i, time_value in enumerate(times):
                    entries.append({
                        "time": time_value,
                        "temperature_2m": (
                            temperatures[i] if i < len(temperatures) else None
                        ),
                        "wind_speed_10m": (
                            winds[i] if i < len(winds) else None
                        ),
                        "relative_humidity_2m": (
                            humidity[i] if i < len(humidity) else None
                        ),
                        "weather_code": (
                            weather_codes[i] if i < len(weather_codes) else None
                        ),
                        "precipitation_probability": (
                            rain_probability[i]
                            if i < len(rain_probability) else None
                        ),
                    })

            elif isinstance(forecast.get("time"), (list, tuple)):
                entries = self._columns_to_rows(forecast)

            else:
                entries = (
                    forecast.get("hourly")
                    or forecast.get("hours")
                    or forecast.get("forecast")
                    or []
                )

        if isinstance(entries, dict):
            entries = self._columns_to_rows(entries)

        if not isinstance(entries, (list, tuple)):
            raise TypeError(
                "Forecast must be a list of hourly dictionaries "
                "or a dictionary containing hourly forecast data."
            )

        hours = []

        for i, e in enumerate(entries):
            if not isinstance(e, dict):
                continue

            t = self._first(
                e, "time", "datetime", "dt_txt", "hour", "timestamp"
            )

            rain = self._number(self._first(
                e,
                "rain_probability",
                "pop",
                "precipitation_probability",
                "chance_of_rain",
                "rain_chance",
                "precip_prob"
            ))

            if rain is not None and 0 < rain <= 1:
                rain *= 100

            cond = self._first(
                e, "condition", "description", "weather",
                "summary", "main", "weather_code", "weathercode"
            )

            if isinstance(cond, dict):
                cond = cond.get("description") or cond.get("main")

            if isinstance(cond, (int, float)) and not isinstance(cond, bool):
                cond = WMO_CODES.get(int(cond), "")

            vis = self._number(
                self._first(e, "visibility", "visibility_km")
            )

            if vis is not None and vis > 100:
                vis /= 1000

            hours.append({
                "index": i,
                "label": self._label(t, i),
                "hour": self._parse_hour(t),
                "temp": self._number(self._first(
                    e, "temperature", "temp", "temp_c", "temperature_2m"
                )),
                "humidity": self._number(self._first(
                    e, "humidity", "humidity_percent",
                    "relative_humidity_2m"
                )),
                "wind": self._number(self._first(
                    e, "wind_speed", "wind_kph", "wind",
                    "wind_speed_10m"
                )),
                "rain": rain,
                "condition": str(cond).lower() if cond else "",
                "uv": self._number(self._first(e, "uv_index", "uv")),
                "visibility": vis,
            })

        return hours


    @staticmethod
    def _columns_to_rows(cols):
        """{"time": [..], "temperature_2m": [..]} -> [{"time":.., "temperature_2m":..}, ...]"""
        times = cols.get("time")
        if not isinstance(times, (list, tuple)):
            return []
        return [{k: v[i] for k, v in cols.items()
                 if isinstance(v, (list, tuple)) and i < len(v)}
                for i in range(len(times))]

    @staticmethod
    def _first(d, *keys):
        for k in keys:
            if k in d and d[k] is not None:
                return d[k]
        return None

    @staticmethod
    def _number(v):
        if v is None or isinstance(v, bool):
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_hour(t):
        if t is None:
            return None
        if isinstance(t, datetime):
            return t.hour
        if isinstance(t, (int, float)) and not isinstance(t, bool):
            return int(t) % 24
        if isinstance(t, str):
            s = t.strip()
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00")).hour
            except ValueError:
                pass
            for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I %p", "%I%p", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(s.upper(), fmt).hour
                except ValueError:
                    continue
            if s.isdigit():
                return int(s) % 24
        return None

    @staticmethod
    def _label(t, index):
        if t is None:
            return f"Hour {index}"
        if isinstance(t, datetime):
            return t.strftime("%Y-%m-%d %H:%M")
        if isinstance(t, (int, float)) and not isinstance(t, bool):
            return f"{int(t) % 24:02d}:00"
        return str(t)

    # ------------------------------------------------------------------
    # Risk handling
    # ------------------------------------------------------------------

    def _external_risk(self, forecast, risk_assessment) -> int:
        source = risk_assessment
        if source is None and isinstance(forecast, dict):
            source = forecast.get("risk") or forecast.get("risk_assessment")
        if source is None:
            source = self.default_risk
        return self._risk_to_int(source)

    @staticmethod
    def _risk_to_int(source) -> int:
        if source is None:
            return 0
        if isinstance(source, bool):
            return 0
        if isinstance(source, (int, float)):
            return max(0, min(3, int(source)))
        if isinstance(source, dict):
            source = (source.get("level") or source.get("risk_level")
                      or source.get("overall") or source.get("risk"))
        elif not isinstance(source, str):
            source = getattr(source, "level", None) or getattr(source, "risk_level", None)
        if isinstance(source, str):
            s = source.strip().lower()
            if s in RISK_ORDER:
                return RISK_ORDER[s]
            aliases = {"medium": "moderate", "mild": "low", "safe": "low", "minimal": "low",
                       "manageable": "moderate", "risky": "high", "avoid": "extreme",
                       "should be avoided": "extreme", "should avoid": "extreme",
                       "severe": "extreme", "critical": "extreme", "dangerous": "high"}
            return RISK_ORDER.get(aliases.get(s, "low"), 0)
        return 0

    def _hour_risk(self, h, profile):
        """Return (risk_int, list_of_reasons) computed from a single hour."""
        level = 0
        notes: List[str] = []

        def bump(to, note):
            nonlocal level
            level = max(level, to)
            notes.append(note)

        cond = h["condition"]
        if any(k in cond for k in SEVERE_KEYWORDS):
            bump(3, "Thunderstorm or severe weather expected")
        elif any(k in cond for k in HEAVY_RAIN_KEYWORDS):
            bump(2, "Heavy rain expected")

        w, t, r, uv, hum, vis = h["wind"], h["temp"], h["rain"], h["uv"], h["humidity"], h["visibility"]
        if w is not None:
            if w >= 60:
                bump(3, f"Dangerous wind ({w:.0f} km/h)")
            elif w >= profile["wind_hard_max"] + 5:
                bump(2, f"Very strong wind ({w:.0f} km/h)")
            elif w >= profile["wind_hard_max"] - 10:
                bump(1, f"Strong wind ({w:.0f} km/h)")
        if t is not None:
            if t >= 40 or t <= -10:
                bump(3, f"Extreme temperature ({t:.0f}°C)")
            elif t >= profile["heat_risk_temp"] + 3:
                bump(2, f"Dangerous heat ({t:.0f}°C)")
            elif t >= profile["heat_risk_temp"]:
                bump(1, f"Very hot ({t:.0f}°C)")
            elif t <= 3:
                bump(2, f"Freezing conditions ({t:.0f}°C)")
            elif t <= 8:
                bump(1, f"Cold ({t:.0f}°C)")
            if hum is not None and t >= 30 and hum >= 85 and level < 1:
                bump(1, "Hot and very humid: high heat stress")
        if r is not None:
            if r >= 90:
                bump(2, f"Rain almost certain ({r:.0f}%)")
            elif r >= 60:
                bump(1, f"Likely rain ({r:.0f}%)")
        if uv is not None:
            if uv >= 11:
                bump(2, f"Extreme UV index ({uv:.0f})")
            elif uv >= 8:
                bump(1, f"Very high UV index ({uv:.0f})")
        if vis is not None:
            if vis < 1:
                bump(2, f"Very poor visibility ({vis:g} km)")
            elif vis < profile.get("visibility_min", 2):
                bump(1, f"Reduced visibility ({vis:g} km)")
        return level, notes

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def _score_hour(self, h, profile, external_risk) -> Dict[str, Any]:
        score = 100.0
        reasons: List[str] = []
        warnings: List[str] = []

        # --- temperature ---
        t = h["temp"]
        if t is not None:
            lo, hi = profile["temp_ideal"]
            hard_lo, hard_hi = profile["temp_hard"]
            if lo <= t <= hi:
                reasons.append(f"Comfortable temperature ({t:.0f}°C)")
            else:
                gap = (lo - t) if t < lo else (t - hi)
                score -= min(40, gap * 4)
                warnings.append(f"{'Cool' if t < lo else 'Hot'} for this activity ({t:.0f}°C)")
                if t < hard_lo or t > hard_hi:
                    score -= 25

        # --- wind ---
        w = h["wind"]
        if w is not None:
            if w <= profile["wind_ideal_max"]:
                reasons.append(f"Light wind ({w:.0f} km/h)")
            else:
                over = w - profile["wind_ideal_max"]
                score -= min(35, over * 1.5)
                warnings.append(f"Windy ({w:.0f} km/h)")
                if w > profile["wind_hard_max"]:
                    score -= 20

        # --- rain ---
        r = h["rain"]
        weight = profile["rain_weight"]
        cond = h["condition"]
        if r is not None:
            if r <= profile["rain_ideal_max"]:
                reasons.append(f"Low chance of rain ({r:.0f}%)")
            else:
                over = r - profile["rain_ideal_max"]
                score -= min(45, over * 0.7 * weight)
                warnings.append(f"Chance of rain ({r:.0f}%)")
        if any(k in cond for k in HEAVY_RAIN_KEYWORDS):
            score -= 30 * weight
        elif any(k in cond for k in RAIN_KEYWORDS) and (r is None or r <= profile["rain_ideal_max"]):
            score -= 15 * weight
            warnings.append("Rain in the forecast")
        if any(k in cond for k in DUST_KEYWORDS):
            score -= 8
            warnings.append("Dust, haze or fog reduces air quality or visibility")

        # --- humidity ---
        hum = h["humidity"]
        if hum is not None and hum > profile["humidity_ideal_max"]:
            score -= min(15, (hum - profile["humidity_ideal_max"]) * 0.6)
            warnings.append(f"High humidity ({hum:.0f}%)")

        # --- UV ---
        uv = h["uv"]
        if uv is not None and uv > profile["uv_ideal_max"]:
            score -= min(15, (uv - profile["uv_ideal_max"]) * 4)
            warnings.append(f"Strong UV ({uv:.0f}): sun protection needed")

        # --- visibility (travelling mostly) ---
        vis = h["visibility"]
        if vis is not None and vis < profile.get("visibility_min", 2):
            score -= 20
            warnings.append(f"Low visibility ({vis:g} km)")

        # --- clear sky bonus ---
        if cond and any(k in cond for k in ("clear", "sunny", "fair", "few clouds", "partly")) \
                and not warnings:
            reasons.append("Pleasant, dry sky")

        # --- risk assessment ---
        own_risk, risk_notes = self._hour_risk(h, profile)
        risk = max(own_risk, external_risk)
        excluded = False
        if risk >= RISK_ORDER["high"]:
            excluded = True
            score = min(score, 20)
            if external_risk >= RISK_ORDER["high"]:
                warnings.append(f"Risk assessment is {RISK_NAMES[external_risk]}")
            warnings += risk_notes
        elif risk == RISK_ORDER["moderate"]:
            score -= 15
            if external_risk == RISK_ORDER["moderate"] and not risk_notes:
                warnings.append("Risk assessment is moderate: stay alert to weather updates")
            warnings += risk_notes
        else:
            reasons.append("Low weather risk")

        score = max(0, min(100, round(score)))
        return {
            "index": h["index"], "label": h["label"], "hour": h["hour"],
            "score": score, "risk": risk, "excluded": excluded,
            "reasons": self._dedupe(reasons), "warnings": self._dedupe(warnings),
        }

    @staticmethod
    def _rating(score):
        if score >= 80:
            return "Excellent"
        if score >= 65:
            return "Good"
        if score >= MIN_RECOMMENDED_SCORE:
            return "Fair"
        return "Poor"

    def _collect_warnings(self, scored):
        warnings: List[str] = []
        for s in scored:
            for w in s["warnings"]:
                if w not in warnings:
                    warnings.append(w)
        return warnings[:6]

    # ------------------------------------------------------------------
    # Checklist helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _weather_stats(hours):
        def vals(key):
            return [h[key] for h in hours if h[key] is not None]

        temps, winds, rains = vals("temp"), vals("wind"), vals("rain")
        hums, uvs, viss = vals("humidity"), vals("uv"), vals("visibility")
        conds = " ".join(h["condition"] for h in hours)
        return {
            "min_temp": min(temps) if temps else None,
            "max_temp": max(temps) if temps else None,
            "max_wind": max(winds) if winds else None,
            "max_rain": max(rains) if rains else None,
            "max_humidity": max(hums) if hums else None,
            "max_uv": max(uvs) if uvs else None,
            "min_visibility": min(viss) if viss else None,
            "severe": any(k in conds for k in SEVERE_KEYWORDS),
            "dusty": any(k in conds for k in ("harmattan", "dust", "haze")),
        }

    @staticmethod
    def _summary(stats):
        parts = []
        if stats["min_temp"] is not None:
            if stats["min_temp"] == stats["max_temp"]:
                parts.append(f"{stats['min_temp']:.0f}°C")
            else:
                parts.append(f"{stats['min_temp']:.0f}-{stats['max_temp']:.0f}°C")
        if stats["max_rain"] is not None:
            parts.append(f"up to {stats['max_rain']:.0f}% rain chance")
        if stats["max_wind"] is not None:
            parts.append(f"wind up to {stats['max_wind']:.0f} km/h")
        return "Expected: " + ", ".join(parts) + "." if parts else ""

    @staticmethod
    def _dedupe(items):
        seen, out = set(), []
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out
