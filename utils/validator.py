# ============================================================
# WEATHER RISK & OUTDOOR ACTIVITY PLANNER
# MODULE: INPUT VALIDATION (validators.py)
# ============================================================
# Description: This module handles all user input validation for 
# locations and dates, ensuring clean data before API calls or 
# risk assessment logic is executed.
# ============================================================

from datetime import date


# ============================================================
# 1. LOCATION VALIDATION
# ============================================================

def validate_location(location: str) -> str:
    """
    Validate and clean a location entered by the user.

    The application supports locations worldwide.
    This function does not restrict locations to any country.

    Args:
        location (str): The location entered by the user.

    Returns:
        str: A cleaned and stripped location string.

    Raises:
        ValueError: If the location is empty, not text, or too short.
    """
    # Ensure that the input is provided as a string.
    if not isinstance(location, str):
        raise ValueError("Location must be entered as text.")

    # Remove unnecessary whitespace from the beginning and end.
    cleaned_location = location.strip()

    # Check whether the location field is empty after stripping.
    if not cleaned_location:
        raise ValueError("Location cannot be empty.")

    # Check that the location has at least two characters.
    if len(cleaned_location) < 2:
        raise ValueError("Location must contain at least 2 characters.")

    # Return the validated and cleaned location.
    return cleaned_location


# ============================================================
# 2. DATE VALIDATION
# ============================================================

def validate_date(date_text: str) -> str:
    """
    Validate a date supplied by the user for activity planning.

    The required format is strictly YYYY-MM-DD.

    Args:
        date_text (str): The date entered by the user.

    Returns:
        str: The validated date string.

    Raises:
        ValueError: If the date is invalid, empty, or incorrectly formatted.
    """
    # Ensure that the date input is provided as a string.
    if not isinstance(date_text, str):
        raise ValueError("Date must be entered as text.")

    # Remove unnecessary whitespace.
    cleaned_date = date_text.strip()

    # Check whether the date field is empty.
    if not cleaned_date:
        raise ValueError("Date cannot be empty.")

    try:
        # Parse the date using Python's ISO format.
        # This automatically catches non-existent dates (e.g., February 30th).
        parsed_date = date.fromisoformat(cleaned_date)

        # Double-check that the parsed date matches the exact string format.
        if parsed_date.isoformat() != cleaned_date:
            raise ValueError("Invalid date format. Please use YYYY-MM-DD.")

    except ValueError as error:
        # Wrap any parsing error into a clear, user-friendly message.
        raise ValueError(
            "Invalid date. Please enter a valid date "
            "in YYYY-MM-DD format (e.g. 2026-11-06)."
        ) from error

    # Return the validated date string.
    return cleaned_date


# ============================================================
# 3. TESTING THE VALIDATION FUNCTIONS
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("WEATHER RISK & OUTDOOR ACTIVITY PLANNER")
    print("RUNNING INPUT VALIDATION TESTS...")
    print("=" * 60)

    # --------------------------------------------------------
    # Test 1: Valid Location Test
    # --------------------------------------------------------
    print("\n[Test 1] Testing valid location (Abuja)...")
    try:
        result_location = validate_location("Abuja")
        print(f" SUCCESS -> Valid location accepted: '{result_location}'")
    except ValueError as err:
        print(f" FAILED -> Unexpected error: {err}")

    # --------------------------------------------------------
    # Test 2: Valid Date Test
    # --------------------------------------------------------
    print("\n[Test 2] Testing valid date (2026-11-06)...")
    try:
        result_date = validate_date("2026-11-06")
        print(f" SUCCESS -> Valid date accepted: '{result_date}'")
    except ValueError as err:
        print(f" FAILED -> Unexpected error: {err}")

    # --------------------------------------------------------
    # Test 3: Invalid Location Test (Empty String)
    # --------------------------------------------------------
    print("\n[Test 3] Testing empty location error handling...")
    try:
        validate_location("   ")
        print(" FAILED -> Should have raised an error for empty location.")
    except ValueError as err:
        print(f" SUCCESS -> Correctly caught expected error: {err}")

    # --------------------------------------------------------
    # Test 4: Invalid Date Test (Non-existent Day)
    # --------------------------------------------------------
    print("\n[Test 4] Testing invalid date error handling (2026-02-30)...")
    try:
        validate_date("2026-02-30")
        print(" FAILED -> Should have raised an error for non-existent date.")
    except ValueError as err:
        print(f" SUCCESS -> Correctly caught expected error: {err}")

    print("\n" + "=" * 60)
    print("ALL INPUT VALIDATION TESTS COMPLETED SUCCESSFULLY.")
    print("=" * 60)
    