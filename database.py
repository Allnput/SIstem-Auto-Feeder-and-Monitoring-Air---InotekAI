import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_PATH = BASE_DIR / "amba.db"


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
            CREATE TABLE IF NOT EXISTS user (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                credential_id TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS monitoring_air (
                id_ph INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ph_level REAL NOT NULL,
                ph_status_color TEXT NOT NULL,
                ph_status_label TEXT NOT NULL,
                timestamp datetime NOT NULL,

                FOREIGN KEY (user_id)
                    REFERENCES user(user_id)
                    ON DELETE CASCADE
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS device_status (
                device_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'aktif',
                last_seen datetime NOT NULL,

                FOREIGN KEY (user_id)
                    REFERENCES user(user_id)
                    ON DELETE CASCADE
            )
            """,

            """
            CREATE TABLE IF NOT EXISTS notifikasi (
                notification_id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,
                device_id INTEGER,
                ph_id INTEGER,

                notification_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,

                is_read INTEGER NOT NULL DEFAULT 0,
                timestamp datetime NOT NULL,

                FOREIGN KEY (user_id)
                    REFERENCES user(user_id)
                    ON DELETE CASCADE,

                FOREIGN KEY (device_id)
                    REFERENCES device_status(device_id)
                    ON DELETE SET NULL,

                FOREIGN KEY (ph_id)
                    REFERENCES monitoring_air(id_ph)
                    ON DELETE SET NULL
            )
            """
        ]
            
        with self._connect() as conn:
            for statement in statements:
                conn.execute(statement)
            
            conn.execute("""
                INSERT OR IGNORE INTO user (
                    credential_id,
                    name
                )
                VALUES (?, ?)
            """, ("12345", "Linda"))
            
    def find_user_by_code(self, code):
        query = """
            SELECT user_id, name
            FROM user
            WHERE credential_id = ?
            LIMIT 1
        """

        with self._connect() as conn:
            row = conn.execute(query, (code,)).fetchone()

        return row
    
    def save_ph_reading(
        self,user_id,ph_level,ph_status_label,ph_status_color):
        query = """
            INSERT INTO monitoring_air (
                user_id,
                ph_level,
                ph_status_label,
                ph_status_color,
                timestamp
            )
            VALUES (?, ?, ?, ?, ?)
        """

        with self._connect() as conn:
            conn.execute(
                query,
                (
                    user_id,
                    ph_level,
                    ph_status_label,
                    ph_status_color,
                    self._serialize_datetime(datetime.now())
                )
            )
    
    
    def get_water_history(self, limit=1000):
        query = """
            SELECT
                ph_level,
                ph_status_label,
                ph_status_color,
                timestamp
            FROM monitoring_air
            ORDER BY timestamp DESC
            LIMIT ?
        """

        with self._connect() as conn:
            rows = conn.execute(query, (limit,)).fetchall()

        return rows

    def get_today_ph_readings(self):
        query = """
            SELECT
                ph_level,
                ph_status_label,
                ph_status_color,
                timestamp
            FROM monitoring_air
            ORDER BY timestamp ASC
        """

        with self._connect() as conn:
            rows = conn.execute(query).fetchall()

        return rows
    
    def _serialize_datetime(self, value):
        if isinstance(value, datetime):
            return value.replace(microsecond=0)
        return datetime.now().replace(microsecond=0)

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

    def get_water_history_by_date_range(self, start_date, end_date):
        query = """
            SELECT
                ph_level,
                ph_status_label,
                ph_status_color,
                timestamp
            FROM monitoring_air
            WHERE DATE(timestamp) BETWEEN ? AND ?
            ORDER BY timestamp DESC
        """

        # Format datetime.date menjadi string YYYY-MM-DD untuk SQLite
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        with self._connect() as conn:
            rows = conn.execute(query, (start_str, end_str)).fetchall()

        return rows

#NOTIFICATION MANAGEMENT-------------------
    def get_last_device_status(self, user_id=1):
        query = """
            SELECT status FROM device_status 
            WHERE user_id = ? 
            ORDER BY last_seen DESC LIMIT 1
        """
        with self._connect() as conn:
            row = conn.execute(query, (user_id,)).fetchone()
        # Default asumsikan 'active' jika belum ada data sama sekali
        return row[0] if row else "active"

    def update_device_status(self, user_id, status):
        query = """
            INSERT INTO device_status (user_id, status, last_seen) 
            VALUES (?, ?, ?)
        """
        with self._connect() as conn:
            conn.execute(query, (user_id, status, self._serialize_datetime(datetime.now())))

    def insert_notification(self, user_id, notif_type, title, message):
        query = """
            INSERT INTO notifikasi (user_id, notification_type, title, message, timestamp) 
            VALUES (?, ?, ?, ?, ?)
        """
        with self._connect() as conn:
            conn.execute(query, (user_id, notif_type, title, message, self._serialize_datetime(datetime.now())))

    def get_notifications(self, user_id=1, limit=5):
        query = """
            SELECT notification_type, title, message, timestamp 
            FROM notifikasi 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """
        with self._connect() as conn:
            return conn.execute(query, (user_id, limit)).fetchall()