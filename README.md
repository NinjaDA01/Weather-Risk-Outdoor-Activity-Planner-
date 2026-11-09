Weather Risk & Outdoor Activity Planner

Project Overview

The Weather Risk & Outdoor Activity Planner is a Python desktop application that helps users determine whether weather conditions are suitable for outdoor activities.

Users can enter a location and select an activity. The application retrieves weather information, evaluates potential risks, and provides recommendations to help users plan their activities safely.

Key Features

- Search for weather information by location.
- Display temperature, humidity, wind speed, and precipitation.
- Assess weather risks for different outdoor activities.
- Classify risk levels as SAFE, MANAGEABLE, RISKY, or AVOID.
- Recommend the best time of day for an activity.
- Generate activity-specific packing checklists.
- Use Google Gemini AI to explain weather risks.
- Save previous searches and activity plans locally.
- Handle invalid inputs, network errors, and API failures.

Supported Activities

- Football
- Jogging
- Farming
- Travelling
- Picnic
- Walking
- Hiking
- Cycling

Technologies Used

- Python: Main programming language.
- Tkinter: Graphical user interface.
- Open-Meteo API: Weather forecast data.
- Google Gemini API: AI-generated risk explanations.
- JSON: Local data storage.
- Requests: API communication.
- Python-dotenv: Environment variable management.
- Pytest: Automated testing.

How to Run the Application

1. Install Python

Ensure Python is installed on your computer.

2. Install Dependencies

Open your terminal in the project directory and run:

pip install -r requirements.txt

3. Configure the Gemini API

Create a ".env" file in the main project directory and add your Gemini API key:

GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=your_available_gemini_model

Replace the placeholders with your actual API credentials.

4. Start the Application

Run:

python main.py

The application window should open.

How to Use

1. Enter the name of a location.
2. Select an outdoor activity.
3. Click Assess Activity.
4. Wait for the application to retrieve weather information and analyse the conditions.
5. View the weather report, risk level, recommended time, explanation, and packing checklist.
6. Click Save Plan to save the assessment.

Running Tests

To run the automated tests, use:

python -m pytest tests/ -v

Important Notes

- An internet connection is required to retrieve weather information and access Gemini AI.
- The Python risk analyzer determines the actual risk level. Gemini AI provides additional explanations and does not override the risk assessment.
- Assessment history and saved plans are stored locally in JSON files.
- The application provides planning guidance and should not replace official weather warnings or emergency advice.

---

Weather Risk & Outdoor Activity Planner
Cohort 39 | Python Advanced | Group 20
