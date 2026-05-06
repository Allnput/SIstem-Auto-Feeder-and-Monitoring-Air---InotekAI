import os
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

from database import Database
from dashboard import DashboardPage
from feed import FeedPage
from feednew import FeedNewPage
from logic import format_last_synced, getWaterStatus, get_device_health, get_feed_level_label, get_today_schedule
from riwayatpakan import RiwayatPakanPage
from services import GpioService, IoTManualFeedClient, SensorService
from watermonitoring import WaterMonitoringPage

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

DATABASE_URL = os.getenv("DATABASE_URL", "")
IOT_MANUAL_FEED_URL = os.getenv("IOT_MANUAL_FEED_URL", "")

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
        self.db = Database(DATABASE_URL)
        self._db_warning_shown = False
        try:
            self.db.ensure_schema()
        except Exception as exc:
            self._warn_database_once(exc)
        self.sensor = SensorService()
        self.gpio = GpioService()
        self.iot_feed_client = IoTManualFeedClient(IOT_MANUAL_FEED_URL)
        self.code_entry = None
        self.login_card_content = None
        self.current_user_name = "Admin InotekAI"
        self.width = DASHBOARD_WIDTH
        self.height = DASHBOARD_HEIGHT
        self._last_saved_water_key = None
        try:
            self.feed_schedules = self.db.load_feed_schedules()
        except Exception as exc:
            self._warn_database_once(exc)
            self.feed_schedules = []
        # Tkinter menghapus gambar dari memori jika tidak disimpan referensinya.
        # Cache ini menjaga semua logo/icon tetap tampil setelah dibuat.
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
        self.show_dashboard(user_name)

    def show_dashboard(self, user_name):
        # Isi tampilan dashboard sekarang ada di dashboard.py.
        self.current_user_name = user_name
        DashboardPage(self, user_name).render()

    def manual_feed(self):
        # Event tombol "Tap untuk memberi makan".
        reading = self.sensor.read_water_quality()
        feeder = get_device_health(reading, getattr(reading, "auto_feeder_status", "active"))
        if not feeder["active"]:
            self._save_feed_history("manual", "failed", "Kesalahan pada alat", getattr(reading, "feed_percentage", None))
            messagebox.showerror("Manual Feed", "Kesalahan pada alat")
            return

        try:
            self.iot_feed_client.triggerManualFeed()
            if not IOT_MANUAL_FEED_URL:
                self.gpio.dispense_feed()
        except Exception as exc:
            self._save_feed_history("manual", "failed", str(exc), getattr(reading, "feed_percentage", None))
            messagebox.showerror("Manual Feed", f"Kesalahan pada alat\n\n{exc}")
            return

        self._save_feed_history("manual", "success", "Pakan telah diberikan", getattr(reading, "feed_percentage", None))
        messagebox.showinfo("Manual Feed", "Pakan telah diberikan")

    def show_schedule_page(self):
        # Isi tampilan jadwal/autofeeder sekarang ada di feed.py.
        FeedPage(self).render()

    def show_feed_history_page(self):
        RiwayatPakanPage(self).render()

    def show_new_feed_page(self):
        # Form tambah jadwal pakan baru ada di feednew.py.
        FeedNewPage(self).render()

    def add_feed_schedule(self, schedule):
        # Dipanggil dari feednew.py ketika tombol Simpan Jadwal ditekan.
        try:
            saved_schedule = self.db.save_feed_schedule(schedule)
        except Exception as exc:
            self._warn_database_once(exc)
            saved_schedule = schedule
        self.feed_schedules.append(saved_schedule)
        self.show_schedule_page()

    def toggle_feed_schedule(self, index):
        if index < 0 or index >= len(self.feed_schedules):
            return

        schedule = self.feed_schedules[index]
        active = not schedule.get("active", True)
        schedule["active"] = active
        try:
            self.db.update_feed_schedule_active(schedule, active)
        except Exception as exc:
            self._warn_database_once(exc)
        self.show_schedule_page()

    def show_water_monitoring_page(self, mode="suhu"):
        # Halaman laporan kondisi air ada di watermonitoring.py.
        WaterMonitoringPage(self, mode).render()

    def get_water_status(self, temp, ph):
        return getWaterStatus(temp, ph)

    def get_device_health(self, data, status="active"):
        return get_device_health(data, status)

    def format_last_synced(self, last_synced):
        return format_last_synced(last_synced)

    def get_today_schedule(self):
        return get_today_schedule(self.feed_schedules)

    def save_water_reading(self, reading, water_status):
        last_synced = reading.last_synced if isinstance(reading.last_synced, datetime) else datetime.now()
        key = (
            round(float(reading.temperature), 2),
            round(float(reading.ph), 2),
            str(last_synced.replace(microsecond=0)),
        )
        if key == self._last_saved_water_key:
            return

        try:
            self.db.save_water_reading(reading, water_status)
        except Exception as exc:
            self._warn_database_once(exc)
        self._last_saved_water_key = key

    def _save_feed_history(self, action_type, status, message, feed_percentage=None):
        try:
            self.db.save_feed_history(action_type, status, message, feed_percentage)
        except Exception as exc:
            self._warn_database_once(exc)

    def _warn_database_once(self, exc):
        if self._db_warning_shown:
            return
        self._db_warning_shown = True
        messagebox.showwarning("Database", f"Data belum bisa disimpan ke PostgreSQL.\n\n{exc}")

    def show_water_history(self):
        try:
            rows = self.db.get_water_history()
        except Exception as exc:
            self._warn_database_once(exc)
            rows = []
        if not rows:
            messagebox.showinfo("Riwayat Air", "Belum ada riwayat air.")
            return

        lines = []
        for row in rows[:8]:
            if isinstance(row, dict):
                synced = format_last_synced(row["last_synced"])
                lines.append(f"{synced} | Suhu {row['temperature']} | pH {row['ph']} | {row['status_label']}")
            else:
                synced = format_last_synced(row[5])
                lines.append(f"{synced} | Suhu {row[0]} | pH {row[1]} | {row[3]}")
        messagebox.showinfo("Riwayat Air", "\n".join(lines))

    def show_feed_history(self):
        try:
            rows = self.db.get_feed_history()
        except Exception as exc:
            self._warn_database_once(exc)
            rows = []
        if not rows:
            messagebox.showinfo("Riwayat Pakan", "Belum ada riwayat pakan.")
            return

        lines = []
        for row in rows[:8]:
            if isinstance(row, dict):
                created_at = format_last_synced(row["created_at"])
                lines.append(f"{created_at} | {row['action_type']} | {row['status']} | {row['message']}")
            else:
                created_at = format_last_synced(row[4])
                lines.append(f"{created_at} | {row[0]} | {row[1]} | {row[2]}")
        messagebox.showinfo("Riwayat Pakan", "\n".join(lines))

    def _draw_schedule_page(self, canvas):
        # Tampilan jadwal pakan sesuai gambar: daftar jadwal, total pemberian, dan manual feed.
        canvas.delete("all")
        canvas.configure(bg="#f8f5fc")

        width = max(canvas.winfo_width(), DASHBOARD_WIDTH)
        height = max(canvas.winfo_height(), DASHBOARD_HEIGHT)
        scale = min(width / DASHBOARD_WIDTH, height / DASHBOARD_HEIGHT)
        ox = (width - DASHBOARD_WIDTH * scale) / 2
        oy = (height - DASHBOARD_HEIGHT * scale) / 2
        x_ratio = DASHBOARD_WIDTH / FIGMA_WIDTH
        y_ratio = DASHBOARD_HEIGHT / FIGMA_HEIGHT

        def sx(value):
            return ox + value * x_ratio * scale

        def sy(value):
            return oy + value * y_ratio * scale

        def fs(size):
            return max(7, int(size * y_ratio * scale))

        def rect(x, y, w, h, r, fill, outline="", width=0, shadow=False, tags=None):
            if shadow:
                self._dashboard_round_rect(canvas, sx(x + 4), sy(y + 5), sx(x + w + 4), sy(y + h + 5), r * y_ratio * scale, "#c9c9c9", "#c9c9c9", 0, None)
            self._dashboard_round_rect(canvas, sx(x), sy(y), sx(x + w), sy(y + h), r * y_ratio * scale, fill, outline or fill, width, tags)

        def text(x, y, value, size, weight="normal", fill="#000000", anchor="nw", tags=None, justify="left"):
            canvas.create_text(
                sx(x),
                sy(y),
                text=value,
                fill=fill,
                anchor=anchor,
                justify=justify,
                font=("Segoe UI", fs(size), weight),
                tags=tags,
            )

        def line(x1, y1, x2, y2, fill=PRIMARY, width=1):
            canvas.create_line(sx(x1), sy(y1), sx(x2), sy(y2), fill=fill, width=max(1, int(width * scale)))

        def circle(x, y, size, fill, tags=None):
            canvas.create_oval(sx(x), sy(y), sx(x + size), sy(y + size), fill=fill, outline=fill, tags=tags)

        canvas.create_rectangle(0, 0, width, height, fill="#f8f5fc", outline="#f8f5fc")

        # Sidebar. Pada halaman ini menu Auto Feeder aktif, jadi icon fish berwarna ungu.
        rect(0, 0, 78, 640, 0, "#ffffff", shadow=True)
        rect(8, 20, 61, 52, 0, "#faf7ff")
        self._draw_icon_image(canvas, sx, sy, scale, "logo inotekai.jpeg", 8, 20, 61, 52, fallback=lambda: text(12, 35, "InotekAI", 10, "bold", PRIMARY))
        self._draw_icon_image(canvas, sx, sy, scale, "home hitam.png", 22, 235, 38, 38, fallback=lambda: self._draw_home_icon(canvas, sx, sy, scale, 24, 243),)
        canvas.create_rectangle(sx(12), sy(228), sx(66), sy(282), fill="", outline="", tags="home-nav")
        self._draw_icon_image(canvas, sx, sy, scale, "water hitam.png", 22, 300, 42, 42, fallback=lambda: self._draw_water_icon(canvas, sx, sy, scale, 21, 302, label=True))
        self._draw_icon_image(canvas, sx, sy, scale, "fish ungu.png", 15, 360, 50, 50, fallback=lambda: self._draw_fish_icon(canvas, sx, sy, scale, 17, 367, color=PRIMARY))

        # Kartu utama Auto Feeder Status.
        rect(93, 20, 610, 598, 40, "#ffffff", shadow=True)
        self._draw_icon_image(canvas, sx, sy, scale, "fish ungu.png", 118, 42, 64, 64, fallback=lambda: self._draw_fish_icon(canvas, sx, sy, scale, 120, 45, color=PRIMARY))
        text(193, 48, "Auto Feeder Status", 28, "bold")
        circle(198, 89, 12, "#09ff00")
        text(213, 82, "Aktif", 16)
        rect(500, 40, 170, 50, 10, "#eeedfe", shadow=True, tags="history-feed")
        text(530, 55, "Riwayat Pakan", 16, "bold", tags="history-feed")
        text(650, 52, ">", 18, "bold", PRIMARY, tags="history-feed")
        line(133, 120, 672, 120, PRIMARY, 1)

        text(120, 150, "Jadwal Pakan", 24, "bold")
        self._schedule_row(canvas, sx, sy, fs, rect, 120, 195, "14.00", "Sekali-5 Meter", True)
        self._schedule_row(canvas, sx, sy, fs, rect, 120, 275, "19.00", "Sen, Sel, Rab-1 Meter", False)

        rect(610, 535, 70, 68, 12, "#eeedfe", shadow=True, tags="add-schedule")
        text(638, 545, "+", 42, "bold", PRIMARY, tags="add-schedule")

        # Kartu kanan: total pemberian dan ringkasan jadwal hari ini.
        rect(715, 20, 220, 340, 24, "#ffffff", shadow=True)
        rect(730, 32, 190, 145, 12, "#e6f1fb")
        text(748, 40, "Total pemberian\npakan hari ini", 18, "bold", justify="left")
        line(748, 96, 900, 96, "#6aa6d8", 1)
        text(817, 112, "5", 58, "bold")
        text(790, 190, "Jadwal hari ini", 20)
        line(748, 222, 900, 222, PRIMARY, 1)
        text(748, 240, "07:00", 22, fill="#c0c0c0")
        text(748, 273, "14:00", 22)
        text(748, 306, "19:00", 22, fill="#c0c0c0")
        self._pill(canvas, sx, sy, fs, 842, 240, 84, "Selesai", "#e1f5ee", "#5ab99b")
        self._pill(canvas, sx, sy, fs, 830, 273, 104, "Menunggu", "#e6f1fb", "#1e63a7")
        self._pill(canvas, sx, sy, fs, 835, 306, 96, "Terjadwal", "#d9d9d9", "#000000")

        # Manual feed card.
        rect(715, 380, 220, 238, 30, "#ffffff", shadow=True)
        circle(736, 398, 12, "#d9d9d9")
        text(752, 392, "Tidak Aktif", 16)
        text(775, 460, "Manual\nFeed", 32, "bold", justify="center")
        self._draw_icon_image(canvas, sx, sy, scale, "fish ungu.png", 865, 492, 28, 28, fallback=lambda: self._draw_feed_button_icon(canvas, sx, sy, scale, 876, 491))
        rect(724, 570, 210, 35, 28, "#d9d9d9", tags="manual-feed")
        text(734, 575, "Tap untuk memberi makan", 15, tags="manual-feed")

    def _draw_dashboard(self, canvas):
        # Semua komponen dashboard digambar manual di Canvas agar mirip desain Figma.
        canvas.delete("all")
        canvas.configure(bg="#f3f4f4")

        # Ukuran layar dashboard adalah 800x480.
        # Desain awal dibuat dengan koordinat Figma 960x640, lalu dipetakan ke layar ini.
        width = max(canvas.winfo_width(), DASHBOARD_WIDTH)
        height = max(canvas.winfo_height(), DASHBOARD_HEIGHT)
        scale = min(width / DASHBOARD_WIDTH, height / DASHBOARD_HEIGHT)
        ox = (width - DASHBOARD_WIDTH * scale) / 2
        oy = (height - DASHBOARD_HEIGHT * scale) / 2
        x_ratio = DASHBOARD_WIDTH / FIGMA_WIDTH
        y_ratio = DASHBOARD_HEIGHT / FIGMA_HEIGHT

        def sx(value):
            # Mengubah koordinat X dari desain Figma 960px ke dashboard 800px.
            return ox + value * x_ratio * scale

        def sy(value):
            # Mengubah koordinat Y dari desain Figma 640px ke dashboard 480px.
            return oy + value * y_ratio * scale

        def fs(size):
            # Mengubah ukuran font agar ikut skala dashboard.
            return max(7, int(size * y_ratio * scale))

        def rect(x, y, w, h, r, fill, outline="", width=0, shadow=False, tags=None):
            # Helper untuk menggambar kartu/panel rounded dengan opsi shadow.
            if shadow:
                self._dashboard_round_rect(canvas, sx(x + 4), sy(y + 5), sx(x + w + 4), sy(y + h + 5), r * y_ratio * scale, "#c9c9c9", "#c9c9c9", 0, None)
            self._dashboard_round_rect(canvas, sx(x), sy(y), sx(x + w), sy(y + h), r * y_ratio * scale, fill, outline or fill, width, tags)

        def text(x, y, value, size, weight="normal", fill="#000000", anchor="nw", tags=None, justify="left"):
            # Helper teks supaya pemanggilan create_text lebih singkat.
            canvas.create_text(
                sx(x),
                sy(y),
                text=value,
                fill=fill,
                anchor=anchor,
                justify=justify,
                font=("Segoe UI", fs(size), weight),
                tags=tags,
            )

        def line(x1, y1, x2, y2, fill="#9157f5", width=1):
            # Helper garis untuk separator seperti pada Figma.
            canvas.create_line(sx(x1), sy(y1), sx(x2), sy(y2), fill=fill, width=max(1, int(width * scale)))

        def circle(x, y, size, fill, tags=None):
            # Helper lingkaran kecil, misalnya indikator status Aktif/Tidak Aktif.
            canvas.create_oval(sx(x), sy(y), sx(x + size), sy(y + size), fill=fill, outline=fill, tags=tags)

        canvas.create_rectangle(0, 0, width, height, fill="#f3f4f4", outline="#f3f4f4")

