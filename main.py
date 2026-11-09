"""Main entry point for the Weather Risk & Outdoor Activity Planner.

Integration contract used by this file:
- WeatherClient.get_weather(location) returns a dictionary containing
  the current weather and hourly forecast data.
- ActivityRiskAnalyzer.assess_risk(forecast, activity) returns a dict with
  level, reasons and warnings. level is SAFE, MANAGEABLE, RISKY or AVOID.
- RecommendationEngine.recommend_best_time(...) returns a dictionary
  containing the recommended time and supporting information.
- RecommendationEngine.generate_checklist(...) returns checklist data.
- AIExplainer.explain_risk(weather, activity, risk) returns explanation text.
- MainWindow accepts root, on_assess and on_save, and implements
  the view methods documented in the project leader guide.
"""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from gui.main_window import MainWindow

from services.ai_explainer import AIExplainer
from services.recommendation_engine import RecommendationEngine
from services.risk_analyzer import ActivityRiskAnalyzer
from services.weather_client import WeatherClient
from storage.json_storage import JSONStorage
from utils.validator import validate_location


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
VALID_RISK_LEVELS = {"SAFE", "MANAGEABLE", "RISKY", "AVOID"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.FileHandler(BASE_DIR / "weather_planner.log", encoding="utf-8"),
              logging.StreamHandler()],
)
logger = logging.getLogger("weather_planner")


