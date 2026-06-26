import sqlite3
from contextlib import contextmanager
from datetime import datetime, time
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
        # Menyuruh SQLite hanya mengambil data di antara start_date dan end_date
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









# #==============================================================================
import random
from datetime import datetime, timedelta

def ph_status(ph):
    try:
        value = float(ph)
    except (TypeError, ValueError):
        return {"label": "Error", "color": "#E74C3C"}

    if value < 0 or value > 14:
        return {"label": "Di Luar Skala", "color": "#E74C3C"}

    hex_color = ph_color(value)

    if 0 <= value < 4: label = "Sangat Asam"
    elif 4 <= value < 6: label = "Asam"
    elif 6 <= value < 7: label = "Hampir Netral"
    elif 7 <= value <= 8: label = "Netral"
    elif 8 < value <= 9: label = "Basa Ringan"
    elif 9 < value < 13: label = "Basa Sedang"
    else: label = "Sangat Basa"

    return {"label": label, "color": hex_color}

def ph_color(ph):
    try:
        value = float(ph)
    except (TypeError, ValueError):
        return "#E74C3C"

    if value < 0 or value > 14: return "#E74C3C"
    
    if value < 1: return "#E74C3C"
    if value < 2: return "#D71920"
    if value < 3: return "#F05A24"
    if value < 4: return "#F7941D"
    if value < 5: return "#FFD21F"
    if value < 6: return "#FFF200"
    if value < 7: return "#D7DF23"
    if value <= 8: return "#37B34A"
    if value <= 9: return "#55C7DF"
    if value <= 10: return "#2F80C8"
    if value <= 11: return "#2464AD"
    if value <= 12: return "#6F63BF"
    if value < 13: return "#6B3FA0"
    if value <= 14: return "#3F1D78"
    
    return "#E74C3C"

# ==========================================
# 2. GENERATOR DATA DUMMY (SPEKTRUM PENUH)
# ==========================================
# def generate_3_months_dummy_data(db: Database, user_id: int):
#     print("Membersihkan data lama agar tidak menumpuk...")
#     with db._connect() as conn:
#         conn.execute("DELETE FROM monitoring_air")
        
#     now = datetime.now()
#     start_date = now - timedelta(days=90)
#     current_date = start_date
#     dummy_records = []
    
#     print("Mempersiapkan data dummy spektrum penuh (0-14)...")
    
#     while current_date <= now:
#         # 4 kali pembacaan dalam sehari (Total ~360 baris dalam 90 hari)
#         for _ in range(4):
#             reading_time = current_date.replace(
#                 hour=random.randint(0, 23),
#                 minute=random.randint(0, 59),
#                 second=random.randint(0, 59)
#             )
            
#             # CRITICAL FIX: Rentang nilai kini mencakup seluruh skala pH (0.0 hingga 14.0)
#             ph_level = round(random.uniform(0.0, 14.0), 2)
            
#             # Panggil fungsi asli aplikasi agar datanya 100% konsisten
#             status = ph_status(ph_level)
            
#             timestamp_str = db._serialize_datetime(reading_time)
            
#             dummy_records.append((
#                 user_id, 
#                 ph_level, 
#                 status["label"], 
#                 status["color"], 
#                 timestamp_str
#             ))
            
#         current_date += timedelta(days=1)

#     query = """
#         INSERT INTO monitoring_air (
#             user_id, ph_level, ph_status_label, ph_status_color, timestamp
#         )
#         VALUES (?, ?, ?, ?, ?)
#     """
    
#     try:
#         with db._connect() as conn:
#             conn.executemany(query, dummy_records)
#         print(f"✅ Berhasil menyisipkan {len(dummy_records)} baris data dummy dengan warna lengkap!")
#     except Exception as e:
#         print(f"❌ Terjadi kesalahan saat memasukkan data: {e}")

def generate_today_hourly_dummy_data(db: Database, user_id: int):
    # Mengambil tanggal hari ini (waktu sistem lokal)
    today = datetime.now().date()
    dummy_records = []
    
    # print(f"Mempersiapkan data dummy per jam untuk hari ini ({today})...")
    
    # Nilai awal pH (dimulai dari Netral untuk simulasi yang realistis)
    current_ph = 7.0
    
    # Looping dari jam 00:00 hingga 23:00 (24 jam)
    for hour in range(24):
        # Set waktu tepat pada pergantian jam (menit 0, detik 0)
        reading_time = datetime.combine(today, time(hour=hour, minute=0, second=0))
        
        # Simulasi fluktuasi air (Random Walk): pH naik atau turun maksimal 1.5 poin
        pergerakan = random.uniform(-1.5, 1.5)
        current_ph += pergerakan
        
        # Clamping: Pastikan nilai tidak bocor hingga kurang dari 0 atau lebih dari 14
        current_ph = round(max(0.0, min(14.0, current_ph)), 2)
        
        # Dapatkan label dan warna menggunakan fungsi validasi
        status = ph_status(current_ph)
        timestamp_str = db._serialize_datetime(reading_time)
        
        dummy_records.append((
            user_id, 
            current_ph, 
            status["label"], 
            status["color"], 
            timestamp_str
        ))

    query = """
        INSERT INTO monitoring_air (
            user_id, ph_level, ph_status_label, ph_status_color, timestamp
        )
        VALUES (?, ?, ?, ?, ?)
    """
    
    try:
        with db._connect() as conn:
            conn.executemany(query, dummy_records)
    except Exception as e:
        print(f"❌ Terjadi kesalahan saat memasukkan data: {e}")