import re


def validate_location(location):
    """Validate a location entered by the user."""

    if not isinstance(location, str):
        return False

    location = location.strip()

    if len(location) < 2 or len(location) > 100:
        return False

    pattern = r"^[a-zA-Z0-9\s,.'-]+$"

    return bool(re.fullmatch(pattern, location))
