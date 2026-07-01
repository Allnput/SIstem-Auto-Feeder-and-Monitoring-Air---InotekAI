import tkinter as tk
from datetime import datetime

# from cv2 import circle
from matplotlib import text


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
        canvas.tag_bind("notif-nav", "<Button-1>", lambda _event: self.app.show_schedule_page())
        canvas.tag_bind("history-water", "<Button-1>", lambda _event: self.app.show_water_history())
        canvas.update_idletasks()
        self.draw(canvas)
        canvas.bind("<Configure>", self._redraw_when_resized)

    def _redraw_when_resized(self, event):
        size = (event.width, event.height)
        if size == self._last_canvas_size:
            return
        self._last_canvas_size = size
        self.draw(event.widget)

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
        scale = min(width / self.app.width, height / self.app.height)
        ox = (width - self.app.width * scale) / 2
        oy = (height - self.app.height * scale) / 2
        x_ratio = self.app.width / FIGMA_WIDTH
        y_ratio = self.app.height / FIGMA_HEIGHT
        
        

        def sx(value):
            return ox + value * x_ratio * scale

        def sy(value):
            return oy + value * y_ratio * scale

        def fs(size):
            return max(7, int(size * y_ratio * scale))

        def rect(x, y, w, h, r, fill, outline="", width=0, shadow=False, tags=None):
            if shadow:
                self.app._dashboard_round_rect(canvas, sx(x + 4), sy(y + 5), sx(x + w + 4), sy(y + h + 5), r * y_ratio * scale, "#c9c9c9", "#c9c9c9", 0, None)
            self.app._dashboard_round_rect(canvas, sx(x), sy(y), sx(x + w), sy(y + h), r * y_ratio * scale, fill, outline or fill, width, tags)

        def text(x, y, value, size, weight="normal", fill="#000000", anchor="nw", tags=None, justify="left"):
            canvas.create_text(sx(x), sy(y), text=value, fill=fill, anchor=anchor, justify=justify, font=("Segoe UI", fs(size), weight), tags=tags)

        def line(x1, y1, x2, y2, fill=PRIMARY, width=1, dash=None):
            canvas.create_line(sx(x1), sy(y1), sx(x2), sy(y2), fill=fill, width=max(1, int(width * scale)), dash=dash)

        def circle(x, y, size, fill, tags=None):
            canvas.create_oval(sx(x), sy(y), sx(x + size), sy(y + size), fill=fill, outline=fill, tags=tags)

        canvas.create_rectangle(0, 0, width, height, fill="#f8f5fc", outline="#f8f5fc")

        rect(0, 0, 78, 640, 0, "#ffffff", shadow=True)
        rect(8, 20, 61, 52, 0, "#faf7ff")
        self.app._draw_icon_image(canvas, sx, sy, scale, "logo inotekai.jpeg", 8, 20, 61, 52, fallback=lambda: text(12, 35, "InotekAI", 10, "bold", PRIMARY))
        self.app._draw_icon_image(canvas, sx, sy, scale, "home ungu.png", 22, 235, 38, 38, fallback=lambda: self.app._draw_home_icon(canvas, sx, sy, scale, 24, 243, PRIMARY))
        self.app._draw_icon_image(canvas, sx, sy, scale, "water hitam.png", 22, 300, 42, 42, fallback=lambda: self.app._draw_water_icon(canvas, sx, sy, scale, 21, 302, label=True))
        self.app._draw_icon_image(canvas, sx, sy, scale, "notif hitam.png", 15, 360, 50, 50, fallback=lambda: self.app._draw_notif_icon(canvas, sx, sy, scale, 17, 367))
        self._sidebar_hitbox(canvas, sx, sy, 206, 284, "home-nav")
        self._sidebar_hitbox(canvas, sx, sy, 284, 352, "water-nav")
        self._sidebar_hitbox(canvas, sx, sy, 352, 430, "notif-nav")

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
            # Urutan index sesuai dengan query SELECT di database: 
            # 0: ph_level, 1: ph_status_label, 2: ph_status_color, 3: timestamp
            last_ph = latest_record[0][0]
            last_label = latest_record[0][1]
            last_color = latest_record[0][2]
            last_time_str = latest_record[0][3]
            
            # Konversi waktu dari string database menjadi tipe datetime
            try:
                last_time = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                last_time = datetime.now()
        else:
            # Fallback jika database masih kosong sama sekali
            last_ph = "-"
            last_label = "Data kosong"
            last_color = "#E74C3C"
            last_time = datetime.now()

        # 2. Tampilkan Waktu Terakhir Diperbarui (Dari Database)
        text(131, 140, self.app.format_today(last_time), 16, "bold")
        text(112, 135, self.app.format_last_synced(last_time), 64, "bold")
        text(128, 238, "Terakhir diperbarui", 16, "bold", "#646464")

        # 3. Tampilkan Nilai pada Kartu Monitoring (Dari Database)
        title = "pH air"
        current_value = last_ph if self.mode == "ph" and ph_health["active"] else "-"
        # average_value = self.app.format_number(average_ph if self.mode == "ph" and ph_health["active"] else "-")
        
        self.app._monitoring_card(canvas, sx, sy, fs, rect, line, 403, 135, title, str(current_value), "", "#eeedfe")
        
        # 4. Tampilkan Status pada Kartu Summary (Dari Database)
        status_label = last_label if ph_health["active"] else ph_health["label"]
        status_color = last_color if ph_health["active"] else ph_health["color"]
        
        self._summary_card(rect, text, line, 575, 135, "Status", status_label, "#e6f1fb", status_color)
        
        if self.mode == "ph":
            chart_data = []
            today_date = datetime.now().date() # Dapatkan tanggal hari ini
            
            for row in today_readings:
                val, dt = self.app.row_value_time(row, "ph")
                
                # Validasi: Hanya tambahkan ke grafik JIKA tanggalnya adalah HARI INI
                if val is not None and dt is not None and dt.date() == today_date:
                    chart_data.append({"time": dt, "value": val})
            
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
        

    def _summary_card(self, rect, text, line, x, y, title, value, fill, value_color):
        padding_y = 15
        width = 330
        height = 115
        rect(x, y, width, height, 18, fill, shadow=True)

        center_x = x + width / 2

        title_y = y + padding_y
        line_y = title_y + 37
        value_y = y + height / 2 + 15

        text(center_x, title_y + 8, title, 22, "bold", fill="#000000", anchor="center")
        line(x + 20, line_y - 7, x + width - 20, line_y - 7, "#000000", 1)
        text(center_x + 1, value_y + 5, value, 32, "bold", value_color, anchor="center")

    def _sidebar_hitbox(self, canvas, sx, sy, y1, y2, tag):
        # Area klik sidebar dibuat lebih besar dari icon agar mudah disentuh di LCD.
        canvas.create_rectangle(sx(0), sy(y1), sx(78), sy(y2), fill="", outline="", tags=tag)