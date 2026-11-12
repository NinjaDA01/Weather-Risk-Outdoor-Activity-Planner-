"""Open-Meteo location lookup and weather forecast service.

The public interface follows the team's technical guide:
    WeatherClient.get_coordinates(location)
    WeatherClient.get_weather(location)

``get_weather`` returns a plain dictionary using the agreed Forecast field
names. This keeps the service independent of the Forecast class being built
by Member 3, while remaining compatible with modules that read the shared
field names as dictionary keys or object attributes.

Units are normalised to Celsius, kilometres per hour and millimetres.
The hourly lists are index-aligned: item N in every list describes
``forecast_times[N]``.

This module uses only Python's standard library. No API key is needed for
Open-Meteo's non-commercial API access.
"""

from __future__ import annotations

import json
import math
import socket
from typing import Any, Dict, List, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "WeatherRiskOutdoorActivityPlanner/1.0"


class WeatherClientError(Exception):
    """Base exception for errors raised by WeatherClient."""


class InvalidLocationError(WeatherClientError, ValueError):
    """Raised when the location input is empty or invalid."""


class LocationNotFoundError(WeatherClientError):
    """Raised when Open-Meteo cannot find the requested location."""


class WeatherNetworkError(WeatherClientError):
    """Raised when a request cannot reach Open-Meteo or times out."""


class WeatherAPIError(WeatherClientError):
    """Raised when Open-Meteo returns an HTTP or API-level error."""


class WeatherDataError(WeatherClientError):
    """Raised when the API response is missing or contains invalid data."""


