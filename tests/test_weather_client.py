"""Unit tests for the Member 2 Open-Meteo weather client."""

import io
import json
import unittest
from urllib.error import HTTPError, URLError
from unittest.mock import patch

from services.weather_client import (
    FORECAST_URL,
    GEOCODING_URL,
    InvalidLocationError,
    LocationNotFoundError,
    WeatherAPIError,
    WeatherClient,
    WeatherDataError,
    WeatherNetworkError,
)


class FakeResponse:
    def __init__(self, body, status=200):
        self.body = body if isinstance(body, bytes) else body.encode("utf-8")
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self, amount=-1):
        return self.body if amount == -1 else self.body[:amount]


class WeatherClientTests(unittest.TestCase):
    def setUp(self):
        self.client = WeatherClient(timeout=2, forecast_days=3)
        self.geocoding_payload = {
            "results": [
                {
                    "name": "Minna",
                    "latitude": 9.6139,
                    "longitude": 6.5569,
                    "country": "Nigeria",
                    "country_code": "NG",
                    "admin1": "Niger",
                    "timezone": "Africa/Lagos",
                }
            ]
        }
        self.forecast_payload = {
            "latitude": 9.625,
            "longitude": 6.5625,
            "elevation": 250.0,
            "timezone": "Africa/Lagos",
            "timezone_abbreviation": "WAT",
            "utc_offset_seconds": 3600,
            "current": {
                "time": "2026-11-07T10:00",
                "temperature_2m": 29.4,
                "relative_humidity_2m": 55,
                "apparent_temperature": 31.0,
                "precipitation": 0.0,
                "weather_code": 1,
                "wind_speed_10m": 12.5,
            },
            "hourly": {
                "time": [
                    "2026-11-07T10:00",
                    "2026-11-07T11:00",
                    "2026-11-07T12:00",
                ],
                "temperature_2m": [29.4, 30.1, 31.0],
                "relative_humidity_2m": [55, 52, 50],
                "apparent_temperature": [31.0, 32.0, 33.0],
                "precipitation": [0.0, 0.1, 0.4],
                "weather_code": [1, 2, 61],
                "wind_speed_10m": [12.5, 14.0, 17.0],
            },
            "hourly_units": {"temperature_2m": "°C", "wind_speed_10m": "km/h"},
            "current_units": {"temperature_2m": "°C"},
        }

    def test_constructor_rejects_invalid_forecast_days(self):
        with self.assertRaises(ValueError):
            WeatherClient(forecast_days=17)

    def test_empty_location_is_rejected_without_api_call(self):
        with patch.object(self.client, "_request_json") as request:
            with self.assertRaises(InvalidLocationError):
                self.client.get_coordinates("   ")
        request.assert_not_called()

    def test_get_coordinates_returns_location_details(self):
        with patch.object(self.client, "_request_json", return_value=self.geocoding_payload) as request:
            result = self.client.get_coordinates("  Minna,   Nigeria ")

        self.assertEqual(result["latitude"], 9.6139)
        self.assertEqual(result["longitude"], 6.5569)
        self.assertEqual(result["country"], "Nigeria")
        request.assert_called_once()
        self.assertEqual(request.call_args.args[0], GEOCODING_URL)
        self.assertEqual(request.call_args.args[1]["name"], "Minna, Nigeria")

    def test_location_not_found_raises_clear_exception(self):
        with patch.object(self.client, "_request_json", return_value={"results": []}):
            with self.assertRaises(LocationNotFoundError):
                self.client.get_coordinates("PlaceThatDoesNotExist")

    def test_get_weather_returns_the_shared_forecast_fields(self):
        with patch.object(
            self.client,
            "_request_json",
            side_effect=[self.geocoding_payload, self.forecast_payload],
        ) as request:
            forecast = self.client.get_weather("Minna, Nigeria")

        expected_fields = {
            "location", "latitude", "longitude", "temperature", "feels_like",
            "humidity", "wind_speed", "precipitation", "weather_code",
            "forecast_times", "hourly_temperatures", "hourly_precipitation",
            "hourly_wind_speeds",
        }
        self.assertTrue(expected_fields.issubset(forecast.keys()))
        self.assertEqual(forecast["location"], "Minna, Niger, Nigeria")
        self.assertEqual(forecast["temperature"], 29.4)
        self.assertEqual(forecast["feels_like"], 31.0)
        self.assertEqual(forecast["humidity"], 55.0)
        self.assertEqual(forecast["wind_speed"], 12.5)
        self.assertEqual(forecast["precipitation"], 0.0)
        self.assertEqual(forecast["weather_code"], 1)
        self.assertEqual(forecast["timezone"], "Africa/Lagos")
        self.assertEqual(len(request.call_args_list), 2)
        self.assertEqual(request.call_args_list[1].args[0], FORECAST_URL)

    def test_hourly_lists_are_index_aligned(self):
        with patch.object(
            self.client,
            "_request_json",
            side_effect=[self.geocoding_payload, self.forecast_payload],
        ):
            forecast = self.client.get_weather("Minna")

        expected_length = len(forecast["forecast_times"])
        self.assertEqual(len(forecast["hourly_temperatures"]), expected_length)
        self.assertEqual(len(forecast["hourly_precipitation"]), expected_length)
        self.assertEqual(len(forecast["hourly_wind_speeds"]), expected_length)
        self.assertEqual(len(forecast["hourly_humidity"]), expected_length)
        self.assertEqual(len(forecast["hourly_weather_codes"]), expected_length)
        self.assertEqual(forecast["hourly_weather_codes"], [1, 2, 61])

    def test_missing_optional_hourly_fields_are_padded_with_none(self):
        payload = json.loads(json.dumps(self.forecast_payload))
        for optional_field in ("relative_humidity_2m", "apparent_temperature", "weather_code"):
            payload["hourly"].pop(optional_field)

        with patch.object(self.client, "_request_json", side_effect=[self.geocoding_payload, payload]):
            forecast = self.client.get_weather("Minna")

        count = len(forecast["forecast_times"])
        self.assertEqual(forecast["hourly_humidity"], [None] * count)
        self.assertEqual(forecast["hourly_feels_like"], [None] * count)
        self.assertEqual(forecast["hourly_weather_codes"], [None] * count)

    def test_missing_or_misaligned_required_data_raises_error(self):
        payload = json.loads(json.dumps(self.forecast_payload))
        payload["hourly"]["wind_speed_10m"] = [10.0]

        with patch.object(self.client, "_request_json", side_effect=[self.geocoding_payload, payload]):
            with self.assertRaises(WeatherDataError):
                self.client.get_weather("Minna")

    def test_missing_values_in_core_hourly_data_are_not_treated_as_zero(self):
        payload = json.loads(json.dumps(self.forecast_payload))
        payload["hourly"]["precipitation"][1] = None

        with patch.object(self.client, "_request_json", side_effect=[self.geocoding_payload, payload]):
            with self.assertRaises(WeatherDataError):
                self.client.get_weather("Minna")

    def test_network_error_is_converted_to_clear_exception(self):
        with patch("services.weather_client.urlopen", side_effect=URLError("offline")):
            with self.assertRaises(WeatherNetworkError):
                self.client._request_json(GEOCODING_URL, {"name": "Minna"})

    def test_http_error_is_converted_to_api_exception(self):
        error = HTTPError(
            GEOCODING_URL,
            503,
            "Service unavailable",
            hdrs=None,
            fp=io.BytesIO(b'{"reason":"Temporary outage"}'),
        )
        with patch("services.weather_client.urlopen", side_effect=error):
            with self.assertRaises(WeatherAPIError) as context:
                self.client._request_json(GEOCODING_URL, {"name": "Minna"})
        self.assertIn("503", str(context.exception))

    def test_invalid_json_response_is_rejected(self):
        with patch("services.weather_client.urlopen", return_value=FakeResponse("not json")):
            with self.assertRaises(WeatherDataError):
                self.client._request_json(GEOCODING_URL, {"name": "Minna"})

    def test_api_level_error_is_reported(self):
        response = FakeResponse('{"error": true, "reason": "Invalid parameter"}')
        with patch("services.weather_client.urlopen", return_value=response):
            with self.assertRaises(WeatherAPIError) as context:
                self.client._request_json(GEOCODING_URL, {"name": "Minna"})
        self.assertIn("Invalid parameter", str(context.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
