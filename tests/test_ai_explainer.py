import pytest
from unittest.mock import MagicMock, patch

from services.ai_explainer import AIExplainer


@pytest.fixture
def explainer():
    """Create an AIExplainer instance without requiring an API key."""
    instance = AIExplainer.__new__(AIExplainer)
    instance.client = None
    instance.model = "gemini-3.5-flash-lite"
    return instance


@pytest.fixture
def valid_risk():
    """Provide a valid risk classification."""
    return {
        "level": "RISKY",
        "reasons": ["High temperature", "Strong wind"],
        "warnings": ["Stay hydrated"]
    }


@pytest.fixture
def valid_weather():
    """Provide valid weather information."""
    return {
        "location": "Abuja",
        "temperature": 35,
        "feels_like": 38,
        "humidity": 70,
        "wind_speed": 20,
        "precipitation": 0,
        "weather_code": 1
    }


class TestAIExplainer:

    def test_initialization_without_api_key(self, monkeypatch):
        """Test initialization when no Gemini API key exists."""

        monkeypatch.setattr(
            "services.ai_explainer.load_dotenv",
            lambda: None
        )

        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        explainer = AIExplainer()

        assert explainer.client is None
        assert explainer.model == "gemini-3.5-flash-lite"

    def test_initialization_with_api_key(self, monkeypatch):
        """Test that the Gemini client initializes with an API key."""

        monkeypatch.setattr(
            "services.ai_explainer.load_dotenv",
            lambda: None
        )

        monkeypatch.setenv("GEMINI_API_KEY", "test-api-key")

        with patch("services.ai_explainer.genai.Client") as mock_client:

            explainer = AIExplainer()

            mock_client.assert_called_once()
            assert explainer.client is not None

    def test_invalid_risk_type(self, explainer, valid_weather):
        """Test handling of a risk result that is not a dictionary."""

        result = explainer.explain_risk(
            valid_weather,
            "Football",
            "RISKY"
        )

        assert result == "Risk result is missing or invalid."

    @pytest.mark.parametrize(
        "level",
        ["UNKNOWN", "LOW", "HIGH", None, 123]
    )
    def test_invalid_risk_level(
        self, explainer, valid_weather, level
    ):
        """Test handling of unsupported risk classifications."""

        risk = {
            "level": level,
            "reasons": [],
            "warnings": []
        }

        result = explainer.explain_risk(
            valid_weather,
            "Football",
            risk
        )

        assert result == "Risk result is missing or invalid."

    def test_missing_risk_reasons_and_warnings(
        self, explainer, valid_weather
    ):
        """Test that missing reasons and warnings use empty lists."""

        risk = {"level": "SAFE"}

        result = explainer.explain_risk(
            valid_weather,
            "Walking",
            risk
        )

        assert "Reasons: []." in result
        assert "Warnings: []." in result

    def test_invalid_reasons_and_warnings(
        self, explainer, valid_weather
    ):
        """Test that invalid reasons and warnings are handled."""

        risk = {
            "level": "SAFE",
            "reasons": "Too hot",
            "warnings": "Be careful"
        }

        result = explainer.explain_risk(
            valid_weather,
            "Walking",
            risk
        )

        assert "Reasons: []." in result
        assert "Warnings: []." in result

    @pytest.mark.parametrize(
        "activity",
        ["", "   ", None, 123]
    )
    def test_invalid_activity(
        self, explainer, valid_weather, valid_risk, activity
    ):
        """Test fallback when the activity is invalid."""

        result = explainer.explain_risk(
            valid_weather,
            activity,
            valid_risk
        )

        assert "AI explanation is unavailable right now." in result
        assert "Risk: RISKY." in result

    def test_missing_weather_data(self, explainer, valid_risk):
        """Test fallback when weather information is unavailable."""

        result = explainer.explain_risk(
            {},
            "Football",
            valid_risk
        )

        assert "AI explanation is unavailable right now." in result

    def test_weather_with_location_only(
        self, explainer, valid_risk
    ):
        """Test fallback when only location is provided."""

        result = explainer.explain_risk(
            {"location": "Abuja"},
            "Football",
            valid_risk
        )

        assert "AI explanation is unavailable right now." in result

    def test_no_gemini_client(
        self, explainer, valid_weather, valid_risk
    ):
        """Test fallback when Gemini is unavailable."""

        explainer.client = None

        result = explainer.explain_risk(
            valid_weather,
            "Football",
            valid_risk
        )

        assert "AI explanation is unavailable right now." in result

    def test_successful_ai_explanation(
        self, explainer, valid_weather, valid_risk
    ):
        """Test successful response from the Gemini API."""

        expected_response = (
            "The temperature is high, making outdoor football risky. "
            "Stay hydrated and avoid prolonged exposure to the sun."
        )

        mock_client = MagicMock()

        mock_client.models.generate_content.return_value.text = (
            expected_response
        )

        explainer.client = mock_client

        result = explainer.explain_risk(
            valid_weather,
            "Football",
            valid_risk
        )

        assert result == expected_response

        mock_client.models.generate_content.assert_called_once()

        call_arguments = (
            mock_client.models.generate_content.call_args
        )

        assert call_arguments.kwargs["model"] == explainer.model
        assert "Football" in call_arguments.kwargs["contents"]
        assert "RISKY" in call_arguments.kwargs["contents"]

    def test_empty_gemini_response(
        self, explainer, valid_weather, valid_risk
    ):
        """Test fallback when Gemini returns an empty response."""

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value.text = ""

        explainer.client = mock_client

        result = explainer.explain_risk(
            valid_weather,
            "Football",
            valid_risk
        )

        assert "AI explanation is unavailable right now." in result

    def test_none_gemini_response(
        self, explainer, valid_weather, valid_risk
    ):
        """Test fallback when Gemini returns no text."""

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value.text = None

        explainer.client = mock_client

        result = explainer.explain_risk(
            valid_weather,
            "Football",
            valid_risk
        )

        assert "AI explanation is unavailable right now." in result

    def test_gemini_api_exception(
        self, explainer, valid_weather, valid_risk
    ):
        """Test fallback when the Gemini API raises an exception."""

        mock_client = MagicMock()

        mock_client.models.generate_content.side_effect = Exception(
            "Connection failed"
        )

        explainer.client = mock_client

        result = explainer.explain_risk(
            valid_weather,
            "Football",
            valid_risk
        )

        assert "AI explanation is unavailable right now." in result

    def test_weather_object_support(
        self, explainer, valid_risk
    ):
        """Test that weather data can be provided as an object."""

        class Weather:
            location = "Abuja"
            temperature = 32
            humidity = 65
            wind_speed = 15

        mock_client = MagicMock()

        mock_client.models.generate_content.return_value.text = (
            "Weather conditions are suitable for walking."
        )

        explainer.client = mock_client

        result = explainer.explain_risk(
            Weather(),
            "Walking",
            valid_risk
        )

        assert result == (
            "Weather conditions are suitable for walking."
        )
