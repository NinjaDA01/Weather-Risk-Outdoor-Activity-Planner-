# Import the json module to handle JSON data.
import json

# Import Path to help us manage file and folder locations.
from pathlib import Path

# Import Any to provide flexible type annotations for JSON data.
from typing import Any


# Create a class responsible for saving and retrieving application data.
class JSONStorage:

    # Constructor: runs automatically when an object is created.
    # data_dir specifies the folder where our JSON files will be stored.
    def _init_(self, data_dir: str = "data") -> None:

        # Store the data folder path as an instance attribute.
        self.data_dir: Path = Path(data_dir)

        # Create the folder if it does not already exist.
        # parents=True creates missing parent folders.
        # exist_ok=True prevents errors if the folder already exists.
    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir: Path = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
       
    # Method for saving information into a JSON file.
    # filename is the name of the file.
    # data is the information we want to save.
    def save_data(self, filename: str, data: Any) -> bool:

        # Combine the folder path and filename.
        file_path: Path = self.data_dir / filename

        # Attempt to save the information.
        try:

            # Open the file in write mode using UTF-8 encoding.
            with open(file_path, "w", encoding="utf-8") as file:

                # Convert Python data into JSON and write it to the file.
                # indent=4 makes the JSON easier to read.
                json.dump(data, file, indent=4)

            # Return True when saving is successful.
            return True

        # Handle file errors and data conversion errors.
        except (OSError, TypeError) as error:

            # Display the error to help with debugging.
            print(f"Error saving data: {error}")

            # Return False because saving was unsuccessful.
            return False

    # Method for retrieving information from a JSON file.
    def load_data(self, filename: str) -> Any:

        # Construct the complete path to the requested file.
        file_path: Path = self.data_dir / filename

        # Check whether the requested file exists.
        if not file_path.exists():

            # Return an empty list if the file is missing.
            return []

        # Attempt to read the JSON file.
        try:

            # Open the file in read mode.
            with open(file_path, "r", encoding="utf-8") as file:

                # Read the JSON data and convert it into Python data.
                return json.load(file)

        # Handle corrupted or incorrectly formatted JSON.
        except json.JSONDecodeError:

            # Display a warning about the corrupted file.
            print(f"Warning: {filename} contains invalid JSON.")

            # Return an empty list instead of crashing.
            return []

        # Handle other file-reading errors.
        except OSError as error:

            # Display the file error.
            print(f"Error loading data: {error}")

            # Return an empty list if loading fails.
            return []


if __name__ == "__main__":
    # 1. Create an instance of JSONStorage (it will create a "data" folder if it doesn't exist)
    storage = JSONStorage(data_dir="data")

    # 2. Test saving some sample data
    sample_data = {
        "project": "GitHub Teamwork",
        "module": "JSONStorage",
        "status": "Ready",
    }
    
    print("Attempting to save data...")
    is_saved = storage.save_data("config.json", sample_data)
    print(f"Save status: {is_saved}\n")

    # 3. Test loading the data back
    print("Attempting to load data...")
    retrieved_data = storage.load_data("config.json")
    print("Loaded data successfully:")
    print(retrieved_data)