class WeatherClient:
    """Retrieve location coordinates and hourly weather data from Open-Meteo.

    Args:
        timeout: Maximum time in seconds to wait for each API request.
        forecast_days: Number of forecast days to request. Open-Meteo allows
            between 1 and 16 days.
        language: Language code used for geocoding result names.

    ``get_coordinates`` returns a dictionary with latitude, longitude,
    location name and available administrative/time-zone details.

    ``get_weather`` returns a dictionary containing the shared Forecast
    fields: location, latitude, longitude, temperature, feels_like, humidity,
    wind_speed, precipitation, weather_code, forecast_times,
    hourly_temperatures, hourly_precipitation and hourly_wind_speeds.
    """

    def __init__(
        self,
        timeout: float = 10.0,
        forecast_days: int = 7,
        language: str = "en",
    ) -> None:
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("timeout must be a positive number of seconds")
        if isinstance(forecast_days, bool) or not isinstance(forecast_days, int):
            raise ValueError("forecast_days must be an integer between 1 and 16")
        if not 1 <= forecast_days <= 16:
            raise ValueError("forecast_days must be between 1 and 16")
        if not isinstance(language, str) or not language.strip():
            raise ValueError("language must be a non-empty language code")

        self.timeout = float(timeout)
        self.forecast_days = forecast_days
        self.language = language.strip().lower()

    def get_coordinates(self, location: str) -> Dict[str, Any]:
        """Convert a place name into coordinates using Open-Meteo Geocoding.

        The first matching result is selected. To improve matching, users can
        include an administrative area or country, for example
        ``"Minna, Nigeria"`` or ``"Zaria, Kaduna, Nigeria"``.

        Returns:
            A dictionary containing ``latitude``, ``longitude``, ``name``,
            ``country``, ``admin1`` and ``timezone`` where available.

        Raises:
            InvalidLocationError: If the input is empty or not text.
            LocationNotFoundError: If no matching place is returned.
            WeatherNetworkError / WeatherAPIError: If the request fails.
        """
        clean_location = self._validate_location(location)
        payload = self._request_json(
            GEOCODING_URL,
            {
                "name": clean_location,
                "count": 5,
                "language": self.language,
                "format": "json",
            },
        )

        results = payload.get("results")
        if not isinstance(results, list) or not results:
            raise LocationNotFoundError(
                f"No matching location was found for '{clean_location}'. "
                "Check the spelling or include the state/country."
            )

        result = results[0]
        if not isinstance(result, Mapping):
            raise WeatherDataError("The geocoding response contained an invalid location record.")

        latitude = self._finite_number(result.get("latitude"))
        longitude = self._finite_number(result.get("longitude"))
        if latitude is None or longitude is None:
            raise WeatherDataError("The geocoding response did not contain valid coordinates.")
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            raise WeatherDataError("The geocoding response contained coordinates outside valid ranges.")

        return {
            "name": str(result.get("name") or clean_location),
            "latitude": latitude,
            "longitude": longitude,
            "country": result.get("country"),
            "country_code": result.get("country_code"),
            "admin1": result.get("admin1"),
            "admin2": result.get("admin2"),
            "timezone": result.get("timezone"),
        }

    def get_weather(self, location: str) -> Dict[str, Any]:
        """Retrieve current conditions and hourly forecast for a location.

        The returned dictionary follows the shared Forecast data structure.
        It also contains useful optional fields such as hourly humidity,
        hourly apparent temperature and hourly weather codes.

        The current values are taken from Open-Meteo's ``current`` response.
        If a current value is unavailable, the first available hourly value
        is used as a fallback. Missing hourly values are never replaced with
        zero.

        Raises:
            InvalidLocationError: If the location input is empty or invalid.
            LocationNotFoundError: If geocoding cannot find the location.
            WeatherNetworkError: If the internet connection fails or times out.
            WeatherAPIError: If Open-Meteo reports a request/API error.
            WeatherDataError: If required forecast data is missing or malformed.
        """
        coordinates = self.get_coordinates(location)
        params = {
            "latitude": coordinates["latitude"],
            "longitude": coordinates["longitude"],
            "current": ",".join(
                [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "apparent_temperature",
                    "precipitation",
                    "weather_code",
                    "wind_speed_10m",
                ]
            ),
            "hourly": ",".join(
                [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "apparent_temperature",
                    "precipitation",
                    "weather_code",
                    "wind_speed_10m",
                    "precipitation_probability"
                ]
            ),
            "forecast_days": self.forecast_days,
            "timezone": "auto",
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
        }
        payload = self._request_json(FORECAST_URL, params)
        return self._build_forecast(location, coordinates, payload)

    def _request_json(self, endpoint: str, params: Mapping[str, Any]) -> Dict[str, Any]:
        """Make a GET request and convert transport/API failures to clear errors."""
        url = f"{endpoint}?{urlencode(params)}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
            method="GET",
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                status = getattr(response, "status", 200)
                if status < 200 or status >= 300:
                    raise WeatherAPIError(f"Open-Meteo returned HTTP status {status}.")
                raw_data = response.read()
        except HTTPError as error:
            detail = self._read_http_error(error)
            raise WeatherAPIError(
                f"Open-Meteo returned HTTP {error.code}. {detail}".strip()
            ) from error
        except (URLError, socket.timeout, TimeoutError, ConnectionError, OSError) as error:
            reason = getattr(error, "reason", error)
            raise WeatherNetworkError(
                f"Could not connect to Open-Meteo. Check your internet connection and try again. ({reason})"
            ) from error

        try:
            payload = json.loads(raw_data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError) as error:
            raise WeatherDataError("Open-Meteo returned a response that was not valid JSON.") from error

        if not isinstance(payload, dict):
            raise WeatherDataError("Open-Meteo returned an unexpected response format.")
        if payload.get("error"):
            reason = payload.get("reason") or "The API rejected the request."
            raise WeatherAPIError(f"Open-Meteo error: {reason}")
        return payload

    def _build_forecast(
        self,
        requested_location: str,
        coordinates: Mapping[str, Any],
        payload: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """Validate API hourly arrays and map them to the shared field names."""
        hourly = payload.get("hourly")
        if not isinstance(hourly, Mapping):
            raise WeatherDataError("The weather response did not include hourly forecast data.")

        times = hourly.get("time")
        temperatures = hourly.get("temperature_2m")
        precipitation = hourly.get("precipitation")
        wind_speeds = hourly.get("wind_speed_10m")

        if not isinstance(times, list) or not times:
            raise WeatherDataError("The hourly forecast did not include any forecast times.")

        required_series = {
            "temperature_2m": temperatures,
            "precipitation": precipitation,
            "wind_speed_10m": wind_speeds,
        }
        for field, values in required_series.items():
            if not isinstance(values, list) or len(values) != len(times):
                raise WeatherDataError(
                    f"The hourly forecast field '{field}' is missing or does not match the time list."
                )

        hourly_temperatures = self._normalise_numeric_series(temperatures, "temperature_2m")
        hourly_precipitation = self._normalise_numeric_series(precipitation, "precipitation")
        hourly_wind_speeds = self._normalise_numeric_series(wind_speeds, "wind_speed_10m")

        # Core measurements must be usable. Returning zero for missing weather
        # data could make a separate risk module incorrectly classify it as safe.
        for field, values in (
            ("temperature_2m", hourly_temperatures),
            ("precipitation", hourly_precipitation),
            ("wind_speed_10m", hourly_wind_speeds),
        ):
            if any(value is None for value in values):
                raise WeatherDataError(
                    f"The hourly forecast contains missing or invalid values in '{field}'."
                )

        hourly_humidity = self._optional_numeric_series(
            hourly.get("relative_humidity_2m"), len(times), "relative_humidity_2m"
        )
        hourly_feels_like = self._optional_numeric_series(
            hourly.get("apparent_temperature"), len(times), "apparent_temperature"
        )
        hourly_weather_codes = self._optional_integer_series(
            hourly.get("weather_code"), len(times), "weather_code"
        )
        hourly_rain_probability = self._optional_numeric_series(
            hourly.get("precipitation_probability"),
            len(times),
            "precipitation_probability"
        )

        current = payload.get("current")
        if not isinstance(current, Mapping):
            current = {}

        current_temperature = self._finite_number(current.get("temperature_2m"))
        current_humidity = self._finite_number(current.get("relative_humidity_2m"))
        current_feels_like = self._finite_number(current.get("apparent_temperature"))
        current_precipitation = self._finite_number(current.get("precipitation"))
        current_wind_speed = self._finite_number(current.get("wind_speed_10m"))
        current_weather_code = self._integer_or_none(current.get("weather_code"))

        display_name = self._make_display_name(coordinates, requested_location)

        forecast: Dict[str, Any] = {
            # Fields agreed in the team's shared Forecast data structure.
            "location": display_name,
            "latitude": float(coordinates["latitude"]),
            "longitude": float(coordinates["longitude"]),
            "temperature": self._first_available(current_temperature, hourly_temperatures),
            "feels_like": self._first_available(current_feels_like, hourly_feels_like),
            "humidity": self._first_available(current_humidity, hourly_humidity),
            "wind_speed": self._first_available(current_wind_speed, hourly_wind_speeds),
            "precipitation": self._first_available(current_precipitation, hourly_precipitation),
            "weather_code": self._first_available(current_weather_code, hourly_weather_codes),
            "forecast_times": list(times),
            "hourly_temperatures": hourly_temperatures,
            "hourly_precipitation": hourly_precipitation,
            "hourly_wind_speeds": hourly_wind_speeds,
            # Extra hourly data that other modules may use if needed.
            "hourly_humidity": hourly_humidity,
            "hourly_feels_like": hourly_feels_like,
            "hourly_weather_codes": hourly_weather_codes,
            "hourly_precipitation_probability": hourly_rain_probability,
            # Useful metadata for displaying local forecast times in the GUI.
            "timezone": payload.get("timezone") or coordinates.get("timezone"),
            "timezone_abbreviation": payload.get("timezone_abbreviation"),
            "utc_offset_seconds": payload.get("utc_offset_seconds"),
            "elevation": payload.get("elevation"),
            "current_time": current.get("time"),
            "hourly_units": payload.get("hourly_units", {}),
            "current_units": payload.get("current_units", {}),
        }
        return forecast

    @staticmethod
    def _validate_location(location: str) -> str:
        if not isinstance(location, str) or not location.strip():
            raise InvalidLocationError("Enter a valid location, such as 'Minna, Nigeria'.")
        clean_location = " ".join(location.split())
        if len(clean_location) < 2:
            raise InvalidLocationError("Enter at least two characters for the location.")
        return clean_location

    @staticmethod
    def _finite_number(value: Any) -> Optional[float]:
        if isinstance(value, bool) or value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    @classmethod
    def _normalise_numeric_series(cls, values: List[Any], field: str) -> List[Optional[float]]:
        if not isinstance(values, list):
            raise WeatherDataError(f"The hourly forecast field '{field}' is not a list.")
        return [cls._finite_number(value) for value in values]

    @classmethod
    def _optional_numeric_series(
        cls, values: Any, expected_length: int, field: str
    ) -> List[Optional[float]]:
        if values is None:
            return [None] * expected_length
        if not isinstance(values, list) or len(values) != expected_length:
            raise WeatherDataError(
                f"The optional hourly forecast field '{field}' does not match the time list."
            )
        return cls._normalise_numeric_series(values, field)

    @classmethod
    def _optional_integer_series(
        cls, values: Any, expected_length: int, field: str
    ) -> List[Optional[int]]:
        if values is None:
            return [None] * expected_length
        if not isinstance(values, list) or len(values) != expected_length:
            raise WeatherDataError(
                f"The optional hourly forecast field '{field}' does not match the time list."
            )
        return [cls._integer_or_none(value) for value in values]

    @classmethod
    def _integer_or_none(cls, value: Any) -> Optional[int]:
        number = cls._finite_number(value)
        if number is None or not number.is_integer():
            return None
        return int(number)

    @staticmethod
    def _first_available(current_value: Any, hourly_values: List[Any]) -> Any:
        if current_value is not None:
            return current_value
        return hourly_values[0] if hourly_values else None

    @staticmethod
    def _make_display_name(coordinates: Mapping[str, Any], requested_location: str) -> str:
        name = str(coordinates.get("name") or requested_location)
        admin1 = coordinates.get("admin1")
        country = coordinates.get("country")
        parts = [name]
        if admin1 and str(admin1).casefold() != name.casefold():
            parts.append(str(admin1))
        if country and str(country).casefold() not in {part.casefold() for part in parts}:
            parts.append(str(country))
        return ", ".join(parts)

    @staticmethod
    def _read_http_error(error: HTTPError) -> str:
        try:
            body = error.read(500).decode("utf-8", errors="replace").strip()
            parsed = json.loads(body) if body else {}
            if isinstance(parsed, dict):
                return str(parsed.get("reason") or parsed.get("message") or "")
            return body
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return ""
