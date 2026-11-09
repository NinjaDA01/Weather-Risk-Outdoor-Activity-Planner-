"""Main entry point for the Weather Risk & Outdoor Activity Planner.

Integration contract:
- WeatherClient.get_weather(location) returns a weather dictionary.
- ActivityRiskAnalyzer.assess_risk(forecast, activity) returns a risk dictionary.
- RecommendationEngine recommends suitable activity times.
- RecommendationEngine generates activity preparation checklists.
- AIExplainer provides Gemini-powered risk explanations.
- JSONStorage saves and retrieves application data.
- validate_location() cleans and validates user location input.
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


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

VALID_RISK_LEVELS = {
    "SAFE",
    "MANAGEABLE",
    "RISKY",
    "AVOID"
}


# ============================================================
# LOGGING CONFIGURATION
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(
            BASE_DIR / "weather_planner.log",
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ],
)

logger = logging.getLogger("weather_planner")


# ============================================================
# DATA CONVERSION
# ============================================================

def to_plain_data(value: Any) -> Any:
    """Convert Python objects into dictionaries and lists."""

    if is_dataclass(value):
        return to_plain_data(asdict(value))

    if isinstance(value, dict):
        return {
            str(key): to_plain_data(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            to_plain_data(item)
            for item in value
        ]

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


# ============================================================
# MAIN APPLICATION CONTROLLER
# ============================================================

class WeatherActivityPlannerApp:
    """Coordinates the GUI, weather services, analysis and storage."""

    def __init__(self, root: tk.Tk) -> None:

        self.root = root

        self.root.title(
            "Weather Risk & Outdoor Activity Planner"
        )

        self.root.minsize(850, 600)

        # ----------------------------------------------------
        # INITIALISE APPLICATION SERVICES
        # ----------------------------------------------------

        self.weather_client = WeatherClient()

        self.risk_analyzer = ActivityRiskAnalyzer()

        self.recommendation_engine = RecommendationEngine()

        self.ai_explainer = AIExplainer()

        self.storage = JSONStorage(DATA_DIR)

        # ----------------------------------------------------
        # APPLICATION STATE
        # ----------------------------------------------------

        self.last_result: dict[str, Any] | None = None

        self.is_busy = False

        self.event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()

        # ----------------------------------------------------
        # INITIALISE GUI
        # ----------------------------------------------------

        self.view = MainWindow(
            self.root,
            on_assess=self.assess_activity,
            on_save=self.save_latest_plan,
        )

        # Process background events on the main Tkinter thread.
        self.root.after(100, self.process_events)

    # ========================================================
    # ACTIVITY ASSESSMENT
    # ========================================================

    def assess_activity(
        self,
        location: str,
        activity: str
    ) -> None:
        """Validate user input and start the assessment."""

        if self.is_busy:
            return

        location = (location or "").strip()
        activity = (activity or "").strip()

        try:

            if not location:
                raise ValueError(
                    "Enter a location before requesting an assessment."
                )

            if not activity:
                raise ValueError(
                    "Select an outdoor activity first."
                )

            # Use the teammate's location validation function.
            location = validate_location(location)

        except (TypeError, ValueError) as error:

            self.view.show_error(str(error))
            return

        self.is_busy = True

        self.view.set_busy(
            True,
            "Retrieving forecast and assessing conditions..."
        )

        # Run weather retrieval and analysis in a background thread.
        worker = threading.Thread(
            target=self.run_assessment,
            args=(location, activity),
            name="weather-assessment-worker",
            daemon=True
        )

        worker.start()

    # ========================================================
    # WEATHER AND RISK ASSESSMENT PIPELINE
    # ========================================================

    def run_assessment(
        self,
        location: str,
        activity: str
    ) -> None:
        """Execute the assessment pipeline in a worker thread."""

        try:

            # ------------------------------------------------
            # 1. RETRIEVE WEATHER INFORMATION
            # ------------------------------------------------

            forecast = self.weather_client.get_weather(location)

            if forecast is None:
                raise RuntimeError(
                    "The weather service returned no forecast."
                )

            if not isinstance(forecast, dict):
                raise TypeError(
                    "WeatherClient.get_weather() must return "
                    "forecast data as a dictionary."
                )

            # ------------------------------------------------
            # 2. PERFORM RULE-BASED RISK ANALYSIS
            # ------------------------------------------------

            risk = self.risk_analyzer.assess_risk(
                forecast,
                activity
            )

            risk = to_plain_data(risk)

            if not isinstance(risk, dict):
                raise TypeError(
                    "assess_risk() must return a dictionary."
                )

            risk_level = str(
                risk.get("level", "")
            ).upper()

            if risk_level not in VALID_RISK_LEVELS:
                raise ValueError(
                    "Risk result has an unsupported level. "
                    "Expected SAFE, MANAGEABLE, RISKY or AVOID."
                )

            risk["level"] = risk_level

            # ------------------------------------------------
            # 3. GENERATE RECOMMENDATIONS
            # ------------------------------------------------

            best_time = self.recommendation_engine.recommend_best_time(
                forecast,
                activity,
                risk
            )

            checklist = self.recommendation_engine.generate_checklist(
                forecast,
                activity,
                risk
            )

            # ------------------------------------------------
            # 4. GEMINI AI EXPLANATION
            # ------------------------------------------------

            try:

                explanation = self.ai_explainer.explain_risk(
                    forecast,
                    activity,
                    risk
                )

                explanation = (
                    str(explanation).strip()
                    if explanation
                    else ""
                )

                if not explanation:
                    explanation = (
                        "AI explanation is unavailable. "
                        "Use the rule-based risk result above."
                    )

            except Exception:

                logger.exception(
                    "AI explanation failed. "
                    "Retaining the rule-based risk result."
                )

                explanation = (
                    "AI explanation is unavailable. "
                    "The risk level above was calculated "
                    "by the rule-based analyzer."
                )

            # ------------------------------------------------
            # 5. ORGANISE FINAL RESULTS
            # ------------------------------------------------

            result = {
                "location": location,
                "activity": activity,
                "weather": to_plain_data(forecast),
                "risk": risk,
                "best_time": to_plain_data(best_time),
                "checklist": to_plain_data(checklist),
                "explanation": explanation
            }

            # Send results to the main GUI thread.
            self.event_queue.put(
                ("success", result)
            )

        except Exception as error:

            logger.exception(
                "Assessment failed for location=%r, activity=%r",
                location,
                activity
            )

            self.event_queue.put(
                ("error", self.friendly_error_message(error))
            )

    # ========================================================
    # ERROR HANDLING
    # ========================================================

    @staticmethod
    def friendly_error_message(error: Exception) -> str:
        """Convert technical errors into readable messages."""

        name = error.__class__.__name__.lower()

        message = str(error).strip()

        if isinstance(error, (ConnectionError, TimeoutError)) or "timeout" in name:

            return (
                "The weather service could not be reached. "
                "Check your internet connection and try again."
            )

        if "connection" in name or "network" in name:

            return (
                "A network problem prevented the forecast "
                "from loading. Check your connection and try again."
            )

        if isinstance(error, ValueError) and message:
            return message

        if message:
            return (
                f"The assessment could not be completed: {message}"
            )

        return (
            "The assessment could not be completed "
            "because an unexpected error occurred."
        )

    # ========================================================
    # GUI EVENT PROCESSING
    # ========================================================

    def process_events(self) -> None:
        """Display worker results safely on the Tkinter main thread."""

        try:

            while True:

                event_type, payload = self.event_queue.get_nowait()

                status_message = "Ready"

                try:

                    if event_type == "success":

                        self.last_result = payload

                        self.view.display_results(payload)

                        status_message = "Assessment complete."

                        self.save_search_history(payload)

                    elif event_type == "error":

                        self.view.show_error(str(payload))

                        status_message = "Assessment was not completed."

                except Exception:

                    logger.exception(
                        "The GUI could not display an assessment event."
                    )

                    self.view.show_error(
                        "The result was calculated, but the interface "
                        "could not display it correctly."
                    )

                    status_message = "Error displaying assessment results."

                finally:

                    self.is_busy = False

                    self.view.set_busy(
                        False,
                        status_message
                    )

        except queue.Empty:
            pass

        finally:

            self.root.after(
                100,
                self.process_events
            )

    # ========================================================
    # SEARCH HISTORY MANAGEMENT
    # ========================================================

    def save_search_history(
        self,
        result: dict[str, Any]
    ) -> None:
        """Save successful assessments to local search history."""

        try:

            history = self.storage.load_data(
                "search_history.json"
            )

            if not isinstance(history, list):
                history = []

            history.append(result)

            saved = self.storage.save_data(
                "search_history.json",
                history[-50:]
            )

            if not saved:

                logger.error(
                    "Search history could not be saved."
                )

                self.view.set_status(
                    "Assessment complete, but search history "
                    "could not be saved."
                )

        except Exception:

            logger.exception(
                "Could not update search history."
            )

            self.view.set_status(
                "Assessment complete, but search history "
                "could not be saved."
            )

    # ========================================================
    # SAVE ACTIVITY PLAN
    # ========================================================

    def save_latest_plan(self) -> None:
        """Save the most recent assessment."""

        if self.last_result is None:

            self.view.show_error(
                "There is no completed assessment to save yet."
            )

            return

        try:

            plans = self.storage.load_data(
                "saved_plans.json"
            )

            if not isinstance(plans, list):
                plans = []

            plans.append(self.last_result)

            saved = self.storage.save_data(
                "saved_plans.json",
                plans
            )

            if saved:

                self.view.set_status(
                    "Plan saved successfully."
                )

            else:

                self.view.show_error(
                    "The plan could not be saved. "
                    "Please check the storage folder."
                )

        except Exception as error:

            logger.exception(
                "Could not save the current plan."
            )

            self.view.show_error(
                f"The plan could not be saved: {error}"
            )


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

def main() -> None:
    """Create the application window and start Tkinter."""

    root = tk.Tk()

    WeatherActivityPlannerApp(root)

    root.mainloop()


if __name__ == "__main__":
    main()
