import tkinter as tk


PRIMARY = "#9157f5"
FIGMA_WIDTH = 960
FIGMA_HEIGHT = 640


class WaterMonitoringPage:
    # Halaman laporan/monitoring air. Mode bisa "suhu" atau "ph".
    def __init__(self, app, mode="suhu"):
        self.app = app
        self.mode = mode
        self._last_canvas_size = None

    def render(self):
        self.app.clear()
        self.app.lock_window_size()

        canvas = tk.Canvas(self.app.window, bg="#f8f5fc", highlightthickness=0, bd=0)
        canvas.pack(expand=True, fill="both")
        canvas.tag_bind("home-nav", "<Button-1>", lambda _event: self.app.show_dashboard(self.app.current_user_name))
        canvas.tag_bind("water-nav", "<Button-1>", lambda _event: self.app.show_water_monitoring_page(self.mode))
        canvas.tag_bind("feed-nav", "<Button-1>", lambda _event: self.app.show_schedule_page())
        canvas.tag_bind("tab-suhu", "<Button-1>", lambda _event: self.switch_mode("suhu"))
        canvas.tag_bind("tab-ph", "<Button-1>", lambda _event: self.switch_mode("ph"))
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

    def switch_mode(self, mode):
        self.mode = mode
        self.render()

    def draw(self, canvas):
        self._last_canvas_size = (canvas.winfo_width(), canvas.winfo_height())
        canvas.delete("all")
        canvas.configure(bg="#f8f5fc")
        reading = self.app.sensor.read_water_quality()
        water_status = self.app.get_water_status(reading.temperature, reading.ph)
        self.app.save_water_reading(reading, water_status)
        temp_health = self.app.get_device_health(reading.temperature, getattr(reading, "sensor_temp_status", "active"))
        ph_health = self.app.get_device_health(reading.ph, getattr(reading, "sensor_ph_status", "active"))
        water_health = temp_health if temp_health["active"] and ph_health["active"] else {"label": "Tidak Aktif", "color": "#95A5A6", "active": False}

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
        self.app._draw_icon_image(canvas, sx, sy, scale, "home hitam.png", 22, 235, 38, 38, fallback=lambda: self.app._draw_home_icon(canvas, sx, sy, scale, 24, 243))
        self.app._draw_icon_image(canvas, sx, sy, scale, "water ungu.png", 18, 294, 52, 52, fallback=lambda: self.app._draw_water_icon(canvas, sx, sy, scale, 21, 302, label=True, color=PRIMARY))
        self.app._draw_icon_image(canvas, sx, sy, scale, "fish hitam.png", 15, 360, 50, 50, fallback=lambda: self.app._draw_fish_icon(canvas, sx, sy, scale, 17, 367))
        self._sidebar_hitbox(canvas, sx, sy, 206, 284, "home-nav")
        self._sidebar_hitbox(canvas, sx, sy, 284, 352, "water-nav")
        self._sidebar_hitbox(canvas, sx, sy, 352, 430, "feed-nav")

        rect(90, 20, 820, 598, 45, "#ffffff")
        self.app._draw_icon_image(canvas, sx, sy, scale, "water ungu.png", 116, 37, 58, 58, fallback=lambda: self.app._draw_water_icon(canvas, sx, sy, scale, 120, 39, label=True, color=PRIMARY))
        text(192, 43, "Kondisi Air Terkini", 28, "bold")
        circle(196, 80, 12, water_health["color"])
        text(213, 74, water_health["label"], 16)
        self._tab(rect, text, "Suhu", 270, self.mode == "suhu", "tab-suhu")
        self._tab(rect, text, "pH air", 355, self.mode == "ph", "tab-ph")
        rect(760, 40, 170, 50, 10, "#eeedfe", shadow=True, tags="history-water")
        text(805, 55, "Riwayat Air", 16, "bold", tags="history-water")
        text(890, 52, ">", 18, "bold", PRIMARY, tags="history-water")
        line(150, 120, 875, 120, PRIMARY, 1)

        text(160, 140, "Senin, 17 April 2026", 16, "bold")
        text(160, 160, self.app.format_last_synced(reading.last_synced), 64, "bold")
        text(166, 235, "Terakhir diperbarui", 16, fill="#646464")

        title = "Suhu" if self.mode == "suhu" else "pH air"
        mode_health = temp_health if self.mode == "suhu" else ph_health
        current_value = reading.temperature if self.mode == "suhu" and temp_health["active"] else reading.ph if self.mode == "ph" and ph_health["active"] else "-"
        average_value = "8.1" if self.mode == "ph" else "28.4"
        accent = "#19a8ff" if self.mode == "suhu" else PRIMARY
        fill = "#dff4ff" if self.mode == "suhu" else "#efe6ff"
        self.app._metric_card(canvas, sx, sy, fs, rect, line, 405, 140, title, str(current_value), "", "#eeedfe")
        status = water_status if mode_health["active"] else mode_health
        self._summary_card(rect, text, line, 575, 140, "Status", status["label"], "#e6f1fb", status["color"])
        self._summary_card(rect, text, line, 750, 140, "Rata-rata", average_value, "#eeedfe", "#000000")

        if self.mode == "ph":
            self._draw_ph_bar(canvas, sx, sy, scale)

        chart_title = "Grafik Suhu" if self.mode == "suhu" else "Grafik pH air"
        text(166, 305, chart_title, 18, "bold")
        text(770, 292, "Status air\nBatas normal", 13, fill="#000000")
        canvas.create_rectangle(sx(760), sy(292), sx(768), sy(300), fill="#000000", outline="#000000")
        line(758, 313, 768, 313, "#000000", 1, dash=(4, 2))
        self._draw_chart(canvas, sx, sy, fs, line, text, accent, fill)

    def _tab(self, rect, text, label, x, active, tag):
        fill = "#eeedfe" if active else "#d9d9d9"
        fg = "#000000" if active else "#555555"
        rect(x, 72, 85, 26, 14, fill, "#c8c8c8", 1, tags=tag)
        text(x + 28, 78, label, 11, "bold", fg, tags=tag)

    def _summary_card(self, rect, text, line, x, y, title, value, fill, value_color):
        rect(x, y, 155, 115, 18, fill, shadow=True)
        text(x + 42, y + 15, title, 22, "bold")
        line(x + 20, y + 42, x + 135, y + 42, "#000000", 1)
        text(x + 47, y + 65, value, 22, "bold", value_color)

    def _draw_ph_bar(self, canvas, sx, sy, scale):
        colors = ["#e91b2d", "#f25f21", "#f5a20a", "#ffe700", "#cde500", "#7bc143", "#36c08b", "#16a0a5", "#295ab5", "#3e2aaa"]
        x = 115
        for color in colors:
            canvas.create_rectangle(sx(x), sy(267), sx(x + 78), sy(282), fill=color, outline=color)
            x += 78

    def _draw_chart(self, canvas, sx, sy, fs, line, text, accent, fill):
        left, top, right, bottom = 140, 340, 885, 545
        values = [6, 3, 10, 10, 12.5, 5, 8]
        times = ["11.00", "13.00", "14.00", "15.00", "16.00", "17.00", "18.00", "19.00"]
        max_value = 20

        for value in [0, 4, 8, 12, 16, 20]:
            y = bottom - (value / max_value) * (bottom - top)
            line(left, y, right, y, "#dddddd", 1, dash=(2, 2))
            text(left - 28, y - 7, str(value), 10, fill="#a0a0a0")
        line(left, bottom, right, bottom, "#aaaaaa", 1)
        line(left, top, left, bottom, "#aaaaaa", 1)
        line(left + 8, top + 5, left, top, "#aaaaaa", 1)
        line(right - 8, bottom - 5, right, bottom, "#aaaaaa", 1)
        line(left + 10, top + 45, right - 20, top + 45, "#000000", 1, dash=(4, 2))

        points = []
        for index, value in enumerate(values):
            x = left + 30 + index * 105
            y = bottom - (value / max_value) * (bottom - top)
            points.extend([sx(x), sy(y)])
        area_points = [sx(left + 30), sy(bottom)] + points + [sx(left + 30 + (len(values) - 1) * 105), sy(bottom)]
        canvas.create_polygon(area_points, fill=fill, outline="")
        canvas.create_line(points, fill=accent, width=max(2, int(2 * self.app.height / FIGMA_HEIGHT)), smooth=True)
        for i in range(0, len(points), 2):
            r = 4
            canvas.create_oval(points[i] - r, points[i + 1] - r, points[i] + r, points[i + 1] + r, fill=accent, outline="#ffffff")

        for index, label in enumerate(times):
            text(left + 20 + index * 95, bottom + 20, label, 9, fill="#a0a0a0")

        tooltip_x = left + 440
        tooltip_y = top + 85
        self.app._dashboard_round_rect(canvas, sx(tooltip_x), sy(tooltip_y), sx(tooltip_x + 105), sy(tooltip_y + 38), 4, "#7e7e7e", "#7e7e7e", 0, None)
        canvas.create_rectangle(sx(tooltip_x + 12), sy(tooltip_y + 12), sx(tooltip_x + 24), sy(tooltip_y + 24), fill="#61e0c2", outline="#61e0c2")
        label = "Suhu: 12" if self.mode == "suhu" else "pH air: 12"
        text(tooltip_x + 30, tooltip_y + 12, label, 10, fill="#ffffff")

    def _sidebar_hitbox(self, canvas, sx, sy, y1, y2, tag):
        # Area klik sidebar dibuat lebih besar dari icon agar mudah disentuh di LCD.
        canvas.create_rectangle(sx(0), sy(y1), sx(78), sy(y2), fill="", outline="", tags=tag)
