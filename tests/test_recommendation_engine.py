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
    ]


@pytest.fixture
def bad_forecast():
    """Provide unfavourable weather conditions."""
    return [
        {
            "time": "2026-11-05T10:00",
            "temperature": 42,
            "humidity": 90,
            "wind_speed": 65,
            "rain_probability": 95,
            "condition": "Thunderstorm",
            "uv_index": 12,
            "visibility": 0.5
        }
    ]


# ============================================================
# 1. INITIALIZATION AND SUPPORTED ACTIVITIES
# ============================================================

class TestInitialization:

    def test_engine_initialization(self, engine):
        """Test that the engine initializes correctly."""

        assert isinstance(engine, RecommendationEngine)

    def test_supported_activities(self, engine):
        """Test that all supported activities are available."""

        expected = [
            "farming",
            "football",
            "jogging",
            "picnic",
            "travelling"
        ]

        assert engine.supported_activities == expected

    def test_default_risk_assessment(self):
        """Test initialization with a default risk assessment."""

        engine = RecommendationEngine("moderate")

        assert engine.default_risk == "moderate"


# ============================================================
# 2. ACTIVITY VALIDATION AND ALIASES
# ============================================================

class TestActivityValidation:

    @pytest.mark.parametrize(
        "activity, expected",
        [
            ("running", "jogging"),
            ("run", "jogging"),
            ("jog", "jogging"),
            ("soccer", "football"),
            ("footballing", "football"),
            ("farm", "farming"),
            ("agriculture", "farming"),
            ("travel", "travelling"),
            ("trip", "travelling"),
            ("traveling", "travelling"),
            ("picnicking", "picnic")
        ]
    )
    def test_activity_aliases(self, engine, activity, expected):

        name, profile = engine._resolve_activity(activity)

        assert name == expected
        assert isinstance(profile, dict)

    @pytest.mark.parametrize(
        "activity",
        ["", "   ", None, 123, "swimming", "cycling"]
    )
    def test_invalid_activity(self, engine, activity):
        """Test that unsupported activities raise ValueError."""

        with pytest.raises(ValueError):
            engine.recommend_best_time([], activity)


# ============================================================
# 3. BEST TIME RECOMMENDATION
# ============================================================

class TestBestTimeRecommendation:

    def test_successful_recommendation(
        self, engine, good_forecast
    ):
        """Test recommendation under favourable weather conditions."""

        result = engine.recommend_best_time(
            good_forecast,
            "jogging"
        )

        assert result["activity"] == "jogging"
        assert result["best_time"] is not None
        assert result["score"] >= 50
        assert result["rating"] in (
            "Excellent", "Good", "Fair"
        )

    def test_recommendation_contains_required_fields(
        self, engine, good_forecast
    ):
        """Test the structure of the recommendation result."""

        result = engine.recommend_best_time(
            good_forecast,
            "football"
        )

        required_fields = [
            "activity",
            "best_time",
            "score",
            "rating",
            "risk_level",
            "reasons",
            "warnings",
            "alternatives",
            "advice",
            "message"
        ]

        for field in required_fields:
            assert field in result

    def test_empty_forecast(self, engine):
        """Test behaviour when no forecast is available."""

        result = engine.recommend_best_time(
            [],
            "jogging"
        )

        assert result["best_time"] is None
        assert result["score"] == 0
        assert result["rating"] == "Poor"
        assert "No forecast data" in result["message"]

    def test_no_recommended_time(
        self, engine, bad_forecast
    ):
        """Test behaviour during extremely unfavourable weather."""

        result = engine.recommend_best_time(
            bad_forecast,
            "football"
        )

        assert result["best_time"] is None
        assert result["score"] == 0
        assert "postponing" in result["message"]

    def test_recommendation_stays_within_activity_window(
        self, engine
    ):
        """Test that recommendations respect activity time limits."""

        forecast = [
            {
                "time": "2026-11-05T02:00",
                "temperature": 23,
                "wind_speed": 5,
                "rain_probability": 0
            },
            {
                "time": "2026-11-05T06:00",
                "temperature": 23,
                "wind_speed": 5,
                "rain_probability": 0
            },
            {
                "time": "2026-11-05T22:00",
                "temperature": 23,
                "wind_speed": 5,
                "rain_probability": 0
            }
        ]

        result = engine.recommend_best_time(
            forecast,
            "jogging"
        )

        assert result["best_time"] == "2026-11-05T06:00"

    def test_recommendation_with_alias(
        self, engine, good_forecast
    ):
        """Test recommendations using activity aliases."""

        result = engine.recommend_best_time(
            good_forecast,
            "running"
        )

        assert result["activity"] == "jogging"

    def test_recommendation_with_external_high_risk(
        self, engine, good_forecast
    ):
        """Test that high external risk prevents recommendations."""

        result = engine.recommend_best_time(
            good_forecast,
            "jogging",
            risk_assessment="high"
        )

        assert result["best_time"] is None
        assert result["risk_level"] == "high"

    def test_recommendation_with_moderate_risk(
        self, engine, good_forecast
    ):
        """Test that moderate risk reduces suitability scores."""

        normal = engine.recommend_best_time(
            good_forecast,
            "jogging"
        )

        moderate = engine.recommend_best_time(
            good_forecast,
            "jogging",
            risk_assessment="moderate"
        )

        assert moderate["score"] < normal["score"]


