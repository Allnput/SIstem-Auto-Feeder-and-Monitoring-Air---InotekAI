import sqlite3
from contextlib import contextmanager
from datetime import datetime, time
from pathlib import Path

from logic import normalize_schedule_time


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_PATH = BASE_DIR / "inotekai.db"


DEMO_USERS = {
    "12345": "Chyntya",
}


class Database:
    def __init__(self, path=None):
        self.path = Path(path or DEFAULT_DATABASE_PATH)

    @contextmanager
    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def ensure_schema(self):
        statements = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                credential_code TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS water_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                temperature REAL NOT NULL,
                ph REAL NOT NULL,
                water_level TEXT,
                status_label TEXT NOT NULL,
                status_color TEXT NOT NULL,
                sensor_temp_status TEXT NOT NULL DEFAULT 'active',
                sensor_ph_status TEXT NOT NULL DEFAULT 'active',
                feed_percentage INTEGER,
                last_synced TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS feed_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_label TEXT NOT NULL,
                detail TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                is_executed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS feed_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT NOT NULL,
                feed_percentage INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
        ]

        with self._connect() as conn:
            for statement in statements:
                conn.execute(statement)
            conn.executemany(
                """
                INSERT OR IGNORE INTO users (name, credential_code)
                VALUES (?, ?)
                """,
                [(name, code) for code, name in DEMO_USERS.items()],
            )

    def find_user_by_code(self, code):
        query = "SELECT name FROM users WHERE credential_code = ? LIMIT 1"
        with self._connect() as conn:
            cursor = conn.execute(query, (code,))
            row = cursor.fetchone()
        return row[0] if row else None

    def save_water_reading(self, reading, status):
        last_synced = reading.last_synced if isinstance(reading.last_synced, datetime) else datetime.now()
        query = """
            INSERT INTO water_readings (
                temperature, ph, water_level, status_label, status_color,
                sensor_temp_status, sensor_ph_status, feed_percentage, last_synced
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self._connect() as conn:
            conn.execute(
                query,
                (
                    reading.temperature,
                    reading.ph,
                    reading.water_level,
                    status["label"],
                    status["color"],
                    getattr(reading, "sensor_temp_status", "active"),
                    getattr(reading, "sensor_ph_status", "active"),
                    getattr(reading, "feed_percentage", None),
                    self._serialize_datetime(last_synced),
                ),
            )

    def get_water_history(self, limit=20):
        query = """
            SELECT temperature, ph, water_level, status_label, feed_percentage, last_synced
            FROM water_readings
            ORDER BY last_synced DESC
            LIMIT ?
        """
        with self._connect() as conn:
            rows = conn.execute(query, (limit,)).fetchall()
        return [
            (temperature, ph, water_level, status_label, feed_percentage, self._parse_datetime(last_synced))
            for temperature, ph, water_level, status_label, feed_percentage, last_synced in rows
        ]

    def get_today_water_readings(self, day=None):
        day = day or datetime.now().date()
        start = datetime.combine(day, time.min)
        end = datetime.combine(day, time.max)

        query = """
            SELECT temperature, ph, water_level, status_label, feed_percentage, last_synced
            FROM water_readings
            WHERE last_synced BETWEEN ? AND ?
            ORDER BY last_synced ASC
        """
        with self._connect() as conn:
            rows = conn.execute(
                query,
                (self._serialize_datetime(start), self._serialize_datetime(end)),
            ).fetchall()
        return [
            (temperature, ph, water_level, status_label, feed_percentage, self._parse_datetime(last_synced))
            for temperature, ph, water_level, status_label, feed_percentage, last_synced in rows
        ]

    def save_feed_schedule(self, schedule):
        row = {
            "time": normalize_schedule_time(schedule["time"]),
            "detail": schedule["detail"],
            "active": bool(schedule.get("active", True)),
            "is_executed": bool(schedule.get("is_executed", False)),
        }

        query = """
            INSERT INTO feed_schedules (time_label, detail, active, is_executed)
            VALUES (?, ?, ?, ?)
        """
        with self._connect() as conn:
            cursor = conn.execute(
                query,
                (
                    row["time"],
                    row["detail"],
                    self._to_sql_bool(row["active"]),
                    self._to_sql_bool(row["is_executed"]),
                ),
            )
            row["id"] = cursor.lastrowid
        return row

    def update_feed_schedule_active(self, schedule, active):
        schedule["active"] = active

        if schedule.get("id"):
            query = "UPDATE feed_schedules SET active = ? WHERE id = ?"
            params = (self._to_sql_bool(active), schedule["id"])
        else:
            query = "UPDATE feed_schedules SET active = ? WHERE time_label = ? AND detail = ?"
            params = (self._to_sql_bool(active), schedule["time"], schedule["detail"])

        with self._connect() as conn:
            conn.execute(query, params)

    def load_feed_schedules(self):
        query = """
            SELECT id, time_label, detail, active, is_executed
            FROM feed_schedules
            ORDER BY time_label ASC
        """
        with self._connect() as conn:
            rows = conn.execute(query).fetchall()
        return [
            {
                "id": row[0],
                "time": row[1],
                "detail": row[2],
                "active": bool(row[3]),
                "is_executed": bool(row[4]),
            }
            for row in rows
        ]

    def save_feed_history(self, action_type, status, message, feed_percentage=None):
        query = """
            INSERT INTO feed_history (action_type, status, message, feed_percentage, created_at)
            VALUES (?, ?, ?, ?, ?)
        """
        with self._connect() as conn:
            conn.execute(
                query,
                (
                    action_type,
                    status,
                    message,
                    feed_percentage,
                    self._serialize_datetime(datetime.now()),
                ),
            )

    def get_feed_history(self, limit=20):
        query = """
            SELECT action_type, status, message, feed_percentage, created_at
            FROM feed_history
            ORDER BY created_at DESC
            LIMIT ?
        """
        with self._connect() as conn:
            rows = conn.execute(query, (limit,)).fetchall()
        return [
            (action_type, status, message, feed_percentage, self._parse_datetime(created_at))
            for action_type, status, message, feed_percentage, created_at in rows
        ]

    def _serialize_datetime(self, value):
        if isinstance(value, datetime):
            return value.replace(microsecond=0).isoformat(sep=" ")
        return datetime.now().replace(microsecond=0).isoformat(sep=" ")

    def _parse_datetime(self, value):
        if isinstance(value, datetime):
            return value
        text = str(value or "").strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(text[:19], fmt)
            except ValueError:
                pass
        return datetime.now()

    def _to_sql_bool(self, value):
        return 1 if bool(value) else 0