def to_plain_data(value: Any) -> Any:
    """Convert common Python objects into dictionaries/lists for the GUI and JSON."""
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): to_plain_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_plain_data(item) for item in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return to_plain_data(value.to_dict())
    if hasattr(value, "__dict__"):
        return {
            key: to_plain_data(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


class WeatherActivityPlannerApp:
    """Coordinates the GUI, weather services, analysis, recommendations and storage."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Weather Risk & Outdoor Activity Planner")
        self.root.minsize(850, 600)

        # Create each service once. The controller reuses these objects for requests.
        self.weather_client = WeatherClient()
        self.risk_analyzer = ActivityRiskAnalyzer()
        self.recommendation_engine = RecommendationEngine()
        self.ai_explainer = AIExplainer()
        self.storage = JSONStorage(DATA_DIR)

        self.last_result: dict[str, Any] | None = None
        self.is_busy = False
        self.event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()

        # The GUI calls these controller methods when the user clicks its buttons.
        self.view = MainWindow(
            self.root,
            on_assess=self.assess_activity,
            on_save=self.save_latest_plan,
        )

        # Poll the worker-thread queue on the Tkinter main thread.
        self.root.after(100, self.process_events)

    def assess_activity(self, location: str, activity: str) -> None:
        """Validate the user's request and start the assessment in a worker thread."""
        if self.is_busy:
            return

        location = (location or "").strip()
        activity = (activity or "").strip()

          try:
            if not location:
              raise ValueError("Enter a location before requesting an assessment.")

            if not activity:
              raise ValueError("Select an outdoor activity first.")

        location = validate_location(location)
        except (TypeError, ValueError) as error:
            self.view.show_error(str(error))
            return

        self.is_busy = True
        self.view.set_busy(True, "Retrieving forecast and assessing conditions...")

        worker = threading.Thread(
            target=self.run_assessment,
            args=(location, activity),
            name="weather-assessment-worker",
            daemon=True,
        )
        worker.start()

    def run_assessment(self, location: str, activity: str) -> None:
        """Run the service pipeline away from the GUI thread."""
        try:
            # 1. Retrieve and organise weather data.
            forecast = self.weather_client.get_weather(location)
            if forecast is None:
                raise RuntimeError("The weather service returned no forecast.")
            if not isinstance(forecast, dict):
                raise TypeError(
                    "WeatherClient.get_weather() must return forecast data as a dictionary."
          )

            # 2. Apply deterministic, rule-based safety analysis.
            risk = self.risk_analyzer.assess_risk(forecast, activity)
            risk = to_plain_data(risk)
            if not isinstance(risk, dict):
                raise TypeError("assess_risk() must return a dictionary risk result.")
            risk_level = str(risk.get("level", "")).upper()
            if risk_level not in VALID_RISK_LEVELS:
                raise ValueError(
                    "Risk result has an unsupported level. Use SAFE, MANAGEABLE, RISKY or AVOID."
                )
            risk["level"] = risk_level

            # 3. Find a suitable time and create a practical checklist.
            best_time = self.recommendation_engine.recommend_best_time(forecast, activity)
            checklist = self.recommendation_engine.generate_checklist(forecast, activity)

            # 4. Ask Gemini for an explanation. AI failure must not erase the risk result.
            try:
                explanation = self.ai_explainer.explain_risk(forecast, activity, risk)
                explanation = str(explanation).strip() if explanation else ""
                if not explanation:
                    explanation = "AI explanation is unavailable. Use the rule-based risk result above."
            except Exception:
                logger.exception("AI explanation failed; retaining the rule-based risk result.")
                explanation = "AI explanation is unavailable. The risk level above was calculated by the rule-based analyzer."

            result = {
                "location": location,
                "activity": activity,
                "weather": to_plain_data(forecast),
                "risk": risk,
                "best_time": to_plain_data(best_time),
                "checklist": to_plain_data(checklist),
                "explanation": explanation,
            }
            self.event_queue.put(("success", result))

        except Exception as error:
            logger.exception("Assessment failed for location=%r, activity=%r", location, activity)
            self.event_queue.put(("error", self.friendly_error_message(error)))

    @staticmethod
    def friendly_error_message(error: Exception) -> str:
        """Turn common service failures into useful messages for the user."""
        name = error.__class__.__name__.lower()
        message = str(error).strip()

        if isinstance(error, (ConnectionError, TimeoutError)) or "timeout" in name:
            return "The weather service could not be reached. Check your internet connection and try again."
        if "connection" in name or "network" in name:
            return "A network problem prevented the forecast from loading. Check your connection and try again."
        if isinstance(error, ValueError) and message:
            return message
        if message:
            return f"The assessment could not be completed: {message}"
        return "The assessment could not be completed because an unexpected error occurred."

    def process_events(self) -> None:
        """Apply worker results to Tkinter widgets on the main GUI thread."""
        try:
            while True:
                event_type, payload = self.event_queue.get_nowait()
                try:
                    if event_type == "success":
                        self.last_result = payload
                        self.view.display_results(payload)
                        self.view.set_status("Assessment complete.")
                        self.save_search_history(payload)
                    elif event_type == "error":
                        self.view.show_error(str(payload))
                        self.view.set_status("Assessment was not completed.")
                except Exception:
                    logger.exception("The GUI could not display an assessment event.")
                    self.view.show_error("The result was calculated, but the interface could not display it correctly.")
                finally:
                    self.is_busy = False
                    self.view.set_busy(False, "")
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_events)

    def save_search_history(self, result: dict[str, Any]) -> None:
        """Append a successful assessment to the local search history."""
        try:
            history = self.storage.load_data("search_history.json")
            if not isinstance(history, list):
                history = []
            history.append(result)
            self.storage.save_data("search_history.json", history[-50:])
        except Exception:
            # Storage is useful, but a history-write problem should not hide results.
            logger.exception("Could not update search history.")
            self.view.set_status("Assessment complete, but search history could not be saved.")

    def save_latest_plan(self) -> None:
        """Save the most recent assessment when the user selects Save Plan."""
        if self.last_result is None:
            self.view.show_error("There is no completed assessment to save yet.")
            return

        try:
            plans = self.storage.load_data("saved_plans.json")
            if not isinstance(plans, list):
                plans = []
            plans.append(self.last_result)
            self.storage.save_data("saved_plans.json", plans)
            self.view.set_status("Plan saved successfully.")
        except Exception as error:
            logger.exception("Could not save the current plan.")
            self.view.show_error(f"The plan could not be saved: {error}")


def main() -> None:
    """Create the Tkinter window and start the event loop."""
    root = tk.Tk()
    WeatherActivityPlannerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