# ============================================================
# 4. RISK ASSESSMENT
# ============================================================

class TestRiskAssessment:

    @pytest.mark.parametrize(
        "risk, expected",
        [
            ("low", 0),
            ("safe", 0),
            ("moderate", 1),
            ("manageable", 1),
            ("medium", 1),
            ("high", 2),
            ("risky", 2),
            ("extreme", 3),
            ("avoid", 3),
            ("severe", 3)
        ]
    )
    def test_risk_level_conversion(
        self, engine, risk, expected
    ):

        result = engine._risk_to_int(risk)

        assert result == expected

    def test_risk_dictionary(self, engine):

        risk = {"level": "high"}

        assert engine._risk_to_int(risk) == 2

    def test_risk_object(self, engine):

        class Risk:
            level = "extreme"

        assert engine._risk_to_int(Risk()) == 3

    def test_invalid_risk_defaults_to_low(self, engine):

        assert engine._risk_to_int(None) == 0
        assert engine._risk_to_int("unknown") == 0

    def test_risk_from_forecast_dictionary(
        self, engine, good_forecast
    ):
        """Test that risk can be supplied inside the forecast."""

        forecast = {
            "hourly": good_forecast,
            "risk": "high"
        }

        result = engine.recommend_best_time(
            forecast,
            "jogging"
        )

        assert result["best_time"] is None
        assert result["risk_level"] == "high"


# ============================================================
# 5. FORECAST DATA NORMALIZATION
# ============================================================

class TestForecastNormalization:

    def test_normal_forecast_format(
        self, engine, good_forecast
    ):

        result = engine._normalise_forecast(good_forecast)

        assert len(result) == 3
        assert result[0]["temp"] == 23
        assert result[0]["hour"] == 6

    def test_forecast_with_field_aliases(self, engine):

        forecast = [
            {
                "time": "2026-11-05T06:00",
                "temp": 25,
                "humidity_percent": 60,
                "wind_kph": 10,
                "pop": 0.2,
                "description": "Clear"
            }
        ]

        result = engine._normalise_forecast(forecast)

        assert result[0]["temp"] == 25
        assert result[0]["humidity"] == 60
        assert result[0]["wind"] == 10
        assert result[0]["rain"] == 20

    def test_open_meteo_forecast_format(self, engine):

        forecast = {
            "hourly": {
                "time": ["2026-11-05T06:00"],
                "temperature_2m": [25],
                "relative_humidity_2m": [60],
                "wind_speed_10m": [10],
                "precipitation_probability": [10],
                "weather_code": [0],
                "uv_index": [3],
                "visibility": [10000]
            }
        }

        result = engine._normalise_forecast(forecast)

        assert result[0]["temp"] == 25
        assert result[0]["humidity"] == 60
        assert result[0]["wind"] == 10
        assert result[0]["visibility"] == 10
        assert result[0]["condition"] == "clear sky"

    def test_empty_forecast(self, engine):

        assert engine._normalise_forecast(None) == []
        assert engine._normalise_forecast([]) == []

    def test_invalid_forecast_type(self, engine):

        with pytest.raises(TypeError):
            engine._normalise_forecast("invalid forecast")

    def test_wmo_weather_code_conversion(self, engine):

        forecast = [
            {
                "time": "2026-11-05T06:00",
                "weather_code": 95
            }
        ]

        result = engine._normalise_forecast(forecast)

        assert result[0]["condition"] == "thunderstorm"

    def test_datetime_parsing(self, engine):

        result = engine._parse_hour("2026-11-05T14:30")

        assert result == 14


