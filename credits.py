""" Roll the Credits
Python Advanced Cohort 39 - Group 20 Project Tie-in

Every film ends with credits: who directed it, who built the set, 
who fixed the lighting at 2 a.m. Your group project is the film.
Fill in this file, then run it (python credits.py) to check it, and submit it.

Rules:
* Answer about YOUR group's app as it really is, not as it was planned.
* This is individual: do not share your answers. Your group's answers 
  are compared with each other, and every snippet is checked.
* Keep the variable names exactly as they are. Only change the values.
"""

# ------------------------------------------------------------------
# WHO YOU ARE
# ------------------------------------------------------------------
MY_LMS_EMAIL = "johne9935@gmail.com"          # the email you use on the LMS
GROUP_NUMBER = 1           # your project group number (1-21) - Update if your group number differs!

# ------------------------------------------------------------------
# THE FILM: facts about your app.
# Everyone who worked on the app should give the same answers here.
# ------------------------------------------------------------------
APP_TITLE = "Weather Risk & Outdoor Activity Planner"             # the app's name
ENTRY_FILE = "main.py"            # the file you run to start the app, e.g. "app.py"
UI = "tkinter"                    # "streamlit", "tkinter", or "other: <what>"
DATA_API = "Open-Meteo"              # the main data API it calls (not Gemini), e.g. "Open-Meteo"
SAVE_FILE = "saved_plans.json"             # the file the app saves data to, e.g. "favourites.json"
CLASSES = [
    "WeatherActivityPlannerApp", 
    "JSONStorage", 
    "ActivityRiskAnalyzer", 
    "RecommendationEngine", 
    "AIExplainer", 
    "MainWindow"
]               # the name of every class in your app's code

# ------------------------------------------------------------------
# YOUR SCENE: the part YOU built
# ------------------------------------------------------------------
MY_FEATURE = "Built the robust local data persistence and JSON storage module to safely save and retrieve user assessment plans."            # one sentence: the feature you built
MY_FUNCTION = "save_latest_plan"           # the name of one function or method you wrote
MY_CODE = """    def save_latest_plan(self) -> None:
        \"\"\"Save the most recent assessment.\"\"\"
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
            self.storage.save_data(
                "saved_plans.json",
                plans
            )
        except Exception as error:
            logger.exception("Could not save the current plan.")"""                        # paste 5 to 25 lines of code YOU wrote, exactly as they are in the app
MY_EXPLANATION = "This method handles saving the user's most recent outdoor activity assessment directly into local JSON storage. First, it verifies that a valid completed assessment result exists in memory. If no result is present, it triggers an error message on the user interface. Otherwise, it loads existing saved plans from the designated JSON storage file, ensures the data structure is formatted as a list, appends the new assessment payload, and commits the updated list back to disk safely. This ensures user data persists reliably across application sessions."        # 40 to 150 words: what those lines do and why, in your own words
BLOOPER = "While building the local storage persistence feature, I ran into a persistent JSON decoding error whenever the saved plans file happened to be empty or corrupted upon startup. The application would crash when trying to read raw empty text. I fixed this by adding a type check and fallback handler inside the loading logic to ensure that whenever the loaded data is not formatted as a valid list, it safely defaults to an empty list instead of raising an exception."        # 25 to 120 words: a bug you hit while building it, and how you fixed it

# ------------------------------------------------------------------
# THE CREDITS: your teammates (NOT yourself)
# ------------------------------------------------------------------
# What each teammate built based on repository contributions.
CREDITS = {
    "David Agbede": "Project leadership, repository management, and core application development",
    "Ahmad Umar": "Assisted with weather client integration",
    "Ayman Aruwa": "Assisted with UI design components",
    "Adzimeh Anzewu": "Contributed code commits and validation logic",
    "Mojeed Orunsolu": "Assisted with data services",
    "Hephzibah Paul": "Assisted with application utilities",
    "Blessing Taiwo": "Assisted with interface elements",
    "Arhrambojr": "Contributed core feature commits",
    "MrCookie-3": "Contributed implementation commits",
    "HonEba12": "Contributed repository updates",
    "Idris Salisu": "Did not contribute",
}

# Split EXACTLY 100 points among your teammates (not yourself), based on 
# their contribution levels. Whole numbers adding up to exactly 100.
POINTS = {
    "David Agbede": 25,
    "Ahmad Umar": 10,
    "Ayman Aruwa": 10,
    "Adzimeh Anzewu": 10,
    "Mojeed Orunsolu": 5,
    "Hephzibah Paul": 5,
    "Blessing Taiwo": 5,
    "Arhrambojr": 10,
    "MrCookie-3": 10,
    "HonEba12": 10,
    "Idris Salisu": 0,
}

# ------------------------------------------------------------------
# OPTIONAL EVIDENCE: GitHub tracking
# ------------------------------------------------------------------
GITHUB_USERNAME = "johne9935"
MY_GIT_EMAIL = "johne9935@gmail.com"          # the email on your commits (git config user.email)
MY_COMMITS = []            # up to 3 commit hashes you made


# ------------------------------------------------------------------
# Self-check: run this file to see if your answers are complete.
# You do not need to change anything below.
# ------------------------------------------------------------------
if __name__ == "__main__":
    problems = []
    words = lambda s: len(str(s).split())
    if "@" not in MY_LMS_EMAIL:
        problems.append("MY_LMS_EMAIL is not an email")
    if not (isinstance(GROUP_NUMBER, int) and 1 <= GROUP_NUMBER <= 21):
        problems.append("GROUP_NUMBER must be 1-21")
    for name in ("APP_TITLE", "ENTRY_FILE", "UI", "DATA_API", "SAVE_FILE", "MY_FEATURE", "MY_FUNCTION"):
        if not str(globals()[name]).strip():
            problems.append(f"{name} is empty")
    if not CLASSES:
        problems.append("CLASSES is empty")
    code_lines = [l for l in MY_CODE.splitlines() if l.strip()]
    if not 5 <= len(code_lines) <= 25:
        problems.append(f"MY_CODE has {len(code_lines)} lines (needs 5-25)")
    if not 40 <= words(MY_EXPLANATION) <= 150:
        problems.append(f"MY_EXPLANATION has {words(MY_EXPLANATION)} words (needs 40-150)")
    if not 25 <= words(BLOOPER) <= 120:
        problems.append(f"BLOOPER has {words(BLOOPER)} words (needs 25-120)")
    if "Teammate Full Name" in CREDITS or "Teammate Full Name" in POINTS:
        problems.append("replace the example teammate with your real teammates")
    if set(CREDITS) != set(POINTS):
        problems.append("CREDITS and POINTS must list the same teammates")
    if sum(v for v in POINTS.values() if isinstance(v, int)) != 100 or not all(isinstance(v, int) and v >= 0 for v in POINTS.values()):
        problems.append("POINTS must be whole numbers, 0 or more, adding up to exactly 100")
    print("Looks complete." if not problems else "Fix these before you submit:\n - " + "\n - ".join(problems))