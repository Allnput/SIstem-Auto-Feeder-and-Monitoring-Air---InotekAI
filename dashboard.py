import tkinter as tk


PRIMARY = "#9157f5"
FIGMA_WIDTH = 960
FIGMA_HEIGHT = 640


class DashboardPage:
    # Halaman dashboard utama setelah login berhasil.
    def __init__(self, app, user_name):
        self.app = app
        self.user_name = user_name
        self._last_canvas_size = None

    def render(self):
        self.app.clear()
        self.app.lock_window_size()

        canvas = tk.Canvas(self.app.window, bg="#f3f4f4", highlightthickness=0, bd=0)
        canvas.pack(expand=True, fill="both")
        canvas.tag_bind("manual-feed", "<Button-1>", lambda _event: self.app.manual_feed())
        canvas.tag_bind("report", "<Button-1>", lambda _event: self.app.show_water_monitoring_page("suhu"))
        canvas.tag_bind("schedule", "<Button-1>", lambda _event: self.app.show_schedule_page())
        canvas.tag_bind("home-nav", "<Button-1>", lambda _event: self.app.show_dashboard(self.app.current_user_name))
        canvas.tag_bind("water-nav", "<Button-1>", lambda _event: self.app.show_water_monitoring_page("suhu"))
        canvas.tag_bind("feed-nav", "<Button-1>", lambda _event: self.app.show_schedule_page())
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
        canvas.configure(bg="#f3f4f4")
        reading = self.app.sensor.read_water_quality()
        water_status = self.app.get_water_status(reading.temperature, reading.ph)
        self.app.save_water_reading(reading, water_status)
        temp_health = self.app.get_device_health(reading.temperature, getattr(reading, "sensor_temp_status", "active"))
        ph_health = self.app.get_device_health(reading.ph, getattr(reading, "sensor_ph_status", "active"))
        water_health = temp_health if temp_health["active"] and ph_health["active"] else {"label": "Tidak Aktif", "color": "#95A5A6", "active": False}
        feeder_health = self.app.get_device_health(reading, getattr(reading, "auto_feeder_status", "active"))
        feed_percent = getattr(reading, "feed_percentage", 0)
        today_schedule = self.app.get_today_schedule()

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

        def line(x1, y1, x2, y2, fill=PRIMARY, width=1):
            canvas.create_line(sx(x1), sy(y1), sx(x2), sy(y2), fill=fill, width=max(1, int(width * scale)))

        def circle(x, y, size, fill, tags=None):
            canvas.create_oval(sx(x), sy(y), sx(x + size), sy(y + size), fill=fill, outline=fill, tags=tags)

        canvas.create_rectangle(0, 0, width, height, fill="#f3f4f4", outline="#f3f4f4")

        rect(0, 0, 78, 640, 0, "#ffffff", shadow=True)
        rect(8, 20, 61, 52, 0, "#faf7ff")
        self.app._draw_icon_image(canvas, sx, sy, scale, "logo inotekai.jpeg", 8, 20, 61, 52, fallback=lambda: text(12, 35, "InotekAI", 10, "bold", PRIMARY))
        self.app._draw_icon_image(canvas, sx, sy, scale, "home ungu.png", 22, 235, 38, 38, fallback=lambda: self.app._draw_home_icon(canvas, sx, sy, scale, 24, 243, PRIMARY))
        self.app._draw_icon_image(canvas, sx, sy, scale, "water hitam.png", 22, 300, 42, 42, fallback=lambda: self.app._draw_water_icon(canvas, sx, sy, scale, 21, 302, label=True))
        self.app._draw_icon_image(canvas, sx, sy, scale, "fish hitam.png", 15, 360, 50, 50, fallback=lambda: self.app._draw_fish_icon(canvas, sx, sy, scale, 17, 367))
        self._sidebar_hitbox(canvas, sx, sy, 206, 284, "home-nav")
        self._sidebar_hitbox(canvas, sx, sy, 284, 352, "water-nav")
        self._sidebar_hitbox(canvas, sx, sy, 352, 430, "feed-nav")

        rect(90, 20, 610, 290, 45, "#ffffff", shadow=True)
        self.app._draw_icon_image(canvas, sx, sy, scale, "water ungu.png", 116, 37, 58, 58, fallback=lambda: self.app._draw_water_icon(canvas, sx, sy, scale, 120, 39, label=True, color=PRIMARY))
        text(192, 43, "Kondisi Air Terkini", 24, "bold")
        circle(196, 85, 12, water_health["color"])
        text(213, 77, water_health["label"], 16)
        text(112, 135, self.app.format_last_synced(reading.last_synced), 64, "bold")
        text(124, 238, "Terakhir diperbarui", 16, "bold", "#646464")

        rect(500, 35, 180, 50, 10, "#eeedfe", shadow=True, tags="report")
        text(515, 48, "Lihat Laporan", 16, "bold", tags="report")
        text(650, 45, ">", 18, "bold", PRIMARY, tags="report")

        ph_value = str(reading.ph) if ph_health["active"] else "-"
        temp_value = str(reading.temperature) if temp_health["active"] else "-"
        ph_status = water_status if ph_health["active"] else ph_health
        temp_status = water_status if temp_health["active"] else temp_health
        self.app._metric_card(canvas, sx, sy, fs, rect, line, 352, 110, "pH Air", ph_value, ph_status["label"], "#eeedfe", ph_status["color"])
        self.app._metric_card(canvas, sx, sy, fs, rect, line, 530, 110, "Suhu Air", temp_value, temp_status["label"], "#e6f1fb", temp_status["color"])

        rect(715, 24, 220, 286, 24, "#ffffff", shadow=True)
        text(755, 43, "Sisa Pakan", 24, "bold")
        self.app._draw_feed_gauge(canvas, sx, sy, scale, 825, 190, feed_percent)

        rect(93, 335, 610, 282, 40, "#ffffff", shadow=True)
        self.app._draw_icon_image(canvas, sx, sy, scale, "fish ungu.png", 114, 360, 65, 65, fallback=lambda: self.app._draw_fish_icon(canvas, sx, sy, scale, 120, 365, color=PRIMARY))
        text(193, 360, "Auto Feeder Status", 24, "bold")
        circle(196, 402, 12, feeder_health["color"])
        text(213, 396, feeder_health["label"], 16)
        rect(500, 355, 180, 50, 10, "#eeedfe", shadow=True, tags="schedule")
        text(515, 370, "Jadwal Pakan", 16, "bold", tags="schedule")
        text(650, 368, ">", 18, "bold", PRIMARY, tags="schedule")
        line(133, 435, 673, 435, PRIMARY, 1)
        text(140, 456, "Jadwal hari ini", 24)
        if today_schedule:
            for index, schedule in enumerate(today_schedule[:3]):
                row_y = 505 + index * 31
                fill = "#000000" if schedule["status"] == "Next" else "#c0c0c0"
                text(145, row_y, schedule["time"], 24, fill=fill)
                self.app._pill(canvas, sx, sy, fs, 544, row_y, 112, schedule["status_text"], schedule["status_bg"], schedule["status_fg"])
        else:
            text(140, 510, "Belum ada jadwal hari ini", 18, "bold", "#8b8b8b")

        card_fill = "#ffffff" if feeder_health["active"] else "#f2f2f2"
        button_fill = "#eeedfe" if feeder_health["active"] else "#d9d9d9"
        manual_tag = "manual-feed" if feeder_health["active"] else None
        text_fill = "#000000" if feeder_health["active"] else "#7f8c8d"
        rect(715, 335, 225, 282, 30, card_fill, shadow=True)
        circle(736, 352, 12, feeder_health["color"])
        text(752, 346, feeder_health["label"], 16, fill=text_fill)
        text(775, 437, "Manual\nFeed", 24, "bold", justify="center")
        self.app._draw_icon_image(canvas, sx, sy, scale, "fish ungu.png", 865, 490, 28, 28, fallback=lambda: self.app._draw_feed_button_icon(canvas, sx, sy, scale, 876, 491))
        rect(724, 570, 210, 35, 28, button_fill, tags=manual_tag)
        text(734, 575, "Tap untuk memberi makan", 15, fill=text_fill, tags=manual_tag)

    def _sidebar_hitbox(self, canvas, sx, sy, y1, y2, tag):
        # Area klik sidebar dibuat lebih besar dari icon agar mudah disentuh di LCD.
        canvas.create_rectangle(sx(0), sy(y1), sx(78), sy(y2), fill="", outline="", tags=tag)
