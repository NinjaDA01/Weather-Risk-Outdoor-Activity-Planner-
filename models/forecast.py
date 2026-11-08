
class Forecast:

    def __init__(self, location, latitude, longitude,
                 temperature, humidity, wind_speed, precipitation):

        # Location details
        self.location = location
        self.latitude = latitude
        self.longitude = longitude

        # Weather details
        self.temperature = temperature
        self.humidity = humidity
        self.wind_speed = wind_speed
        self.precipitation = precipitation

        # Hourly forecast details
        self.forecast_times = []
        self.hourly_temperatures = []
        self.hourly_precipitation = []
        self.hourly_wind_speeds = []
