# ============================================================
# WEATHER RISK & OUTDOOR ACTIVITY PLANNER
# MODULE: INPUT VALIDATION (validator.py)
# ============================================================

from datetime import date


# ============================================================
# 1. LOCATION VALIDATION
# ============================================================

def validate_location(location: str) -> str:
    """
    Validate and clean a location entered by the user.

    Supports locations worldwide.

    Returns:
        str: A cleaned location string.

    Raises:
        ValueError: If the location is invalid.
    """

    if not isinstance(location, str):
        raise ValueError("Location must be entered as text.")

    cleaned_location = location.strip()

    if not cleaned_location:
        raise ValueError("Location cannot be empty.")

    if len(cleaned_location) < 2:
        raise ValueError("Location must contain at least 2 characters.")

    if len(cleaned_location) > 100:
        raise ValueError("Location cannot exceed 100 characters.")

    return cleaned_location


# ============================================================
# 2. DATE VALIDATION
# ============================================================

def validate_date(date_text: str) -> str:
    """
    Validate a date supplied by the user.

    Required format: YYYY-MM-DD

    Returns:
        str: The validated date.

    Raises:
        ValueError: If the date is invalid.
    """

    if not isinstance(date_text, str):
        raise ValueError("Date must be entered as text.")

    cleaned_date = date_text.strip()

    if not cleaned_date:
        raise ValueError("Date cannot be empty.")

    try:
        parsed_date = date.fromisoformat(cleaned_date)

        if parsed_date.isoformat() != cleaned_date:
            raise ValueError

    except ValueError as error:
        raise ValueError(
            "Invalid date. Please enter a valid date "
            "in YYYY-MM-DD format (e.g. 2026-11-09)."
        ) from error

    return cleaned_date


# ============================================================
# 3. TESTING THE VALIDATION FUNCTIONS
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("WEATHER RISK & OUTDOOR ACTIVITY PLANNER")
    print("RUNNING INPUT VALIDATION TESTS...")
    print("=" * 60)

    # Test valid location.
    print("\n[Test 1] Valid location...")

    try:
        result = validate_location(" Abuja ")
        print(f"SUCCESS: {result}")

    except ValueError as error:
        print(f"FAILED: {error}")

    # Test valid date.
    print("\n[Test 2] Valid date...")

    try:
        result = validate_date("2026-11-09")
        print(f"SUCCESS: {result}")

    except ValueError as error:
        print(f"FAILED: {error}")

    # Test invalid location.
    print("\n[Test 3] Empty location...")

    try:
        validate_location("   ")
        print("FAILED: Expected an error.")

    except ValueError as error:
        print(f"SUCCESS: {error}")

    # Test invalid date.
    print("\n[Test 4] Invalid date...")

    try:
        validate_date("2026-02-30")
        print("FAILED: Expected an error.")

    except ValueError as error:
        print(f"SUCCESS: {error}")

    print("\n" + "=" * 60)
    print("VALIDATION TESTS COMPLETED.")
    print("=" * 60)