# Sidebar.
        rect(0, 0, 78, 640, 0, "#ffffff", shadow=True)
        rect(8, 20, 61, 52, 0, "#faf7ff")
        self._draw_icon_image(canvas, sx, sy, scale, "logo inotekai.jpeg", 8, 20, 61, 52, fallback=lambda: text(12, 35, "InotekAI", 10, "bold", PRIMARY))
        self._draw_icon_image(canvas, sx, sy, scale, "home ungu.png", 22, 235, 38, 38, fallback=lambda: self._draw_home_icon(canvas, sx, sy, scale, 24, 243, PRIMARY))
        self._draw_icon_image(canvas, sx, sy, scale, "water hitam.png", 22, 300, 42, 42, fallback=lambda: self._draw_water_icon(canvas, sx, sy, scale, 21, 302, label=True))
        self._draw_icon_image(canvas, sx, sy, scale, "fish hitam.png", 15, 360, 50, 50, fallback=lambda: self._draw_fish_icon(canvas, sx, sy, scale, 17, 367))

        # Kondisi air card.
        rect(90, 20, 610, 290, 45, "#ffffff", shadow=True)
        self._draw_icon_image(canvas, sx, sy, scale, "water ungu.png", 116, 37, 58, 58, fallback=lambda: self._draw_water_icon(canvas, sx, sy, scale, 120, 39, label=True, color=PRIMARY))
        text(192, 43, "Kondisi Air Terkini", 24, "bold")
        circle(196, 85, 12, "#09ff00")
        text(213, 77, "Aktif", 16)
        text(129, 135, "13.45", 64, "bold")
        text(145, 238, "Terakhir diperbarui", 16, fill="#646464", weight="bold")
