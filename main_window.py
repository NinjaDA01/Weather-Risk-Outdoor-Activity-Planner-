import tkinter as tk
from tkinter import ttk, messagebox
import sys, os

# This lets us use main.py from your teammates
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from gui.weather_view import WeatherView
from gui.activity_view import ActivityView

# Try to import main.py
try:
    import main as backend
except:
    backend = None

class MainWindow:
    def __init__(self, root):
        self.root = root
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
        self.activity_combo['values'] = ("football", "jogging", "farming", "travelling", "picnics")
        self.activity_combo.current(0)
        self.activity_combo.grid(row=0, column=3, padx=10)

        # 3. BUTTONS
        btn_frame = tk.Frame(root, bg="#f0f4f8")
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Check Weather", bg="#3498db", fg="white", command=self.check_weather, width=15).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Get Recommendation", bg="#27ae60", fg="white", command=self.get_recommendation, width=18).pack(side="left", padx=10)

        # 4. DISPLAY SECTIONS
        display_frame = tk.Frame(root, bg="#f0f4f8")
        display_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.weather_view = WeatherView(display_frame)
        self.weather_view.pack(side="left", fill="both", expand=True, padx=5)

        self.activity_view = ActivityView(display_frame)
        self.activity_view.pack(side="left", fill="both", expand=True, padx=5)

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

if __name__ == "__main__":
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()