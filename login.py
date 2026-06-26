import os
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox
# from database import Database
# 
from database import Database #generate_today_hourly_dummy_data #, generate_3_months_dummy_data
from dashboard import DashboardPage
from logic import draw_chart_today, draw_gradient_fill, draw_ph_bar, row_value_time, average_ph, bucket_range_label, dot_color, format_last_synced, format_number, four_hour_average, getpHStatus, get_device_health, format_today, mix_color, ph_color, ph_status
from riwayatwmonitoring import RiwayatWaterMonitoringPage
from services import SensorService
# from watermonitoring import WaterMonitoringPage

try:
    from PIL import Image, ImageTk
except ImportError:  # Jika Pillow belum terpasang, sebagian gambar akan memakai fallback teks/gambar PNG biasa.
    Image = None
    ImageTk = None

# Warna utama aplikasi. Nilai ini dipakai berulang supaya tampilan konsisten.
APP_BG = "#f7f2fb"
CARD_BG = "#ffffff"
PRIMARY = "#9157f5"
PRIMARY_DARK = "#7047c8"
TEXT = "#26212a"
MUTED = "#6e6675"
INPUT_BORDER = "#bf8cff"
SHADOW = "#d8d0df"

#kalo ukuran di lcd nya sih 800x480, tapi buat nyamaain lcd ukuran dashboard dibuat 520x320 
DASHBOARD_WIDTH = 520
DASHBOARD_HEIGHT = 320
LOGIN_WIDTH = DASHBOARD_WIDTH
LOGIN_HEIGHT = DASHBOARD_HEIGHT
FIGMA_WIDTH = 960
FIGMA_HEIGHT = 640
BASE_DIR = Path(__file__).resolve().parent
ICON_DIR = BASE_DIR / "icon"

DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "amba.db"))

