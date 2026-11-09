import tkinter as tk
from tkinter import ttk, messagebox
import sys, os

# This lets us use main.py from your teammates


from gui.weather_view import WeatherView
from gui.activity_view import ActivityView



class MainWindow:
    def __init__(self, root, on_assess=None, on_save=None):
        self.root = root
        self.on_assess = on_assess
        self.on_save = on_save
        self.root.title("Weather Activity Planner")
        self.root.geometry("900x650")
        self.root.config(bg="#f0f4f8")

        # 1. TITLE
        tk.Label(root, text="Weather Activity Planner", font=("Arial", 16, "bold"), bg="#f0f4f8").pack(pady=10)

        # 2. INPUT FIELD + ACTIVITY SELECTION
        input_frame = tk.LabelFrame(root, text="Enter Location and Activity", bg="white", padx=10, pady=10)
        input_frame.pack(fill="x", padx=20)

        tk.Label(input_frame, text="Location:", bg="white").grid(row=0, column=0)
        self.location_entry = tk.Entry(input_frame, width=25)
        self.location_entry.grid(row=0, column=1, padx=10)
        self.location_entry.insert(0, "Abuja")

        tk.Label(input_frame, text="Activity:", bg="white").grid(row=0, column=2, padx=(20,0))
        self.activity_var = tk.StringVar()
        self.activity_combo = ttk.Combobox(input_frame, textvariable=self.activity_var, width=15, state="readonly")
        self.activity_combo['values'] = (
          "football",
          "jogging",
          "farming",
          "travelling",
          "picnic"
        )
     
        self.activity_combo.current(0)
        self.activity_combo.grid(row=0, column=3, padx=10)

        # 3. BUTTONS
        btn_frame = tk.Frame(root, bg="#f0f4f8")
        btn_frame.pack(pady=10)

           tk.Button(
              btn_frame,
              text="Assess Activity",
              b.g="#3498db",
              fg="white",
              command=self.request_assessment,
              width=18
            ).pack(side="left", padx=10)

            tk.Button(
               btn_frame,
               text="Save Plan",
               bg="#27ae60",
               fg="white",
               command=self.request_save,
               width=15
            ).pack(side="left", padx=10) 

        # 4. DISPLAY SECTIONS
        display_frame = tk.Frame(root, bg="#f0f4f8")
        display_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self.status_label = tk.Label(
            root,
            text="Ready",
            bg="#f0f4f8",
            font=("Arial", 9)
        )
        
self.status_label.pack(side="bottom", pady=5)

        self.weather_view = WeatherView(display_frame)
        self.weather_view.pack(side="left", fill="both", expand=True, padx=5)

        self.activity_view = ActivityView(display_frame)
        self.activity_view.pack(side="left", fill="both", expand=True, padx=5)

class MainWindow:

    def __init__(self, root, on_assess=None, on_save=None):

        self.root = root
        self.on_assess = on_assess
        self.on_save = on_save

        # Your existing GUI setup goes here

        self.weather_view = WeatherView(display_frame)
        self.activity_view = ActivityView(display_frame)

    # ADD THE NEW METHODS HERE

    def request_assessment(self):
        location = self.location_entry.get().strip()
        activity = self.activity_var.get().strip()

        if self.on_assess:
            self.on_assess(location, activity)

    def request_save(self):
        if self.on_save:
            self.on_save()

    def set_busy(self, busy, message=""):
        self.status_label.config(text=message)

    def set_status(self, message):
        self.status_label.config(text=message)

    def show_error(self, message):
        messagebox.showerror("Weather Planner", message)

    def display_results(self, result):
        weather = result.get("weather", {})
        risk = result.get("risk", {})
        best_time = result.get("best_time", {})
        checklist = result.get("checklist", {})

        self.weather_view.display_weather(weather)

        if isinstance(best_time, dict):
            recommended_time = best_time.get(
                "best_time", "Unavailable"
            )
        else:
            recommended_time = str(best_time)

        if isinstance(checklist, dict):
            packing = checklist.get("essentials", [])
        else:
            packing = checklist if isinstance(checklist, list) else []

        recommendation = {
            "risk": risk.get("level", "Unknown"),
            "best_time": recommended_time,
            "explanation": result.get("explanation", ""),
            "safety": "\n".join(risk.get("warnings", [])),
            "packing": packing
        }

        self.activity_view.display_recommendation(recommendation)
    def check_weather(self):
        loc = self.location_entry.get()
        if not loc:
            messagebox.showwarning("Error", "Please enter location")
            return
        if backend and hasattr(backend, 'get_weather_data'):
            data = backend.get_weather_data(loc)
            self.weather_view.display_weather(data)
        else:
            # Demo if main.py not ready
            demo = {"location": loc, "temp": "30°C", "condition": "Sunny", "humidity": "60%", "wind": "10 km/h"}
            self.weather_view.display_weather(demo)

    def get_recommendation(self):
        loc = self.location_entry.get()
        act = self.activity_var.get()
        if backend and hasattr(backend, 'get_activity_recommendation'):
            result = backend.get_activity_recommendation(loc, act)
            self.activity_view.display_recommendation(result)
        else:
            demo = {"risk": "Low Risk", "best_time": "Morning 7-10 AM", "explanation": f"Good for {act} in {loc}", "safety": "Stay hydrated", "packing": ["Water", "Cap", "Sunscreen"]}
            self.activity_view.display_recommendation(demo)

