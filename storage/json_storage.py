import json
from pathlib import Path


class JSONStorage:
    """Handles saving and loading application data using JSON."""

    def __init__(self, storage_dir=None):
        if storage_dir is None:
            storage_dir = Path(__file__).resolve().parent

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_data(self, filename, data):
        file_path = self.storage_dir / filename

        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

        return True

    def load_data(self, filename):
        file_path = self.storage_dir / filename

        if not file_path.exists():
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return json.load(file)

        except json.JSONDecodeError:
            return []

    def delete_data(self, filename):
        file_path = self.storage_dir / filename

        if file_path.exists():
            file_path.unlink()
            return True

        return False
