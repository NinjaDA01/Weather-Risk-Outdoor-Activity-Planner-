# Import the json module to handle JSON data.
import json

# Import Path to manage file and folder locations.
from pathlib import Path

# Import Any for flexible type annotations.
from typing import Any


class JSONStorage:

    # Constructor: runs automatically when an object is created.
    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir: Path = Path(data_dir)

        # Create the storage folder if it does not exist.
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # Save information into a JSON file.
    def save_data(self, filename: str, data: Any) -> bool:

        file_path: Path = self.data_dir / filename

        try:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)

            return True

        except (OSError, TypeError, ValueError) as error:
            print(f"Error saving data: {error}")
            return False

    # Retrieve information from a JSON file.
    def load_data(self, filename: str) -> Any:

        file_path: Path = self.data_dir / filename

        # Return an empty list if the file does not exist.
        if not file_path.exists():
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)

        except json.JSONDecodeError:
            print(f"Warning: {filename} contains invalid JSON.")
            return []

        except OSError as error:
            print(f"Error loading data: {error}")
            return []


# Test the storage module independently.
if __name__ == "__main__":

    storage = JSONStorage(data_dir="data")

    sample_data = {
        "project": "Weather Risk & Outdoor Activity Planner",
        "module": "JSONStorage",
        "status": "Ready"
    }

    print("Attempting to save data...")

    is_saved = storage.save_data("config.json", sample_data)

    print(f"Save status: {is_saved}")

    print("\nAttempting to load data...")

    retrieved_data = storage.load_data("config.json")

    print("Loaded data successfully:")
    print(retrieved_data)