# ============================================================
# 6. CHECKLIST GENERATION
# ============================================================

class TestChecklistGeneration:

    def test_successful_checklist(
        self, engine, good_forecast
    ):

        result = engine.generate_checklist(
            good_forecast,
            "jogging"
        )

        assert result["activity"] == "jogging"
        assert len(result["essentials"]) > 0
        assert "risk_level" in result
        assert "summary" in result

    def test_checklist_required_fields(
        self, engine, good_forecast
    ):

        result = engine.generate_checklist(
            good_forecast,
            "football"
        )

        required = [
            "activity",
            "essentials",
            "weather_gear",
            "safety",
            "risk_level",
            "summary"
        ]

        for field in required:
            assert field in result

    def test_checklist_contains_activity_essentials(
        self, engine, good_forecast
    ):
        """Test that activity-specific essentials are included."""

        result = engine.generate_checklist(
            good_forecast,
            "football"
        )

        assert "Football" in result["essentials"]
        assert "Water bottle" in result["essentials"]

    def test_hot_weather_checklist(self, engine):

        forecast = [
            {
                "time": "2026-11-05T12:00",
                "temperature": 35,
                "humidity": 70,
                "uv_index": 8
            }
        ]

        result = engine.generate_checklist(
            forecast,
            "jogging"
        )

        assert any(
            "water" in item.lower()
            for item in result["weather_gear"]
        )

        assert any(
            "sunscreen" in item.lower()
            for item in result["weather_gear"]
        )

    def test_rainy_weather_checklist(self, engine):

        forecast = [
            {
                "time": "2026-11-05T10:00",
                "temperature": 25,
                "rain_probability": 80,
                "condition": "Heavy rain"
            }
        ]

        result = engine.generate_checklist(
            forecast,
            "picnic"
        )

        assert "Umbrella or raincoat" in result["weather_gear"]

        assert any(
            "ground sheet" in item.lower()
            for item in result["weather_gear"]
        )

    def test_high_risk_checklist(
        self, engine, good_forecast
    ):

        result = engine.generate_checklist(
            good_forecast,
            "jogging",
            risk_assessment="high"
        )

        assert result["risk_level"] == "high"

        assert any(
            "postponing" in item.lower()
            for item in result["safety"]
        )

    def test_empty_forecast_checklist(self, engine):

        result = engine.generate_checklist(
            [],
            "travelling"
        )

        assert result["activity"] == "travelling"
        assert len(result["essentials"]) > 0
        assert result["summary"] == ""


# ============================================================
# 7. CHECKLIST FORMATTING
# ============================================================

class TestChecklistFormatting:

    def test_format_checklist(
        self, engine, good_forecast
    ):

        checklist = engine.generate_checklist(
            good_forecast,
            "jogging"
        )

        result = engine.format_checklist(checklist)

        assert isinstance(result, str)
        assert "Checklist for jogging" in result
        assert "Essentials:" in result

    def test_format_checklist_contains_items(self, engine):

        checklist = {
            "activity": "football",
            "risk_level": "low",
            "summary": "Expected: 25°C.",
            "essentials": ["Football", "Water bottle"],
            "weather_gear": ["Sunscreen"],
            "safety": ["Warm up before playing."]
        }

        result = engine.format_checklist(checklist)

        assert "Football" in result
        assert "Water bottle" in result
        assert "Sunscreen" in result
        assert "Warm up before playing." in result


# ============================================================
# 8. GENERAL HELPER FUNCTIONS
# ============================================================

class TestHelperFunctions:

    def test_duplicate_removal(self, engine):

        items = ["Water", "Food", "Water", "Phone"]

        result = engine._dedupe(items)

        assert result == ["Water", "Food", "Phone"]

    @pytest.mark.parametrize(
        "score, expected",
        [
            (90, "Excellent"),
            (75, "Good"),
            (55, "Fair"),
            (30, "Poor")
        ]
    )
    def test_score_rating(self, engine, score, expected):

        assert engine._rating(score) == expected

    def test_score_is_within_valid_range(
        self, engine, good_forecast
    ):

        result = engine.recommend_best_time(
            good_forecast,
            "jogging"
        )

        assert 0 <= result["score"] <= 100