class RoundedEntry(tk.Canvas):
    # Tkinter Entry bawaan tidak punya rounded corner.
    # Karena itu input "Kode" dibuat dari Canvas + Entry di atasnya.
    def __init__(self, parent, width=260, height=31, radius=15, **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=parent["bg"],
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self.entry_var = tk.StringVar()
        self._draw_round_rect(1, 1, width - 1, height - 1, radius)
        self.entry = tk.Entry(
            self,
            textvariable=self.entry_var,
            relief="flat",
            bd=0,
            font=("Segoe UI", 8),
            fg=TEXT,
            insertbackground=PRIMARY_DARK,
            bg=CARD_BG,
            highlightthickness=0,
        )
        self.entry.insert(0, "Kode")
        self.entry.bind("<FocusIn>", self._clear_placeholder)
        self.entry.bind("<FocusOut>", self._restore_placeholder)
        self.create_window(18, height // 2, window=self.entry, anchor="w", width=width - 34)

    def _draw_round_rect(self, x1, y1, x2, y2, radius):
        # Menggambar kotak rounded memakai polygon smooth.
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        self.create_polygon(points, smooth=True, fill=CARD_BG, outline=INPUT_BORDER, width=1.5)

    def _clear_placeholder(self, _event):
        # Saat input diklik, tulisan placeholder "Kode" dihapus.
        if self.entry_var.get() == "Kode":
            self.entry_var.set("")

    def _restore_placeholder(self, _event):
        # Jika input kosong setelah fokus hilang, placeholder ditampilkan lagi.
        if not self.entry_var.get().strip():
            self.entry_var.set("Kode")

    def get(self):
        value = self.entry_var.get().strip()
        return "" if value == "Kode" else value


class InotekApp:
    # Class utama aplikasi. Semua perpindahan layar dan event tombol ada di sini.
    def __init__(self, window):
        self.window = window
        self.db = Database(DATABASE_PATH)
        self._db_warning_shown = False
        try:
            self.db.ensure_schema()
            # generate_3_months_dummy_data(self.db, user_id=1)
            # generate_today_hourly_dummy_data(self.db, user_id=1)
        except Exception as exc:
            self._warn_database_once(exc)
        self.sensor = SensorService()

        self.code_entry = None
        self.login_card_content = None
        self.current_user_name = "Admin InotekAI"
        self.width = DASHBOARD_WIDTH
        self.height = DASHBOARD_HEIGHT
        self._last_saved_water_key = None
        self.image_cache = {}

        self.window.title("InotekAI Login")
        self.lock_window_size(LOGIN_WIDTH, LOGIN_HEIGHT)
        self.window.configure(bg=APP_BG)
        self.window.bind("<Return>", lambda _event: self.login())

        self.show_login()

    def clear(self):
        # Menghapus semua widget pada window sebelum mengganti halaman.
        for child in self.window.winfo_children():
            child.destroy()

    def lock_window_size(self, width=DASHBOARD_WIDTH, height=DASHBOARD_HEIGHT):
        # Mengunci ukuran window agar semua halaman konsisten.
        self.window.geometry(f"{width}x{height}")
        self.window.minsize(width, height)
        self.window.maxsize(width, height)
        self.window.resizable(False, False)

    def show_login(self):
        # Halaman pertama aplikasi: form login sesuai desain Welcome.
        self.clear()
        self.lock_window_size(LOGIN_WIDTH, LOGIN_HEIGHT)

        shell = tk.Frame(self.window, bg=APP_BG)
        shell.pack(expand=True, fill="both", padx=10, pady=10)

        card = tk.Canvas(shell, bg=APP_BG, highlightthickness=0)
        card.pack(expand=True, fill="both")
        # Configure dipanggil saat ukuran canvas berubah, sehingga kartu tetap tergambar rapi.
        card.bind("<Configure>", self._draw_login_card)

        content = tk.Frame(card, bg=CARD_BG)
        self.login_card_content = content
        card.create_window(LOGIN_WIDTH / 2, LOGIN_HEIGHT / 2, window=content, anchor="center", tags="content")
        card.bind(
            "<Configure>",
            lambda event: card.coords("content", event.width / 2, event.height / 2),
            add="+",
        )

        self._build_logo(content)

        tk.Label(
            content,
            text="Welcome",
            font=("Segoe UI", 14, "bold"),
            fg=TEXT,
            bg=CARD_BG,
        ).pack(pady=(7, 0))

        tk.Label(
            content,
            text="Masukan kode kredential",
            font=("Segoe UI", 7, "bold"),
            fg=TEXT,
            bg=CARD_BG,
        ).pack(pady=(0, 11))

        self.code_entry = RoundedEntry(content)
        self.code_entry.pack()
        self.code_entry.entry.focus_set()

        tk.Button(
            content,
            text="Login",
            command=self.login,
            font=("Segoe UI", 8, "bold"),
            fg="#ffffff",
            bg=PRIMARY,
            activebackground=PRIMARY_DARK,
            activeforeground="#ffffff",
            relief="flat",
            bd=0,
            padx=20,
            pady=4,
            cursor="hand2",
        ).pack(pady=(14, 0))

    def _draw_login_card(self, event):
        # Menggambar kartu putih besar pada halaman login.
        canvas = event.widget
        canvas.delete("card")
        width = event.width
        height = event.height
        margin_x = max(18, int(width * 0.045))
        margin_y = max(16, int(height * 0.045))
        radius = 28
        self._rounded_rect(canvas, margin_x + 1, margin_y + 5, width - margin_x + 1, height - margin_y + 5, radius, SHADOW, "card")
        self._rounded_rect(canvas, margin_x, margin_y, width - margin_x, height - margin_y, radius, CARD_BG, "card")
        canvas.tag_lower("card")

    def _rounded_rect(self, canvas, x1, y1, x2, y2, radius, fill, tag):
        # Helper rounded rectangle sederhana untuk halaman login.
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        canvas.create_polygon(points, smooth=True, fill=fill, outline=fill, tags=tag)

    def _build_logo(self, parent):
        # Logo login memakai file asli dari folder icon.
        logo_image = self._load_icon("logo inotekai.jpeg", 132, 82)
        if logo_image:
            tk.Label(parent, image=logo_image, bg=CARD_BG, bd=0).pack(pady=(0, 0))
            return

        tk.Label(
            parent,
            text="InotekAI",
            font=("Segoe UI", 18, "bold"),
            fg=PRIMARY,
            bg="#faf7ff",
            width=11,
            height=3,
        ).pack(pady=(0, 0))

    def login(self):
        # Ambil kode dari input, lalu cek ke database atau data demo.
        code = self.code_entry.get() if self.code_entry else ""
        if not code:
            messagebox.showerror("Error", "Kode wajib diisi.")
            return

        user_name = self.db.find_user_by_code(code)
        if not user_name:
            messagebox.showerror("Error", "Kode tidak valid.")
            return

        self.current_user_name = user_name
        self.show_dashboard(user_name, mode="ph")

    def show_dashboard(self, user_name, mode="ph"):
        # Isi tampilan dashboard sekarang ada di dashboard.py.
        self.current_user_name = user_name
        DashboardPage(self, user_name, mode).render()

    # def show_water_monitoring_page(self, mode="suhu"):
    #     # Halaman laporan kondisi air ada di watermonitoring.py.
    #     RiwayatWaterMonitoringPage(self, mode).render()

    def get_ph_status(self, ph):
        return getpHStatus(ph)

    def get_device_health(self, data, status="active"):
        return get_device_health(data, status)

    def format_last_synced(self, last_synced):
        return format_last_synced(last_synced)
    
    def format_today(self, last_synced):
        return format_today(last_synced)
    
    def four_hour_average(self, rows, metric):
        return four_hour_average(rows, metric)
    
    def average_ph(self, rows):
        return average_ph(rows)
    
    def ph_status(self, ph):
        return ph_status(ph)
    
    def dot_color(self, status):
        return dot_color(status)
    
    def ph_color(self, ph):
        return ph_color(ph)
    
    def mix_color(self, start_color, end_color, ratio):
        return mix_color(start_color, end_color, ratio)

    def bucket_range_label(self, index):
        return bucket_range_label(index)
    
    def format_number(self, value):
        return format_number(value)
    
    def get_today_ph_readings(self):
        try:
            return self.db.get_today_ph_readings()
        except Exception as exc:
            self._warn_database_once(exc)
            return []

    def save_water_reading(self, reading, ph_status_label, ph_status_color, last_synced):
        last_synced = reading.last_synced if isinstance(reading.last_synced, datetime) else datetime.now()
        key = (
            round(float(reading.ph), 2),
            str(last_synced.replace(microsecond=0)),
        )
        if key == self._last_saved_water_key:
            return
        try:
            user_id = self.current_user_name[0] if isinstance(self.current_user_name, tuple) else 1
            self.db.save_ph_reading(user_id, reading.ph, ph_status_label, ph_status_color)
            
        except Exception as exc:
            self._warn_database_once(exc)
            
        self._last_saved_water_key = key

    def _warn_database_once(self, exc):
        if self._db_warning_shown:
            return
        self._db_warning_shown = True
        messagebox.showwarning("Database", f"Data belum bisa disimpan ke SQLite.\n\n{exc}")

    def show_water_history(self):
        RiwayatWaterMonitoringPage(self).render()

    def _dashboard_round_rect(self, canvas, x1, y1, x2, y2, radius, fill, outline, width, tags):
        # Rounded rectangle khusus dashboard.
        # Tkinter Canvas tidak punya create_round_rectangle, jadi bentuknya dibuat dari polygon.
        points = [
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        ]
        canvas.create_polygon(points, smooth=True, fill=fill, outline=outline, width=width, tags=tags)

# Atur bagian kartu kecil didalam kondisi air
    def _metric_card(self, canvas, sx, sy, fs, rect, line, x, y, title, value, status, fill, status_color="#000000"):
        # Kartu kecil untuk nilai sensor seperti pH Air dan Suhu Air.
        rect(x, y, 153, 162, 22, fill, shadow=True)
        canvas.create_text(sx(x + 77), sy(y + 2), text=title, anchor="n", font=("Segoe UI", fs(24), "bold"), fill="#000000")
        line(x + 16, y + 45, x + 136, y + 45, "#000000", 1)
        canvas.create_text(sx(x + 77), sy(y + 55), text=value, anchor="n", font=("Segoe UI", fs(40), "bold"), fill="#000000")
        canvas.create_text(sx(x + 77), sy(y + 115), text=status, anchor="n", font=("Segoe UI", fs(20)), fill=status_color)

# Atur bagian kartu kecil didalam kondisi air
    def _monitoring_card(self, canvas, sx, sy, fs, rect, line, x, y, title, value, status, fill, status_color="#000000"):
        # Ukuran rectangle fleksibel, menyesuaikan konten
        padding_x = 20  # jarak kiri-kanan
        padding_y = 15  # jarak atas-bawah

        # Hitung lebar dan tinggi rectangle berdasarkan teks
        width = max(155, len(str(value)) * 20 + padding_x*2)
        height = 115  # tetap, tapi bisa juga dibuat dinamis jika mau

        rect(x-5, y, width, height, 18, fill, shadow=True)

        # Titik tengah rectangle
        center_x = x + width / 2
        center_y = y + height / 2

        # Posisi relatif title, value, status
        title_y = y + padding_y + 5
        value_y = y + height / 2 - 10
        status_y = y + height - padding_y

        # Gambar teks center
        canvas.create_text(sx(center_x), sy(title_y), text=title, anchor="center", font=("Segoe UI", fs(24), "bold"), fill="#000000")
        line(x + 16, y + 43, x + width - 16, y + 43, "#000000", 1)
        canvas.create_text(sx(center_x), sy(value_y + 30), text=value, anchor="center", font=("Segoe UI", fs(32), "bold"), fill="#000000")
        canvas.create_text(sx(center_x), sy(status_y), text=status, anchor="center", font=("Segoe UI", fs(20)), fill=status_color)
        

    def _stroke(self, size, scale):
        # Ketebalan garis ikut rasio tinggi dashboard agar tidak terlalu besar di layar 800x480.
        return max(1, int(size * (DASHBOARD_HEIGHT / FIGMA_HEIGHT) * scale))
    
    def row_value_time(self, row, metric):
        return row_value_time(row, metric)

    def _load_icon(self, filename, width, height):
        # Membaca dan mengecilkan/membesarkan icon dari folder icon.
        # Pillow dibutuhkan agar file JPEG dan resize gambar berjalan baik.
        key = (filename, width, height)
        if key in self.image_cache:
            return self.image_cache[key]

        path = ICON_DIR / filename
        if not path.exists():
            return None

        if Image is not None and ImageTk is not None:
            resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
            image = Image.open(path).convert("RGBA")
            image = image.resize((max(1, width), max(1, height)), resample)
            photo = ImageTk.PhotoImage(image)
            self.image_cache[key] = photo
            return photo

        if path.suffix.lower() == ".png":
            photo = tk.PhotoImage(file=str(path))
            self.image_cache[key] = photo
            return photo

        return None

    def _draw_icon_image(self, canvas, sx, sy, scale, filename, x, y, width, height, fallback=None):
        # Menggambar icon dari file. Jika gagal, fallback menggambar icon manual lama.
        image_width = max(1, int(width * (DASHBOARD_WIDTH / FIGMA_WIDTH) * scale))
        image_height = max(1, int(height * (DASHBOARD_HEIGHT / FIGMA_HEIGHT) * scale))
        image = self._load_icon(filename, image_width, image_height)
        if image:
            canvas.create_image(sx(x), sy(y), image=image, anchor="nw")
        elif fallback:
            fallback()
    
    def draw_ph_bar(self, canvas, sx, sy, scale):
        return draw_ph_bar(canvas, sx, sy, scale)
    
    def draw_gradient_fill(self, canvas, sx, sy, point_items, bottom):
        return draw_gradient_fill(canvas, sx, sy, point_items, bottom, self.ph_color)

    def draw_chart_today(self, canvas, sx, sy, fs, line, text, accent, fill, values):
        return draw_chart_today(self, canvas, sx, sy, fs, line, text, accent, fill, values)

if __name__ == "__main__":
    # Titik awal program. Tk() membuat window, lalu mainloop menjalankan aplikasi.
    root = tk.Tk()
    app = InotekApp(root)
    root.mainloop()