#LAPORAN DI KONDISI AIR
        rect(500, 35, 180, 50, 10, "#eeedfe", shadow=True, tags="report")
        text(515, 48, "Lihat Laporan", 16, "bold", tags="report")
        text(650, 45, ">", 18, "bold", PRIMARY, tags="report")
        
        reading = self.sensor.read_water_quality()
        ph_value = reading.ph
        temp_value = reading.temperature

        self._metric_card(canvas, sx, sy, fs, rect, line, 352, 110, "pH Air", str(ph_value), "Optimal", "#eeedfe")
        self._metric_card(canvas, sx, sy, fs, rect, line, 530, 110, "Suhu Air", str(temp_value), "Normal", "#e6f1fb")

        # Sisa pakan card.
        rect(715, 24, 220, 286, 24, "#ffffff", shadow=True)
        text(755, 43, "Sisa Pakan", 24, "bold")
        self._draw_feed_gauge(canvas, sx, sy, scale, 825, 190, 75)

        # Auto feeder card.
        rect(93, 335, 610, 282, 40, "#ffffff", shadow=True)
        self._draw_icon_image(canvas, sx, sy, scale, "fish ungu.png", 114, 360, 65, 65, fallback=lambda: self._draw_fish_icon(canvas, sx, sy, scale, 120, 365, color=PRIMARY))
        text(193, 360, "Auto Feeder Status", 24, "bold")
        circle(196, 402, 12, "#09ff00")
        text(213, 396, "Aktif", 16)
        rect(500, 355, 180, 50, 10, "#eeedfe", shadow=True, tags="schedule")

        text(515, 370, "Jadwal Pakan", 16, "bold", tags="schedule")
        text(650, 368, ">", 18, "bold", PRIMARY, tags="schedule")
        line(133, 435, 673, 435, PRIMARY, 1)
        text(140, 456, "Jadwal hari ini", 24)
        text(145, 505, "07:00", 24, fill="#c0c0c0")
        text(144, 536, "14:00", 24)
        text(144, 566, "19:00", 24, fill="#c0c0c0")
        self._pill(canvas, sx, sy, fs, 558, 505, 88, "Selesai", "#e1f5ee", "#5ab99b")
        self._pill(canvas, sx, sy, fs, 544, 536, 112, "Menunggu", "#e6f1fb", "#1e63a7")
        self._pill(canvas, sx, sy, fs, 548, 567, 105, "Terjadwal", "#d9d9d9", "#000000")

        # Manual feed card.
        rect(715, 335, 225, 282, 30, "#ffffff", shadow=True)
        circle(736, 352, 12, "#d9d9d9")
        text(752, 346, "Tidak Aktif", 16)
        text(775, 437, "Manual\nFeed", 24, "bold", justify="center")
        self._draw_icon_image(canvas, sx, sy, scale, "fish ungu.png", 865, 490, 28, 28, fallback=lambda: self._draw_feed_button_icon(canvas, sx, sy, scale, 876, 491))
        rect(724, 570, 210, 35, 28, "#d9d9d9", tags="manual-feed")
        text(734, 575, "Tap untuk memberi makan", 15, tags="manual-feed")

    def _schedule_row(self, canvas, sx, sy, fs, rect, x, y, time_text, detail_text, active):
        # Satu baris jadwal pakan, lengkap dengan toggle aktif/nonaktif di kanan.
        row_fill = "#eeedfe" if active else "#ffffff"
        knob_fill = PRIMARY if active else "#d9d9d9"
        knob_x = x + 465 if active else x + 442
        rect(x, y, 555, 70, 26, row_fill, shadow=True)
        canvas.create_text(sx(x + 28), sy(y + 11), text=time_text, anchor="nw", font=("Segoe UI", fs(34)), fill="#000000")
        canvas.create_text(sx(x + 30), sy(y + 48), text=detail_text, anchor="nw", font=("Segoe UI", fs(14)), fill="#000000")
        self._dashboard_round_rect(canvas, sx(x + 430), sy(y + 23), sx(x + 515), sy(y + 55), 18, "#ffffff", "#eeeeee", 1, None)
        canvas.create_oval(sx(knob_x), sy(y + 22), sx(knob_x + 34), sy(y + 56), fill=knob_fill, outline=knob_fill)

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
        rect(x, y, 155, 162, 22, fill, shadow=True)
        canvas.create_text(sx(x + 77), sy(y + 2), text=title, anchor="n", font=("Segoe UI", fs(24), "bold"), fill="#000000")
        line(x + 16, y + 45, x + 136, y + 45, "#000000", 1)
        canvas.create_text(sx(x + 77), sy(y + 55), text=value, anchor="n", font=("Segoe UI", fs(40), "bold"), fill="#000000")
        canvas.create_text(sx(x + 77), sy(y + 115), text=status, anchor="n", font=("Segoe UI", fs(20)), fill=status_color)

