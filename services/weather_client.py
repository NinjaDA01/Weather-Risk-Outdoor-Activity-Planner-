
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from gui.weather_view import WeatherView
from gui.activity_view import ActivityView

def format_saved_plan(plan):
    """Convert a saved activity plan into readable information."""

    if not isinstance(plan, dict):
        return "Invalid saved plan."

    weather = plan.get("weather", {})
    risk = plan.get("risk", {})
    best = plan.get("best_time", {})
    checklist = plan.get("checklist", {})

    if not isinstance(weather, dict):
        weather = {}

    if not isinstance(risk, dict):
        risk = {"level": str(risk)}

    if not isinstance(best, dict):
        best = {}

    if not isinstance(checklist, dict):
        checklist = {}

    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Heavy drizzle",
        61: "Light rain",
        63: "Moderate rain",
        65: "Heavy rain",
        80: "Rain showers",
        81: "Moderate rain showers",
        82: "Heavy rain showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Severe thunderstorm"
    }

    lines = []

    def section(title):
        lines.append("")
        lines.append(title.upper())
        lines.append("-" * 45)

    def add_list(title, items):
        if isinstance(items, str):
            items = [items]

        if not isinstance(items, (list, tuple)):
            return

        if items:
            lines.append(f"\n{title}:")

            for item in items:
                lines.append(f"  • {item}")

    def readable_date(value):
        if not value:
            return "Not available"

        try:
            return datetime.fromisoformat(
                str(value)
            ).strftime("%A, %d %B %Y at %I:%M %p")

        except (ValueError, TypeError):
            return str(value)

    # GENERAL INFORMATION
    lines.append("SAVED ACTIVITY PLAN")
    lines.append("=" * 45)
    lines.append(f"Location: {plan.get('location', 'N/A')}")
    lines.append(f"Activity: {plan.get('activity', 'N/A')}")

    # WEATHER CONDITIONS
    section("WEATHER CONDITIONS")

    code = weather.get("weather_code")

    try:
        code = int(code)
    except (ValueError, TypeError):
        pass

    description = weather_codes.get(
        code,
        "Weather information unavailable"
    )

    lines.append(f"Conditions: {description}")
    lines.append(f"Temperature: {weather.get('temperature', 'N/A')} °C")
    lines.append(f"Feels Like: {weather.get('feels_like', 'N/A')} °C")
    lines.append(f"Humidity: {weather.get('humidity', 'N/A')}%")
    lines.append(f"Wind Speed: {weather.get('wind_speed', 'N/A')} km/h")
    lines.append(f"Precipitation: {weather.get('precipitation', 'N/A')} mm")

    # RISK ASSESSMENT
    section("RISK ASSESSMENT")

    lines.append(f"Risk Level: {risk.get('level', 'N/A')}")
    lines.append(f"Risk Score: {risk.get('score', 'N/A')}/100")

    add_list("Assessment Reasons", risk.get("reasons", []))
    add_list("Warnings", risk.get("warnings", []))

    # RECOMMENDED TIME
    section("RECOMMENDED TIME")

    lines.append(f"Activity: {best.get('activity', 'N/A')}")
    lines.append(
        f"Best Time: {readable_date(best.get('best_time'))}"
    )
    lines.append(f"Rating: {best.get('rating', 'N/A')}")
    lines.append(f"Score: {best.get('score', 'N/A')}/100")
    lines.append(f"Risk Level: {best.get('risk_level', 'N/A')}")

    add_list("Reasons", best.get("reasons", []))
    add_list("Warnings", best.get("warnings", []))
    add_list("Activity Advice", best.get("advice", []))

    # ALTERNATIVE TIMES
    alternatives = best.get("alternatives", [])

    if isinstance(alternatives, list) and alternatives:
        section("ALTERNATIVE TIMES")

        for index, alternative in enumerate(alternatives, start=1):

            if not isinstance(alternative, dict):
                continue

            lines.append(
                f"{index}. {readable_date(alternative.get('time'))}"
            )

            lines.append(
                f"   Rating: {alternative.get('rating', 'N/A')}"
            )

            lines.append(
                f"   Score: {alternative.get('score', 'N/A')}/100"
            )

    # PACKING CHECKLIST
    section("PACKING CHECKLIST")

    add_list("Essentials", checklist.get("essentials", []))
    add_list("Weather Gear", checklist.get("weather_gear", []))
    add_list("Safety Instructions", checklist.get("safety", []))

    lines.append(
        f"\nWeather Summary: {checklist.get('summary', 'N/A')}"
    )

    # AI EXPLANATION
    section("AI WEATHER EXPLANATION")

    explanation = plan.get(
        "explanation",
        "No explanation available."
    )

    lines.append(str(explanation).replace("**", ""))

    lines.append("\n" + "=" * 45)
    lines.append("END OF SAVED PLAN")

    return "\n".join(lines)

