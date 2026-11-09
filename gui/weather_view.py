import tkinter as tk


class WeatherView(tk.LabelFrame):

    def __init__(self, parent):

        super().__init__(
            parent,
            text="2. Weather Information",
            font=("Arial", 10, "bold"),
            bg="white",
            padx=15,
            pady=10
        )

        self.text = tk.Text(
            self,
            height=15,
            width=35,
            font=("Arial", 10),
            bg="#f9fbfd",
            relief="flat",
            wrap="word"
        )

        self.text.pack(
            fill="both",
            expand=True
        )

        self.text.insert(
            "1.0",
            "Weather information will appear here."
        )

        self.text.config(state="disabled")

    def display_weather(self, data):

        self.text.config(state="normal")
        self.text.delete("1.0", tk.END)

        info = (
            f"Location: {data.get('location', 'Unknown')}\n\n"
            f"Temperature: {data.get('temperature', 'N/A')} °C\n"
            f"Feels Like: {data.get('feels_like', 'N/A')} °C\n"
            f"Humidity: {data.get('humidity', 'N/A')}%\n"
            f"Wind Speed: {data.get('wind_speed', 'N/A')} km/h\n"
            f"Precipitation: {data.get('precipitation', 'N/A')} mm\n"
            f"Weather Code: {data.get('weather_code', 'N/A')}"
        )

        self.text.insert("1.0", info)

        self.text.config(state="disabled")