# Label kecil pada jadwal pakan: Selesai, Menunggu, Terjadwal.
    def _pill(self, canvas, sx, sy, fs, x, y, width, label, bg, fg):
        # Label status kecil pada jadwal pakan: Selesai, Menunggu, Terjadwal.
        self._dashboard_round_rect(canvas, sx(x), sy(y), sx(x + width), sy(y + 24), 12, bg, bg, 0, None)
        canvas.create_text(sx(x + width / 2), sy(y + 12), text=label, anchor="center", font=("Segoe UI", fs(14)), fill=fg)

    def _stroke(self, size, scale):
        # Ketebalan garis ikut rasio tinggi dashboard agar tidak terlalu besar di layar 800x480.
        return max(1, int(size * (DASHBOARD_HEIGHT / FIGMA_HEIGHT) * scale))

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

    def _draw_feed_gauge(self, canvas, sx, sy, scale, cx, cy, percent):
        # Lingkaran progress untuk sisa pakan.
        # Bagian ungu menunjukkan persentase pakan yang masih tersedia.
        percent = max(0, min(100, int(float(percent or 0))))
        purple = PRIMARY
        track = "#eeedfe"
        radius = 80
        stroke = max(12, self._stroke(15, scale))
        x1, y1 = sx(cx - radius), sy(cy - radius)
        x2, y2 = sx(cx + radius), sy(cy + radius)
        canvas.create_arc(x1, y1, x2, y2, start=0, extent=359.9, style="arc", outline=track, width=stroke)
        canvas.create_arc(
            x1,
            y1,
            x2,
            y2,
            start=90,
            extent=-360 * percent / 100,
            style="arc",
            outline=purple,
            width=stroke,
        )
        canvas.create_text(sx(cx), sy(cy - 8), text=f"{percent}%", anchor="center", font=("Segoe UI", max(10, int(20 * scale)), "bold"), fill="#000000")
        canvas.create_text(sx(cx), sy(cy + 24), text=get_feed_level_label(percent), anchor="center", font=("Segoe UI", max(7, int(10 * scale)), "bold"), fill=purple)

    def _draw_home_icon(self, canvas, sx, sy, scale, x, y, color="#000000"):
        # Ikon home sederhana di sidebar.
        w = self._stroke(4, scale)
        canvas.create_line(
            sx(x), sy(y + 15), sx(x + 16), sy(y), sx(x + 32), sy(y + 15),
            sx(x + 32), sy(y + 32), sx(x + 22), sy(y + 32), sx(x + 22), sy(y + 19),
            sx(x + 10), sy(y + 19), sx(x + 10), sy(y + 32), sx(x), sy(y + 32),
            sx(x), sy(y + 15),
            fill=color,
            width=w,
            joinstyle="round",
        )

    def _draw_water_icon(self, canvas, sx, sy, scale, x, y, label=False, color="#000000"):
        # Ikon tetes air/pH sederhana di sidebar dan kartu kondisi air.
        w = self._stroke(4, scale)
        canvas.create_arc(sx(x), sy(y + 5), sx(x + 36), sy(y + 43), start=112, extent=285, style="arc", outline=color, width=w)
        canvas.create_line(sx(x + 18), sy(y), sx(x + 4), sy(y + 19), fill=color, width=w)
        canvas.create_line(sx(x + 18), sy(y), sx(x + 32), sy(y + 19), fill=color, width=w)
        if label:
            canvas.create_text(sx(x + 36), sy(y + 27), text="PH", anchor="w", font=("Segoe UI", max(8, self._stroke(18, scale)), "bold"), fill=color)

    def _draw_fish_icon(self, canvas, sx, sy, scale, x, y, color="#000000"):
        # Ikon ikan untuk fitur autofeeder.
        w = self._stroke(4, scale)
        canvas.create_oval(sx(x + 8), sy(y + 4), sx(x + 44), sy(y + 40), outline=color, width=w)
        canvas.create_polygon(sx(x + 5), sy(y + 22), sx(x - 4), sy(y + 12), sx(x - 4), sy(y + 32), fill="", outline=color, width=w)
        canvas.create_oval(sx(x + 25), sy(y + 13), sx(x + 30), sy(y + 18), fill=color, outline=color)
        canvas.create_oval(sx(x + 45), sy(y + 16), sx(x + 60), sy(y + 31), outline=color, width=w)
        canvas.create_line(sx(x + 44), sy(y + 22), sx(x + 54), sy(y + 22), fill=color, width=w)

    def _draw_feed_button_icon(self, canvas, sx, sy, scale, x, y):
        # Ikon kecil di samping teks Manual Feed.
        color = PRIMARY
        w = self._stroke(3, scale)
        canvas.create_line(sx(x + 4), sy(y + 2), sx(x + 4), sy(y + 26), fill=color, width=w)
        canvas.create_line(sx(x + 4), sy(y + 14), sx(x + 20), sy(y + 14), fill=color, width=w)
        canvas.create_oval(sx(x + 14), sy(y), sx(x + 28), sy(y + 14), outline=color, width=w)
        canvas.create_oval(sx(x + 14), sy(y + 14), sx(x + 28), sy(y + 28), outline=color, width=w)


if __name__ == "__main__":
    # Titik awal program. Tk() membuat window, lalu mainloop menjalankan aplikasi.
    root = tk.Tk()
    app = InotekApp(root)
    root.mainloop()
