"""Rule-based weather risk assessment for outdoor activities.

The assessment is intentionally deterministic. Gemini or any other AI service
may explain the result, but must not decide or change the risk classification.

Expected forecast fields (matching the project contract):
    location, temperature, feels_like, humidity, wind_speed, precipitation,
    weather_code, forecast_times, hourly_temperatures,
    hourly_precipitation, hourly_wind_speeds

Open-Meteo wind speeds are expected in km/h and precipitation in mm.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
from typing import Any


@dataclass(frozen=True)
class _ActivityProfile:
    """Small set of adjustments for activities with different exposure levels."""

    heat_adjustment: float = 0.0
    cold_adjustment: float = 0.0
    rain_multiplier: float = 1.0
    wind_multiplier: float = 1.0
    fog_sensitive: bool = False


class ActivityRiskAnalyzer:
    """Assess outdoor activity risk using predefined weather rules."""

    # Risk score bands. A score is a heuristic, not a measured probability.
    SAFE_MAX = 19
    MANAGEABLE_MAX = 39
    RISKY_MAX = 64

    _ACTIVITY_ALIASES = {
        "jogging": "jogging",
        "jog": "jogging",
        "running": "jogging",
        "run": "jogging",
        "football": "football",
        "soccer": "football",
        "farming": "farming",
        "farm work": "farming",
        "gardening": "farming",
        "travel": "travel",
        "travelling": "travel",
        "traveling": "travel",
        "driving": "travel",
        "picnic": "picnic",
        "walking": "walking",
        "hiking": "hiking",
        "cycling": "cycling",
        "biking": "cycling",
    }

    _PROFILES = {
        # Strenuous activities need more conservative heat/cold thresholds.
        "jogging": _ActivityProfile(heat_adjustment=-2, cold_adjustment=-2, rain_multiplier=1.1, wind_multiplier=1.0),
        "football": _ActivityProfile(heat_adjustment=-2, cold_adjustment=-2, rain_multiplier=1.15, wind_multiplier=1.05),
        "hiking": _ActivityProfile(heat_adjustment=-2, cold_adjustment=-2, rain_multiplier=1.15, wind_multiplier=1.1),
        "cycling": _ActivityProfile(heat_adjustment=-1, cold_adjustment=-2, rain_multiplier=1.1, wind_multiplier=1.2),
        "farming": _ActivityProfile(heat_adjustment=-2, cold_adjustment=-1, rain_multiplier=1.0, wind_multiplier=1.0),
        "picnic": _ActivityProfile(heat_adjustment=1, cold_adjustment=1, rain_multiplier=1.3, wind_multiplier=1.0),
        "walking": _ActivityProfile(heat_adjustment=0, cold_adjustment=0, rain_multiplier=1.0, wind_multiplier=1.0),
        # Travel is less affected by temperature, but visibility and wind matter.
        "travel": _ActivityProfile(heat_adjustment=3, cold_adjustment=2, rain_multiplier=0.9, wind_multiplier=1.15, fog_sensitive=True),
    }

    # WMO weather codes that indicate thunderstorms, hail, freezing rain,
    # heavy snow, or very heavy showers. These trigger an AVOID classification.
    _SEVERE_WEATHER_CODES = {65, 67, 75, 82, 95, 96, 99}
    _THUNDERSTORM_CODES = {95, 96, 99}
    _FREEZING_OR_HAIL_CODES = {66, 67, 77, 96, 99}

    def assess_risk(self, forecast: Any, activity: str) -> dict[str, Any]:
        """Return a consistent risk result for ``activity`` and ``forecast``.

        The returned dictionary always contains ``level``, ``score``,
        ``reasons`` and ``warnings``. The score ranges from 0 (lowest concern)
        to 100 (highest concern). Hourly values, when present, are checked over
        the first six forecast entries so near-term hazards are not ignored.

        Args:
            forecast: Project Forecast object or a mapping containing the
                agreed forecast fields.
            activity: Activity name, for example ``"jogging"`` or ``"picnic"``.

        Returns:
            A dictionary whose ``level`` is SAFE, MANAGEABLE, RISKY, or AVOID.
        """
        if not isinstance(activity, str) or not activity.strip():
            raise ValueError("activity must be a non-empty string")

        activity_key = self._normalise_activity(activity)
        profile = self._PROFILES.get(activity_key, _ActivityProfile())
        reasons: list[str] = []
        warnings: list[str] = []
        score = 0.0
        critical_hazard = False

        temperature = self._number(self._read(forecast, "temperature"))
        feels_like = self._number(self._read(forecast, "feels_like"))
        humidity = self._number(self._read(forecast, "humidity"))
        wind_speed = self._number(self._read(forecast, "wind_speed"))
        precipitation = self._number(self._read(forecast, "precipitation"))
        weather_code = self._integer(self._read(forecast, "weather_code"))

        hourly_temperatures = self._hourly_values(forecast, "hourly_temperatures")
        hourly_precipitation = self._hourly_values(forecast, "hourly_precipitation")
        hourly_wind_speeds = self._hourly_values(forecast, "hourly_wind_speeds")

        # Use the most adverse near-term hourly value when hourly data exists.
        temperature_values = hourly_temperatures[:6]
        if feels_like is not None:
            effective_temperature = feels_like
        elif temperature is not None:
            effective_temperature = temperature
        elif temperature_values:
            effective_temperature = max(temperature_values)
        else:
            effective_temperature = None

        rainfall_values = hourly_precipitation[:6]
        if precipitation is not None:
            rainfall_values.append(precipitation)
        wind_values = hourly_wind_speeds[:6]
        if wind_speed is not None:
            wind_values.append(wind_speed)
        near_term_rain = max(rainfall_values) if rainfall_values else None
        near_term_wind = max(wind_values) if wind_values else None

        available_measurements = sum(
            value is not None
            for value in (effective_temperature, humidity, near_term_rain, near_term_wind, weather_code)
        )
        if available_measurements == 0:
            return {
                "level": "MANAGEABLE",
                "score": 25,
                "reasons": ["There is not enough weather data to make a reliable activity assessment."],
                "warnings": ["Check the weather connection and try again before going outdoors."],
            }

        # Temperature and apparent-temperature rules, in degrees Celsius.
        if effective_temperature is not None:
            heat_value = effective_temperature - profile.heat_adjustment
            cold_value = effective_temperature + profile.cold_adjustment
            if heat_value >= 42:
                score += 48
                critical_hazard = True
                reasons.append(f"Extreme heat is expected (feels-like/air temperature about {effective_temperature:.1f}°C).")
                warnings.append("Avoid strenuous outdoor exposure in extreme heat.")
            elif heat_value >= 38:
                score += 35
                reasons.append(f"Very high heat is expected (about {effective_temperature:.1f}°C), increasing heat-stress risk.")
                warnings.append("Reduce exposure, take breaks in shade and drink water.")
            elif heat_value >= 35:
                score += 25
                reasons.append(f"High temperatures (about {effective_temperature:.1f}°C) may make the activity strenuous.")
                warnings.append("Stay hydrated and avoid the hottest part of the day.")
            elif heat_value >= 32:
                score += 13
                reasons.append(f"Warm conditions (about {effective_temperature:.1f}°C) may cause discomfort during activity.")
                warnings.append("Take regular breaks, especially during strenuous activity.")

            if cold_value <= -5:
                score += 30
                reasons.append(f"Very cold conditions are expected (about {effective_temperature:.1f}°C).")
                warnings.append("Use appropriate cold-weather clothing and watch for slippery surfaces.")
            elif cold_value <= 0:
                score += 22
                reasons.append(f"Freezing conditions are expected (about {effective_temperature:.1f}°C).")
                warnings.append("Dress warmly and take care on potentially icy surfaces.")
            elif cold_value <= 5:
                score += 12
                reasons.append(f"Cold conditions (about {effective_temperature:.1f}°C) may affect comfort and performance.")
                warnings.append("Wear suitable layers for the conditions.")

        # Rainfall is mm per hour for Open-Meteo precipitation fields.
        if near_term_rain is not None:
            rain_score = 0
            if near_term_rain >= 20:
                rain_score = 48
                critical_hazard = True
                reasons.append(f"Very heavy rainfall is indicated (up to {near_term_rain:.1f} mm in an hour).")
                warnings.append("Avoid outdoor activity during very heavy rainfall; flooding and poor visibility may occur.")
            elif near_term_rain >= 10:
                rain_score = 32
                reasons.append(f"Heavy rainfall is expected (up to {near_term_rain:.1f} mm in an hour).")
                warnings.append("Wet surfaces and reduced visibility may make the activity unsafe.")
            elif near_term_rain >= 5:
                rain_score = 23
                reasons.append(f"Moderate to heavy rainfall is expected (up to {near_term_rain:.1f} mm in an hour).")
                warnings.append("Consider postponing or moving the activity to a covered location.")
            elif near_term_rain >= 1:
                rain_score = 12
                reasons.append(f"Rain is expected (up to {near_term_rain:.1f} mm in an hour).")
                warnings.append("Expect wet conditions and possible slippery surfaces.")
            elif near_term_rain >= 0.2:
                rain_score = 5
                reasons.append("Light rain or drizzle may affect the activity.")
                warnings.append("Consider suitable waterproof clothing or an alternative location.")
            score += rain_score * profile.rain_multiplier

        # Wind speeds are km/h, matching the Open-Meteo API field used by the project.
        if near_term_wind is not None:
            adjusted_wind_score = 0
            if near_term_wind >= 75:
                adjusted_wind_score = 48
                critical_hazard = True
                reasons.append(f"Very strong winds are expected (up to {near_term_wind:.1f} km/h).")
                warnings.append("Avoid exposed outdoor areas and stay away from trees or unstable structures.")
            elif near_term_wind >= 55:
                adjusted_wind_score = 32
                reasons.append(f"Strong winds are expected (up to {near_term_wind:.1f} km/h).")
                warnings.append("Strong gusts can affect balance, equipment and travel safety.")
            elif near_term_wind >= 40:
                adjusted_wind_score = 22
                reasons.append(f"Wind speeds may be uncomfortable or disruptive (up to {near_term_wind:.1f} km/h).")
                warnings.append("Use caution in exposed areas, particularly when handling equipment.")
            elif near_term_wind >= 30:
                adjusted_wind_score = 12
                reasons.append(f"Breezy conditions are expected (up to {near_term_wind:.1f} km/h).")
                warnings.append("Secure loose items and be aware of changing wind conditions.")
            elif near_term_wind >= 20:
                adjusted_wind_score = 5
                reasons.append("Moderate winds may affect comfort for some outdoor activities.")
            score += adjusted_wind_score * profile.wind_multiplier

        # High humidity adds to heat stress when temperatures are already warm.
        if humidity is not None and humidity >= 85 and effective_temperature is not None and effective_temperature >= 30:
            score += 10
            reasons.append(f"High humidity ({humidity:.0f}%) may make warm conditions feel more oppressive.")
            warnings.append("Take more frequent rest breaks and monitor for signs of heat stress.")
        elif humidity is not None and humidity >= 90:
            score += 3
            reasons.append(f"Humidity is high ({humidity:.0f}%), which may reduce comfort.")

        # WMO code assessment. Thunderstorms and selected severe conditions
        # force AVOID even if the numerical score from other factors is low.
        if weather_code in self._SEVERE_WEATHER_CODES:
            score += 40 if weather_code in self._THUNDERSTORM_CODES else 28
            critical_hazard = True
            if weather_code in self._THUNDERSTORM_CODES:
                reasons.append("Thunderstorm conditions are indicated by the weather forecast.")
                warnings.append("Do not start or continue outdoor activity during a thunderstorm. Move to a safe shelter.")
            elif weather_code in self._FREEZING_OR_HAIL_CODES:
                reasons.append("The forecast indicates freezing precipitation, hail, or severe wintry conditions.")
                warnings.append("Avoid exposed outdoor activity until conditions improve.")
            else:
                reasons.append("The forecast indicates very heavy rain or severe showers.")
                warnings.append("Avoid outdoor activity until the severe weather has passed.")
        elif weather_code in {63, 66, 73, 81}:
            score += 13
            reasons.append("The weather code indicates rain, freezing precipitation, snow, or heavy showers.")
            warnings.append("Check local conditions because surfaces may be slippery or visibility may be reduced.")
        elif weather_code in {51, 53, 55, 61, 62, 71, 72, 80}:
            score += 6
            reasons.append("The forecast indicates drizzle, rain, snow, or showers.")
        elif weather_code in {45, 48}:
            fog_points = 10 if profile.fog_sensitive else 5
            score += fog_points
            reasons.append("Fog is indicated, which may reduce visibility.")
            if profile.fog_sensitive:
                warnings.append("Poor visibility may make travel unsafe. Check road and transport advisories.")

        # Mention if the result is based on incomplete forecast information.
        if available_measurements < 3:
            warnings.append("Some weather measurements are unavailable, so this assessment may be incomplete.")

        score = max(0, min(100, int(round(score))))
        if critical_hazard:
            score = max(score, 65)
        level = self._classify_score(score)

        if not reasons:
            reasons.append("No significant weather hazards were found in the available forecast data.")
        if level == "SAFE":
            reasons.append("The available weather conditions appear suitable for this activity.")
        elif level == "MANAGEABLE":
            reasons.append("The activity may proceed with sensible precautions.")
        elif level == "RISKY":
            reasons.append("Weather conditions could make this activity unsafe; consider changing the time or location.")
        else:
            reasons.append("The weather conditions are unsuitable for this activity at the time assessed.")

        # Preserve message order while removing accidental duplicates.
        return {
            "level": level,
            "score": score,
            "reasons": list(dict.fromkeys(reasons)),
            "warnings": list(dict.fromkeys(warnings)),
        }

    @classmethod
    def _classify_score(cls, score: int) -> str:
        if score <= cls.SAFE_MAX:
            return "SAFE"
        if score <= cls.MANAGEABLE_MAX:
            return "MANAGEABLE"
        if score <= cls.RISKY_MAX:
            return "RISKY"
        return "AVOID"

    @classmethod
    def _normalise_activity(cls, activity: str) -> str:
        cleaned = " ".join(activity.strip().lower().replace("_", " ").replace("-", " ").split())
        return cls._ACTIVITY_ALIASES.get(cleaned, cleaned)

    @staticmethod
    def _read(source: Any, key: str) -> Any:
        """Read a forecast field from either a mapping or an object."""
        if isinstance(source, Mapping):
            value = source.get(key)
            if value is not None:
                return value
            # Also accept the nested shape returned by raw Open-Meteo responses.
            if key in {"temperature", "feels_like", "humidity", "wind_speed", "precipitation", "weather_code"}:
                current = source.get("current")
                if isinstance(current, Mapping):
                    aliases = {
                        "temperature": "temperature_2m",
                        "feels_like": "apparent_temperature",
                        "humidity": "relative_humidity_2m",
                        "wind_speed": "wind_speed_10m",
                        "precipitation": "precipitation",
                        "weather_code": "weather_code",
                    }
                    return current.get(aliases[key])
            return value
        return getattr(source, key, None)

    @classmethod
    def _hourly_values(cls, forecast: Any, key: str) -> list[float]:
        value = cls._read(forecast, key)
        if value is None and isinstance(forecast, Mapping):
            hourly = forecast.get("hourly")
            if isinstance(hourly, Mapping):
                aliases = {
                    "hourly_temperatures": "temperature_2m",
                    "hourly_precipitation": "precipitation",
                    "hourly_wind_speeds": "wind_speed_10m",
                }
                value = hourly.get(aliases.get(key, key))
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            return []
        result: list[float] = []
        for item in value:
            number = cls._number(item)
            if number is not None:
                result.append(number)
        return result

    @staticmethod
    def _number(value: Any) -> float | None:
        if isinstance(value, bool) or value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    @classmethod
    def _integer(cls, value: Any) -> int | None:
        number = cls._number(value)
        if number is None:
            return None
        return int(number)
