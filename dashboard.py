import tkinter as tk
from datetime import datetime

PRIMARY = "#9157f5"
FIGMA_WIDTH = 960
FIGMA_HEIGHT = 640
PH_MIN = 0
PH_MAX = 15
PH_TICKS = [0, 3, 6, 9, 12, 15]
FOUR_HOUR_LABELS = [f"{hour:02d}.00" for hour in range(0, 24, 4)]
CHART_AXIS_LABELS = FOUR_HOUR_LABELS + ["00.59"]

class DashboardPage:
    def __init__(self, app,user_name, mode="ph"):
        
        self.app = app
        self.user_name = user_name
        self.mode = mode
        self._last_canvas_size = None
        self._selected_bucket_index = None
        
    def render(self):
        self.app.clear()
        self.app.lock_window_size()

        canvas = tk.Canvas(self.app.window, bg="#f8f5fc", highlightthickness=0, bd=0)
        canvas.pack(expand=True, fill="both")
        canvas.tag_bind("home-nav", "<Button-1>", lambda _event: self.app.show_dashboard(self.app.current_user_name, mode="ph"))
        canvas.tag_bind("water-nav", "<Button-1>", lambda _event: self.app.show_water_history())
        canvas.tag_bind("notif-nav", "<Button-1>", lambda _event: self.app.show_notification())
        canvas.tag_bind("history-water", "<Button-1>", lambda _event: self.app.show_water_history())
        canvas.update_idletasks()
        self.draw(canvas)
        canvas.bind("<Configure>", self.app.redraw_when_resized)
        self._start_auto_refresh(canvas)

    def _start_auto_refresh(self, canvas, interval_ms=2000):
        """
        Gambar ulang dashboard tiap `interval_ms` supaya data pH dari
        Arduino (lihat serial_reader.py) selalu ter-update di layar,
        bukan cuma sekali saat halaman pertama kali dibuka.
        Loop otomatis berhenti kalau halaman ini sudah ditinggalkan
        (mis. pindah ke halaman lain), jadi tidak menumpuk di background.
        """
        def tick():
            if not canvas.winfo_exists():
                return
            self.draw(canvas)
            canvas.after(interval_ms, tick)

        canvas.after(interval_ms, tick)

    def draw(self, canvas):
        self._last_canvas_size = (canvas.winfo_width(), canvas.winfo_height())
        canvas.delete("all")
        canvas.configure(bg="#f8f5fc")
        reading = self.app.sensor.read_water_quality()
        ph_status_label = self.app.ph_status(reading.ph)["label"]
        ph_status_color = self.app.ph_status(reading.ph)["color"]
        self.app.save_water_reading(reading, ph_status_label, ph_status_color, reading.last_synced)
        ph_health = self.app.get_device_health(reading.ph, getattr(reading, "sensor_ph_status", "active"))

        width = max(canvas.winfo_width(), self.app.width)
        height = max(canvas.winfo_height(), self.app.height)

        sx, sy, fs, rect, text, line, scale = self.app.get_canvas_helpers(canvas)

        def circle(x, y, size, fill, tags=None):
            canvas.create_oval(sx(x), sy(y), sx(x + size), sy(y + size), fill=fill, outline=fill, tags=tags)

        canvas.create_rectangle(0, 0, width, height, fill="#f8f5fc", outline="#f8f5fc")
        reading = self.app.sensor.read_water_quality()
        status = self.app.ph_status(reading.ph)
        rect(0, 0, 78, 640, 0, "#ffffff", shadow=True)
        self.app.draw_sidebar(canvas, sx, sy, scale)

        self.app.draw_universal_card(
            rect, text, line, 
            x=575, y=135, width=330, height=115, 
            title="Status", value=status["label"], 
            fill="#e6f1fb", value_color=status["color"], 
            show_line=True
        )
        rect(90, 20, 845, 600, 45, "#ffffff", shadow=True)
        self.app._draw_icon_image(canvas, sx, sy, scale, "water ungu.png", 116, 37, 58, 58, fallback=lambda: self.app._draw_water_icon(canvas, sx, sy, scale, 120, 39, label=True, color=PRIMARY))
        text(192, 43, "Kondisi pH Air Terkini", 24, "bold")        
        circle(196, 85, 12, ph_health["color"])
        text(213, 77, ph_health["label"], 16)

        rect(740, 40, 170, 50, 10, "#eeedfe", shadow=True, tags="history-water")
        text(773, 55, "Riwayat Air", 16, "bold", tags="history-water")
        text(887, 52, ">", 18, "bold", PRIMARY, tags="history-water")
        line(150, 120, 875, 120, PRIMARY, 1)

        today_readings = self.app.get_today_ph_readings()
        if not today_readings:
            today_readings = [{
                "ph": reading.ph,
                "last_synced": reading.last_synced if isinstance(reading.last_synced, datetime) else datetime.now(),
            }]

        latest_record = self.app.db.get_water_history(limit=1)
        
        if latest_record:
            last_ph = latest_record[0][0]
            last_label = latest_record[0][1]
            last_color = latest_record[0][2]
            last_time_str = latest_record[0][3]

            try:
                last_time = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                last_time = datetime.now()
        else:
            last_ph = "-"
            last_label = "Data kosong"
            last_color = "#E74C3C"
            last_time = datetime.now()

        text(131, 140, self.app.format_today(last_time), 16, "bold")
        text(112, 135, self.app.format_last_synced(last_time), 64, "bold")
        text(128, 238, "Terakhir diperbarui", 16, "bold", "#646464")

        title = "pH air"
        current_value = last_ph if self.mode == "ph" and ph_health["active"] else "-"
        self.app._monitoring_card(canvas, sx, sy, fs, rect, line, 403, 135, title, str(current_value), "", "#eeedfe")
        
        status_label = last_label if ph_health["active"] else ph_health["label"]
        status_color = last_color if ph_health["active"] else ph_health["color"]
        
        self.app.draw_universal_card(
        rect, text, line, 
        x=575, y=135, 
        width=330, height=115, 
        title="Status", value=status_label, 
        fill="#e6f1fb", value_color=status_color, 
        show_line=True)
        
        if self.mode == "ph":
            hourly_buckets = {hour: [] for hour in range(24)}
            today_date = datetime.now().date()

            for row in today_readings:
                val, dt = self.app.row_value_time(row, "ph")

                if val is not None and dt is not None and dt.date() == today_date:
                    hourly_buckets[dt.hour].append(val)

            chart_data = []
            for hour, values in hourly_buckets.items():
                if values:  # Pastikan keranjangnya tidak kosong
                    avg_value = sum(values) / len(values)
                    dt_hour = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
                    
                    chart_data.append({
                        "time": dt_hour, 
                        "value": avg_value
                    })
            
            self.app.draw_ph_bar(canvas, sx, sy, scale)
            self.app.draw_chart_today(canvas, sx, sy, fs, line, text, PRIMARY, PRIMARY, chart_data)
                
        chart_title = "Grafik pH air"
        text(166, 325, chart_title, 18, "bold") if self.mode == "ph" else text(166, 300, chart_title, 18, "bold")
        legend_y = 325 if self.mode == "ph" else 325
        text(800, legend_y - 10, "Status air", 13, fill="#000000")
        text(800, legend_y + 8, "Batas normal", 13, fill="#000000")
        canvas.create_rectangle(sx(780), sy(legend_y), sx(788), sy(legend_y + 8), fill=status_color, outline="#000000")
        line(775, legend_y + 21, 793, legend_y + 21, "#000000", 1, dash=(4, 2))

    def _tab(self, rect, text, label, x, y,active, tag):
        fill = "#eeedfe" if active else "#d9d9d9"
        fg = "#000000" if active else "#555555"
        rect(x + 5, y, 85, 26, 14, fill,PRIMARY if active else"#c8c8c8", 1, tags=tag)
        text(x + 28, y + 2, label, 11, "bold", fg, tags=tag)