from pathlib import Path

current_file_path = Path(__file__).resolve()

BASE_DIR = current_file_path.parents[2]

# print(BASE_DIR)