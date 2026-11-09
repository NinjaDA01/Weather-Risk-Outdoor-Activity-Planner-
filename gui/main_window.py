import tkinter as tk
from tkinter import ttk, messagebox

from gui.weather_view import WeatherView
from gui.activity_view import ActivityView


class MainWindow:

    def __init__(self, root, on_assess=None, on_save=None):
        self.root = root
        self.on_assess = on_assess
        self.on_save = on_save

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
        btn_frame = tk.Frame(
            root,
            bg="#f0f4f8"
        )
        btn_frame.pack(pady=10)

        self.assess_button = tk.Button(
            btn_frame,
            text="Assess Activity",
            bg="#3498db",
            fg="white",
            command=self.request_assessment,
            width=18
        )
        self.assess_button.pack(side="left", padx=10)

        self.save_button = tk.Button(
            btn_frame,
            text="Save Plan",
            bg="#27ae60",
            fg="white",
            command=self.request_save,
            width=15
        )
        self.save_button.pack(side="left", padx=10)

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

        if self.on_assess:
            self.on_assess(location, activity)

    def request_save(self):
        if self.on_save:
            self.on_save()

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

        # Display weather information
        self.weather_view.display_weather(weather)

        # Extract recommended time
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

        # Extract checklist information
        packing = []

        if isinstance(checklist, dict):
            packing.extend(checklist.get("essentials", []))
            packing.extend(checklist.get("weather_gear", []))
            packing.extend(checklist.get("safety", []))

        elif isinstance(checklist, list):
            packing = checklist

        # Extract risk warnings
        warnings = risk.get("warnings", [])

        if not isinstance(warnings, list):
            warnings = [str(warnings)]

        checklist_safety = (
            checklist.get("safety", [])
            if isinstance(checklist, dict)
            else []
        )

        safety_items = warnings + checklist_safety

        recommendation = {
            "risk": risk.get("level", "Unknown"),
            "best_time": recommended_time,
            "explanation": result.get(
                "explanation",
                "No explanation available."
            ),
            "safety": "\n".join(str(item) for item in safety_items),
            "packing": packing
        }

        self.activity_view.display_recommendation(
            recommendation
        )
