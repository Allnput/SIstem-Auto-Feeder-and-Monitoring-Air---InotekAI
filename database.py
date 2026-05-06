from datetime import datetime

from logic import normalize_schedule_time

try:
    import psycopg2
except ImportError:
    psycopg2 = None


DEMO_USERS = {
    "12345": "Chyntya"
}


class Database:
    def __init__(self, url):
        self.url = url
        self.demo_water_history = []
        self.demo_feed_schedules = []
        self.demo_feed_history = []

    def _can_use_postgres(self):
        return bool(self.url and psycopg2 is not None)

    def ensure_schema(self):
        if not self._can_use_postgres():
            return

        statements = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                credential_code VARCHAR(50) NOT NULL UNIQUE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS water_readings (
                id SERIAL PRIMARY KEY,
                temperature NUMERIC(5, 2) NOT NULL,
                ph NUMERIC(4, 2) NOT NULL,
                water_level VARCHAR(50),
                status_label VARCHAR(30) NOT NULL,
                status_color VARCHAR(20) NOT NULL,
                sensor_temp_status VARCHAR(30) NOT NULL DEFAULT 'active',
                sensor_ph_status VARCHAR(30) NOT NULL DEFAULT 'active',
                feed_percentage INTEGER,
                last_synced TIMESTAMP NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS feed_schedules (
                id SERIAL PRIMARY KEY,
                time_label VARCHAR(5) NOT NULL,
                detail TEXT NOT NULL,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                is_executed BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS feed_history (
                id SERIAL PRIMARY KEY,
                action_type VARCHAR(30) NOT NULL,
                status VARCHAR(30) NOT NULL,
                message TEXT NOT NULL,
                feed_percentage INTEGER,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
        ]

        with psycopg2.connect(self.url) as conn:
            with conn.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)

    def find_user_by_code(self, code):
        if not self._can_use_postgres():
            return DEMO_USERS.get(code)

        query = "SELECT name FROM users WHERE credential_code = %s LIMIT 1"
        try:
            with psycopg2.connect(self.url) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (code,))
                    row = cursor.fetchone()
                    return row[0] if row else None
        except Exception:
            return DEMO_USERS.get(code)

    def save_water_reading(self, reading, status):
        last_synced = reading.last_synced if isinstance(reading.last_synced, datetime) else datetime.now()
        row = {
            "temperature": reading.temperature,
            "ph": reading.ph,
            "water_level": reading.water_level,
            "status_label": status["label"],
            "status_color": status["color"],
            "sensor_temp_status": getattr(reading, "sensor_temp_status", "active"),
            "sensor_ph_status": getattr(reading, "sensor_ph_status", "active"),
            "feed_percentage": getattr(reading, "feed_percentage", None),
            "last_synced": last_synced,
        }

        if not self._can_use_postgres():
            self.demo_water_history.append(row)
            return

        query = """
            INSERT INTO water_readings (
                temperature, ph, water_level, status_label, status_color,
                sensor_temp_status, sensor_ph_status, feed_percentage, last_synced
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        with psycopg2.connect(self.url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    query,
                    (
                        row["temperature"],
                        row["ph"],
                        row["water_level"],
                        row["status_label"],
                        row["status_color"],
                        row["sensor_temp_status"],
                        row["sensor_ph_status"],
                        row["feed_percentage"],
                        row["last_synced"],
                    ),
                )

    def get_water_history(self, limit=20):
        if not self._can_use_postgres():
            return list(reversed(self.demo_water_history[-limit:]))

        query = """
            SELECT temperature, ph, water_level, status_label, feed_percentage, last_synced
            FROM water_readings
            ORDER BY last_synced DESC
            LIMIT %s
        """
        with psycopg2.connect(self.url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (limit,))
                return cursor.fetchall()

    def save_feed_schedule(self, schedule):
        row = {
            "time": normalize_schedule_time(schedule["time"]),
            "detail": schedule["detail"],
            "active": schedule.get("active", True),
            "is_executed": schedule.get("is_executed", False),
        }

        if not self._can_use_postgres():
            self.demo_feed_schedules.append(row)
            return row

        query = """
            INSERT INTO feed_schedules (time_label, detail, active, is_executed)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        with psycopg2.connect(self.url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (row["time"], row["detail"], row["active"], row["is_executed"]))
                row["id"] = cursor.fetchone()[0]
        return row

    def update_feed_schedule_active(self, schedule, active):
        schedule["active"] = active

        if not self._can_use_postgres():
            for row in self.demo_feed_schedules:
                same_id = row.get("id") and row.get("id") == schedule.get("id")
                same_schedule = row.get("time") == schedule.get("time") and row.get("detail") == schedule.get("detail")
                if same_id or same_schedule:
                    row["active"] = active
                    break
            return

        if schedule.get("id"):
            query = "UPDATE feed_schedules SET active = %s WHERE id = %s"
            params = (active, schedule["id"])
        else:
            query = "UPDATE feed_schedules SET active = %s WHERE time_label = %s AND detail = %s"
            params = (active, schedule["time"], schedule["detail"])

        with psycopg2.connect(self.url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)

    def load_feed_schedules(self):
        if not self._can_use_postgres():
            return list(self.demo_feed_schedules)

        query = """
            SELECT id, time_label, detail, active, is_executed
            FROM feed_schedules
            ORDER BY time_label ASC
        """
        with psycopg2.connect(self.url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                return [
                    {
                        "id": row[0],
                        "time": row[1],
                        "detail": row[2],
                        "active": row[3],
                        "is_executed": row[4],
                    }
                    for row in cursor.fetchall()
                ]

    def save_feed_history(self, action_type, status, message, feed_percentage=None):
        row = {
            "action_type": action_type,
            "status": status,
            "message": message,
            "feed_percentage": feed_percentage,
            "created_at": datetime.now(),
        }

        if not self._can_use_postgres():
            self.demo_feed_history.append(row)
            return

        query = """
            INSERT INTO feed_history (action_type, status, message, feed_percentage)
            VALUES (%s, %s, %s, %s)
        """
        with psycopg2.connect(self.url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (action_type, status, message, feed_percentage))

    def get_feed_history(self, limit=20):
        if not self._can_use_postgres():
            return list(reversed(self.demo_feed_history[-limit:]))

        query = """
            SELECT action_type, status, message, feed_percentage, created_at
            FROM feed_history
            ORDER BY created_at DESC
            LIMIT %s
        """
        with psycopg2.connect(self.url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (limit,))
                return cursor.fetchall()