class MainWindow:

    def __init__(
        self,
        root,
        on_assess=None,
        on_save=None,
        on_view_saved=None
    ):

        self.root = root
        self.on_assess = on_assess
        self.on_save = on_save
        self.on_view_saved = on_view_saved

        self.root.title("Weather Risk & Outdoor Activity Planner")
        self.root.geometry("900x650")
        self.root.minsize(850, 600)
        self.root.config(bg="#f0f4f8")

        # 1. TITLE
        title = tk.Label(
            root,
            text="Weather Risk & Outdoor Activity Planner",
            font=("Arial", 16, "bold"),
            bg="#f0f4f8"
        )
        title.pack(pady=10)

        # 2. LOCATION AND ACTIVITY INPUTS
        input_frame = tk.LabelFrame(
            root,
            text="Enter Location and Activity",
            bg="white",
            padx=10,
            pady=10
        )
        input_frame.pack(fill="x", padx=20)

        tk.Label(
            input_frame,
            text="Location:",
            bg="white"
        ).grid(row=0, column=0)

        self.location_entry = tk.Entry(
            input_frame,
            width=25
        )
        self.location_entry.grid(row=0, column=1, padx=10)
        self.location_entry.insert(0, "Abuja")

        tk.Label(
            input_frame,
            text="Activity:",
            bg="white"
        ).grid(row=0, column=2, padx=(20, 0))

        self.activity_var = tk.StringVar()

        self.activity_combo = ttk.Combobox(
            input_frame,
            textvariable=self.activity_var,
            width=15,
            state="readonly"
        )

        self.activity_combo["values"] = (
            "football",
            "jogging",
            "farming",
            "travelling",
            "picnic",
            "walking",
            "hiking",
            "cycling"
        )

        self.activity_combo.current(0)
        self.activity_combo.grid(row=0, column=3, padx=10)

        # 3. BUTTONS
        btn_frame = tk.Frame(root, bg="#f0f4f8")
        btn_frame.pack(pady=10)

        self.assess_button = tk.Button(
            btn_frame,
            text="Assess Activity",
            bg="#3498db",
            fg="white",
            command=self.request_assessment,
            width=16
        )
        self.assess_button.pack(side="left", padx=5)

        self.save_button = tk.Button(
            btn_frame,
            text="Save Plan",
            bg="#27ae60",
            fg="white",
            command=self.request_save,
            width=13
        )
        self.save_button.pack(side="left", padx=5)

        self.saved_button = tk.Button(
            btn_frame,
            text="View Saved Plans",
            bg="#34495e",
            fg="white",
            command=self.request_view_saved,
            width=17
        )
        self.saved_button.pack(side="left", padx=5)

        # 4. DISPLAY SECTIONS
        display_frame = tk.Frame(
            root,
            bg="#f0f4f8"
        )
        display_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=10
        )

        self.weather_view = WeatherView(display_frame)
        self.weather_view.pack(
            side="left",
            fill="both",
            expand=True,
            padx=5
        )

        self.activity_view = ActivityView(display_frame)
        self.activity_view.pack(
            side="left",
            fill="both",
            expand=True,
            padx=5
        )

        # 5. STATUS LABEL
        self.status_label = tk.Label(
            root,
            text="Ready",
            bg="#f0f4f8",
            font=("Arial", 9)
        )
        self.status_label.pack(
            side="bottom",
            pady=5
        )

    # ----------------------------------------
    # BUTTON CALLBACK METHODS
    # ----------------------------------------

    def request_assessment(self):

        location = self.location_entry.get().strip()
        activity = self.activity_var.get().strip()

        if not location:
            messagebox.showwarning(
                "Missing Location",
                "Please enter a location."
            )
            return

        if not activity:
            messagebox.showwarning(
                "Missing Activity",
                "Please select an activity."
            )
            return

        if self.on_assess:
            self.on_assess(location, activity)

    def request_save(self):

        if self.on_save:
            self.on_save()

    def request_view_saved(self):

        if self.on_view_saved:
            self.on_view_saved()

    # ----------------------------------------
    # SAVED PLANS WINDOW
    # ----------------------------------------

    def show_saved_plans(self, plans):

        window = tk.Toplevel(self.root)
        window.title("Saved Activity Plans")
        window.geometry("850x650")
        window.minsize(650, 450)
        window.config(bg="#f0f4f8")

        tk.Label(
            window,
            text="Your Saved Activity Plans",
            font=("Arial", 16, "bold"),
            bg="#f0f4f8"
        ).pack(pady=12)

        if not plans:
            tk.Label(
                window,
                text="No saved plans found.\nComplete an assessment and click Save Plan.",
                font=("Arial", 11),
                bg="#f0f4f8",
                justify="center"
            ).pack(expand=True)

            return

        # MAIN CONTENT
        content = tk.Frame(window, bg="#f0f4f8")
        content.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=10
        )

        # SAVED PLANS TABLE
        table_frame = tk.Frame(content)
        table_frame.pack(
            fill="both",
            expand=True
        )

        columns = ("location", "activity", "risk")

        tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=7
        )

        tree.heading("location", text="Location")
        tree.heading("activity", text="Activity")
        tree.heading("risk", text="Risk Level")

        tree.column("location", width=250)
        tree.column("activity", width=200)
        tree.column("risk", width=150)

        tree_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=tree.yview
        )

        tree.configure(
            yscrollcommand=tree_scrollbar.set
        )

        tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        tree_scrollbar.pack(
            side="right",
            fill="y"
        )

        # INSERT SAVED RECORDS
        for index, plan in enumerate(plans):

            if not isinstance(plan, dict):
                continue

            location = plan.get("location", "Unknown")
            activity = plan.get("activity", "Unknown")

            risk = plan.get("risk", {})

            if isinstance(risk, dict):
                risk_level = risk.get("level", "Unknown")
            else:
                risk_level = str(risk)

            tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    location,
                    activity,
                    risk_level
                )
            )

        # DETAILS SECTION
        tk.Label(
            content,
            text="Selected Plan Details",
            font=("Arial", 11, "bold"),
            bg="#f0f4f8"
        ).pack(
            anchor="w",
            pady=(12, 5)
        )

        details_frame = tk.Frame(content)
        details_frame.pack(
            fill="both",
            expand=True
        )

        details_scrollbar = ttk.Scrollbar(
            details_frame,
            orient="vertical"
        )

        details = tk.Text(
            details_frame,
            height=12,
            wrap="word",
            font=("Consolas", 9),
            yscrollcommand=details_scrollbar.set
        )

        details_scrollbar.config(
            command=details.yview
        )

        details.pack(
            side="left",
            fill="both",
            expand=True
        )

        details_scrollbar.pack(
            side="right",
            fill="y"
        )

        details.insert(
            "1.0",
            "Select a saved plan above to view its full details."
        )

        details.config(state="disabled")

        # DISPLAY SELECTED PLAN
        def display_selected_plan(event=None):

            selection = tree.selection()

            if not selection:
                return

            index = int(selection[0])
            selected_plan = plans[index]

            readable_text = format_saved_plan(
                selected_plan
            )

            details.config(state="normal")
            details.delete("1.0", tk.END)
            details.insert("1.0", readable_text)
            details.config(state="disabled")

        # IMPORTANT: CONNECT THE SELECTION EVENT
        tree.bind(
            "<<TreeviewSelect>>",
            display_selected_plan
        )

        # CLOSE BUTTON
        tk.Button(
            window,
            text="Close",
            command=window.destroy,
            bg="#34495e",
            fg="white",
            width=12
        ).pack(pady=10)

    # ----------------------------------------
    # STATUS AND ERROR METHODS
    # ----------------------------------------

    def set_busy(self, busy, message=""):

        self.status_label.config(text=message)

        if busy:
            self.assess_button.config(state="disabled")
        else:
            self.assess_button.config(state="normal")

    def set_status(self, message):

        self.status_label.config(text=message)

    def show_error(self, message):

        messagebox.showerror(
            "Weather Planner",
            message
        )

    # ----------------------------------------
    # DISPLAY ASSESSMENT RESULTS
    # ----------------------------------------

    def display_results(self, result):

        weather = result.get("weather", {})
        risk = result.get("risk", {})
        best_time = result.get("best_time", {})
        checklist = result.get("checklist", {})

        if not isinstance(weather, dict):
            weather = {}

        if not isinstance(risk, dict):
            risk = {}

        if not isinstance(checklist, dict):
            checklist = {}

        self.weather_view.display_weather(weather)

        if isinstance(best_time, dict):

            recommended_time = best_time.get(
                "best_time",
                "Unavailable"
            )

            if not recommended_time:
                recommended_time = best_time.get(
                    "message",
                    "No suitable time found"
                )

        else:
            recommended_time = str(best_time)

        packing = []

        if isinstance(checklist, dict):

            packing.extend(
                checklist.get("essentials", [])
            )

            packing.extend(
                checklist.get("weather_gear", [])
            )

            packing.extend(
                checklist.get("safety", [])
            )

        elif isinstance(checklist, list):
            packing = checklist

        warnings = risk.get("warnings", [])

        if not isinstance(warnings, list):
            warnings = [str(warnings)]

        checklist_safety = checklist.get(
            "safety", []
        )

        if not isinstance(checklist_safety, list):
            checklist_safety = [str(checklist_safety)]

        safety_items = warnings + checklist_safety

        recommendation = {
            "risk": risk.get("level", "Unknown"),
            "best_time": recommended_time,
            "explanation": result.get(
                "explanation",
                "No explanation available."
            ),
            "safety": "\n".join(
                str(item) for item in safety_items
            ),
            "packing": packing
        }

        self.activity_view.display_recommendation(
            recommendation
        )
