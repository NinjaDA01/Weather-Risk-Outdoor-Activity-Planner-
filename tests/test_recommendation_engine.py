import pytest

from services.recommendation_engine import RecommendationEngine


@pytest.fixture
def engine():
    """Create a RecommendationEngine instance."""
    return RecommendationEngine()


@pytest.fixture
def good_forecast():
    """Provide favourable weather conditions."""
    return [
        {
            "time": "2026-11-05T06:00",
            "temperature": 23,
            "humidity": 55,
            "wind_speed": 10,
            "rain_probability": 5,
            "condition": "Clear",
            "uv_index": 2,
            "visibility": 10
        },
        {
            "time": "2026-11-05T08:00",
            "temperature": 25,
            "humidity": 60,
            "wind_speed": 12,
            "rain_probability": 10,
            "condition": "Clear",
            "uv_index": 3,
            "visibility": 10
        },
        {
            "time": "2026-11-05T10:00",
            "temperature": 27,
            "humidity": 65,
            "wind_speed": 15,
            "rain_probability": 5,
            "condition": "Partly cloudy",
            "uv_index": 5,
            "visibility": 10
        }
