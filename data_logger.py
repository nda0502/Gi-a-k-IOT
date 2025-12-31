import csv
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, "weather_log.csv")
HEADER = ["time", "temp_now", "humidity", "uv"]

def append_weather(temp_now, humidity, uv):
    file_exists = os.path.exists(CSV_FILE)

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(HEADER)

        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            round(float(temp_now), 2),
            round(float(humidity), 2),
            round(float(uv), 2),
        ])
        f.flush()              # ép ghi ra đĩa
        os.fsync(f.fileno())   # chắc chắn ghi xong

    return CSV_FILE
