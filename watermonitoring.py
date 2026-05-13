import tkinter as tk
from datetime import datetime

from cv2 import circle
from matplotlib import text


PRIMARY = "#9157f5"
FIGMA_WIDTH = 960
FIGMA_HEIGHT = 640
TEMP_MIN = 10
TEMP_MAX = 35
TEMP_TICKS = [10, 15, 20, 25, 30, 35]
TEMP_NORMAL_MIN = 23
TEMP_NORMAL_MAX = 28
PH_MIN = 0
PH_MAX = 15
PH_TICKS = [0, 3, 6, 9, 12, 15]
FOUR_HOUR_LABELS = [f"{hour:02d}.00" for hour in range(0, 24, 4)]
CHART_AXIS_LABELS = FOUR_HOUR_LABELS + ["00.59"]
USE_DUMMY_WATER_CHART_DATA = True


class WaterMonitoringPage:
    # Halaman laporan/monitoring air. Mode bisa "suhu" atau "ph".
    def __init__(self, app, mode="suhu"):
        self.app = app
        self.mode = mode
        self._last_canvas_size = None
        self._selected_bucket_index = None

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
        self._selected_bucket_index = None
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
        self.app._draw_icon_image(canvas, sx, sy, scale, "water ungu.png", 22, 300, 42, 42, fallback=lambda: self.app._draw_water_icon(canvas, sx, sy, scale, 21, 302, label=True, color=PRIMARY))
        self.app._draw_icon_image(canvas, sx, sy, scale, "fish hitam.png", 15, 360, 50, 50, fallback=lambda: self.app._draw_fish_icon(canvas, sx, sy, scale, 17, 367))
        self._sidebar_hitbox(canvas, sx, sy, 206, 284, "home-nav")
        self._sidebar_hitbox(canvas, sx, sy, 284, 352, "water-nav")
        self._sidebar_hitbox(canvas, sx, sy, 352, 430, "feed-nav")

        # rect(90, 20, 845, 610, 45, "#ffffff", shadow=True)
        rect(90, 20, 845, 610, 45, "#ffffff", shadow=True)
        self.app._draw_icon_image(canvas, sx, sy, scale, "water ungu.png", 116, 37, 58, 58, fallback=lambda: self.app._draw_water_icon(canvas, sx, sy, scale, 120, 39, label=True, color=PRIMARY))
        text(192, 43, "Kondisi Air Terkini", 24, "bold")        
        circle(196, 85, 12, water_health["color"])
        text(213, 77, water_health["label"], 16)
        self._tab(rect, text, "Suhu", 270, 85, self.mode == "suhu", "tab-suhu")
        self._tab(rect, text, "pH air", 360, 85, self.mode == "ph", "tab-ph")
        rect(740, 40, 170, 50, 10, "#eeedfe", shadow=True, tags="history-water")
        text(773, 55, "Riwayat Air", 16, "bold", tags="history-water")
        text(887, 52, ">", 18, "bold", PRIMARY, tags="history-water")
        line(150, 120, 875, 120, PRIMARY, 1)

        today_readings = self.app.get_today_water_readings()
        if USE_DUMMY_WATER_CHART_DATA:
            today_readings = self._dummy_water_readings(reading.last_synced)
        elif not today_readings:
            today_readings = [{
                "temperature": reading.temperature,
                "ph": reading.ph,
                "last_synced": reading.last_synced if isinstance(reading.last_synced, datetime) else datetime.now(),
            }]
        bucketed_temperature = self._four_hour_average(today_readings, "temperature")
        bucketed_ph = self._four_hour_average(today_readings, "ph")
        average_temperature = self._average_temperature(today_readings)
        average_ph = self._average_ph(today_readings)
        current_temp_status = self._temperature_status(reading.temperature) if temp_health["active"] else temp_health
        current_ph_status = self._ph_status(reading.ph) if ph_health["active"] else ph_health

        text(131, 140, self._format_today(reading.last_synced), 16, "bold")
        text(112, 135, self.app.format_last_synced(reading.last_synced), 64, "bold")
        text(128, 238, "Terakhir diperbarui", 16, "bold", "#646464")


        title = "Suhu" if self.mode == "suhu" else "pH air"
        mode_health = temp_health if self.mode == "suhu" else ph_health
        current_value = reading.temperature if self.mode == "suhu" and temp_health["active"] else reading.ph if self.mode == "ph" and ph_health["active"] else "-"
        average_value = self._format_number(average_ph if self.mode == "ph" else average_temperature)
        accent = "#19a8ff" if self.mode == "suhu" else PRIMARY
        fill = "#19a8ff" if self.mode == "suhu" else PRIMARY
        self.app._monitoring_card(canvas, sx, sy, fs, rect, line, 403, 135, title, str(current_value), "", "#eeedfe")
        status = current_temp_status if self.mode == "suhu" and mode_health["active"] else current_ph_status if mode_health["active"] else mode_health
        self._summary_card(rect, text, line, 575, 135, "Status", status["label"], "#e6f1fb", status["color"])
        self._summary_card(rect, text, line, 750, 135, "Rata-rata", average_value, "#eeedfe", "#000000")

        if self.mode == "ph":
            self._draw_ph_bar(canvas, sx, sy, scale)

        chart_title = "Grafik Suhu" if self.mode == "suhu" else "Grafik pH air"
        text(166, 325, chart_title, 18, "bold") if self.mode == "ph" else text(166, 300, chart_title, 18, "bold")
        legend_y = 325 if self.mode == "ph" else 325
        text(800, legend_y - 10, "Status air", 13, fill="#000000") if self.mode == "ph" else text(800, legend_y - 30, "Status air", 13, fill="#000000")
        text(800, legend_y + 8, "Batas normal", 13, fill="#000000") if self.mode == "ph" else text(800, legend_y -10, "Batas normal", 13, fill="#000000")
        canvas.create_rectangle(sx(780), sy(legend_y), sx(788), sy(legend_y + 8), fill=status["color"], outline="#000000") if self.mode == "ph" else canvas.create_rectangle(sx(780), sy(legend_y - 20), sx(788), sy(legend_y - 12), fill=status["color"], outline="#000000")
        line(775, legend_y + 21, 793, legend_y + 21, "#000000", 1, dash=(4, 2)) if self.mode == "ph" else line(775, legend_y + 5, 793, legend_y + 5, "#000000", 1, dash=(4, 2))
        chart_values = bucketed_temperature if self.mode == "suhu" else bucketed_ph
        self._draw_chart(canvas, sx, sy, fs, line, text, accent, fill, chart_values) 

    def _tab(self, rect, text, label, x, y,active, tag):
        fill = "#eeedfe" if active else "#d9d9d9"
        fg = "#000000" if active else "#555555"
        rect(x + 5, y, 85, 26, 14, fill,PRIMARY if active else"#c8c8c8", 1, tags=tag)
        text(x + 28, y + 2, label, 11, "bold", fg, tags=tag)
        

    def _summary_card(self, rect, text, line, x, y, title, value, fill, value_color):
        # Padding untuk kotak
        padding_x = 20
        padding_y = 15

        # Hitung lebar kotak berdasarkan panjang teks value
        width = max(155, len(str(value)) * 15 + padding_x*2)
        height = 115  # bisa juga dibuat dinamis jika mau

        # Gambar rectangle
        rect(x, y, width, height, 18, fill, shadow=True)

        # Titik tengah kotak
        center_x = x + width / 2

        # Posisi teks relatif terhadap rectangle
        title_y = y + padding_y
        line_y = title_y + 37
        value_y = y + height / 2 + 15  # value berada di tengah ke bawah

# line(x + 16, y + 43, x + width - 16, y + 43, "#000000", 1)

        # Gambar teks dan garis
        text(center_x, title_y + 8, title, 22, "bold", fill="#000000", anchor="center")
        line(x + 20, line_y - 7, x + width - 20, line_y - 7, "#000000", 1)
        text(center_x + 1, value_y + 5, value, 32, "bold", value_color, anchor="center")

    def _draw_ph_bar(self, canvas, sx, sy, scale):
        colors = [
            "#d71920", "#f05a24", "#f7941d", "#ffd21f", "#fff200", "#d7df23", "#8dc63f",
            "#37b34a", "#55c7df", "#2f80c8", "#2464ad", "#6f63bf", "#6b3fa0", "#3f1d78",
        ]
        left, top, segment_width, height = 140, 275, 50, 16
        shaft_left = left + 22
        shaft_right = left + 22 + segment_width * len(colors)
        y_mid = top + height / 2
        canvas.create_polygon(
            sx(left), sy(y_mid),
            sx(shaft_left), sy(top - 8),
            sx(shaft_left), sy(top),
            sx(shaft_left), sy(top + height),
            sx(shaft_left), sy(top + height + 8),
            fill=colors[0],
            outline=colors[0],
        )
        x = shaft_left
        for color in colors:
            canvas.create_rectangle(sx(x), sy(top), sx(x + segment_width), sy(top + height), fill=color, outline=color)
            x += segment_width
        canvas.create_polygon(
            sx(shaft_right), sy(top - 8),
            sx(shaft_right + 22), sy(y_mid),
            sx(shaft_right), sy(top + height + 8),
            fill=colors[-1],
            outline=colors[-1],
        )
        canvas.create_text(sx(left + 92), sy(293), text="keasaman meningkat", anchor="n", font=("Segoe UI", max(7, int(5 * scale))), fill="#444444")
        canvas.create_text(sx(left + 375), sy(293), text="netral", anchor="n", font=("Segoe UI", max(7, int(5 * scale))), fill="#444444")
        canvas.create_text(sx(left + 650), sy(293), text="alkali/ basa meningkat", anchor="n", font=("Segoe UI", max(7, int(5 * scale))), fill="#444444")

    def _draw_chart(self, canvas, sx, sy, fs, line, text, accent, fill, values):
        left, top, right, bottom = 140, 365, 885, 590
        chart_min = TEMP_MIN if self.mode == "suhu" else PH_MIN
        chart_max = TEMP_MAX if self.mode == "suhu" else PH_MAX
        chart_ticks = TEMP_TICKS if self.mode == "suhu" else PH_TICKS
        times = CHART_AXIS_LABELS
        chart_width = right - left
        chart_height = bottom - top

        def y_for(value):
            bounded = max(chart_min, min(chart_max, float(value)))
            return bottom - ((bounded - chart_min) / (chart_max - chart_min)) * chart_height

        def x_for(index):
            denominator = max(1, len(CHART_AXIS_LABELS) - 1)
            return left + (index / denominator) * chart_width

        for value in chart_ticks:
            y = y_for(value)
            line(left, y, right, y, "#dddddd", 1, dash=(2, 2))
            text(left - 28, y - 7, str(value), 10, fill="#a0a0a0")
        line(left, bottom, right, bottom, "#aaaaaa", 1)
        line(left, top, left, bottom, "#aaaaaa", 1)
        line(left + 8, top + 5, left, top, "#aaaaaa", 1)
        line(right - 8, bottom - 5, right, bottom, "#aaaaaa", 1)
        if self.mode == "suhu":
            for boundary in (TEMP_NORMAL_MIN, TEMP_NORMAL_MAX):
                line(left, y_for(boundary), right, y_for(boundary), "#000000", 1, dash=(4, 2))
        else:
            for boundary in (6, 8):
                line(left, y_for(boundary), right, y_for(boundary), "#000000", 1, dash=(4, 2))

        def show_tooltip(selected_index):
            if selected_index is None or selected_index < 0 or selected_index >= len(values) or values[selected_index] is None:
                return
            self._selected_bucket_index = selected_index
            canvas.delete("chart-tooltip")
            tooltip_x = min(right - 140, max(left + 8, x_for(selected_index) - 55))
            tooltip_y = max(top + 12, y_for(values[selected_index]) - 64)
            self.app._dashboard_round_rect(canvas, sx(tooltip_x), sy(tooltip_y), sx(tooltip_x + 132), sy(tooltip_y + 48), 4, "#000000", "#000000", 0, "chart-tooltip")
            dot_color = self._dot_color(values[selected_index])
            canvas.create_oval(sx(tooltip_x + 12), sy(tooltip_y + 17), sx(tooltip_x + 24), sy(tooltip_y + 29), fill=dot_color, outline=dot_color, tags="chart-tooltip")
            value_label = "Suhu" if self.mode == "suhu" else "pH air"
            text(tooltip_x + 30, tooltip_y + 8, f"Rata-rata {self._bucket_range_label(selected_index)}", 8, fill="#ffffff", tags="chart-tooltip")
            text(tooltip_x + 30, tooltip_y + 24, f"{value_label}: {self._format_number(values[selected_index])}", 10, "bold", "#ffffff", tags="chart-tooltip")

        points = []
        point_items = []
        for index, value in enumerate(values):
            if value is None:
                continue
            x = x_for(index)
            y = y_for(value)
            points.extend([sx(x), sy(y)])
            point_items.append((index, value, x, y))
        if points:
            area_points = [points[0], sy(bottom)] + points + [points[-2], sy(bottom)]
            if self.mode == "ph":
                self._draw_ph_gradient_fill(canvas, sx, sy, point_items, bottom)
            else:
                self._draw_temperature_gradient_fill(canvas, sx, sy, point_items, bottom)
        if len(points) >= 4:
            canvas.create_line(points, fill=accent, width=max(2, int(2 * self.app.height / FIGMA_HEIGHT)), smooth=True)
        for index, value, x, y in point_items:
            r = 4
            dot_color = self._dot_color(value)
            tag = f"chart-point-{index}"
            canvas.create_oval(sx(x) - r, sy(y) - r, sx(x) + r, sy(y) + r, fill=dot_color, outline="#ffffff", tags=tag)
            canvas.tag_bind(tag, "<Button-1>", lambda _event, selected=index: show_tooltip(selected))

        for index, label in enumerate(times):
            text(x_for(index), bottom + 20, label, 7, fill="#a0a0a0", anchor="n")

        selected_index = self._selected_bucket_index
        if selected_index is not None:
            show_tooltip(selected_index)

    def _draw_ph_gradient_fill(self, canvas, sx, sy, point_items, bottom):
        self._draw_gradient_fill(canvas, sx, sy, point_items, bottom, self._ph_color)

    def _draw_temperature_gradient_fill(self, canvas, sx, sy, point_items, bottom):
        self._draw_gradient_fill(canvas, sx, sy, point_items, bottom, self._temperature_color)

    def _draw_gradient_fill(self, canvas, sx, sy, point_items, bottom, color_for_value):
        if len(point_items) == 1:
            _index, value, x, y = point_items[0]
            canvas.create_polygon(
                sx(x - 8), sy(bottom),
                sx(x), sy(y),
                sx(x + 8), sy(bottom),
                fill=color_for_value(value),
                outline="",
                stipple="gray50",
            )
            return

        for item_index in range(len(point_items) - 1):
            _start_index, start_value, start_x, start_y = point_items[item_index]
            _end_index, end_value, end_x, end_y = point_items[item_index + 1]
            steps = 18
            for step in range(steps):
                ratio_a = step / steps
                ratio_b = (step + 1) / steps
                x1 = start_x + (end_x - start_x) * ratio_a
                y1 = start_y + (end_y - start_y) * ratio_a
                x2 = start_x + (end_x - start_x) * ratio_b
                y2 = start_y + (end_y - start_y) * ratio_b
                color = self._mix_color(color_for_value(start_value), color_for_value(end_value), (ratio_a + ratio_b) / 2)
                canvas.create_polygon(
                    sx(x1), sy(bottom),
                    sx(x1), sy(y1),
                    sx(x2), sy(y2),
                    sx(x2), sy(bottom),
                    fill=color,
                    outline="",
                    stipple="gray50",
                )

    def _four_hour_average(self, rows, metric):
        buckets = [[] for _ in FOUR_HOUR_LABELS]
        for row in rows:
            value, synced_at = self._row_value_time(row, metric)
            if value is None or not isinstance(synced_at, datetime):
                continue
            bucket_index = synced_at.hour // 4
            if 0 <= bucket_index < len(buckets):
                buckets[bucket_index].append(value)
        return [sum(bucket) / len(bucket) if bucket else None for bucket in buckets]

    def _dummy_water_readings(self, last_synced):
        current = last_synced if isinstance(last_synced, datetime) else datetime.now()
        base = datetime(current.year, current.month, current.day)
        bucket_averages = [
            (0, 24.0, 3.0),
            (4, 26.5, 5.5),
            (8, 29.5, 7.2),
            (12, 27.0, 8.8),
            (16, 22.0, 11.0),
            (20, 31.0, 13.0),
        ]
        rows = []
        for hour, temperature, ph in bucket_averages:
            rows.append({"temperature": temperature - 0.4, "ph": ph - 0.2, "last_synced": base.replace(hour=hour, minute=20)})
            rows.append({"temperature": temperature + 0.4, "ph": ph + 0.2, "last_synced": base.replace(hour=hour + 2, minute=40)})
        return rows

    def _average_temperature(self, rows):
        values = []
        for row in rows:
            temperature, _synced_at = self._row_temperature_time(row)
            if temperature is not None:
                values.append(temperature)
        return sum(values) / len(values) if values else None

    def _average_ph(self, rows):
        values = []
        for row in rows:
            ph, _synced_at = self._row_value_time(row, "ph")
            if ph is not None:
                values.append(ph)
        return sum(values) / len(values) if values else None

    def _row_temperature_time(self, row):
        return self._row_value_time(row, "temperature")

    def _row_value_time(self, row, metric):
        try:
            if isinstance(row, dict):
                value = row[metric]
            else:
                value = row[0] if metric == "temperature" else row[1]
            synced_at = row["last_synced"] if isinstance(row, dict) else row[5]
            return float(value), synced_at
        except (KeyError, IndexError, TypeError, ValueError):
            return None, None

    def _temperature_status(self, temperature):
        try:
            value = float(temperature)
        except (TypeError, ValueError):
            return {"label": "Bahaya", "color": "#E74C3C"}
        if TEMP_NORMAL_MIN <= value <= TEMP_NORMAL_MAX:
            return {"label": "Optimal", "color": "#2ECC71"}
        return {"label": "Bahaya", "color": "#E74C3C"}

    def _ph_status(self, ph):
        try:
            value = float(ph)
        except (TypeError, ValueError):
            return {"label": "Bahaya", "color": "#E74C3C"}
        if 1 <= value < 4:
            return {"label": "Sangat Asam", "color": self._ph_color(value)}
        if 4 <= value < 6:
            return {"label": "Asam", "color": self._ph_color(value)}
        if 6 <= value < 7:
            return {"label": "Hampir Netral", "color": self._ph_color(value)}
        if 7 <= value <= 8:
            return {"label": "Netral", "color": self._ph_color(value)}
        if 8 < value <= 9:
            return {"label": "Basa Ringan", "color": self._ph_color(value)}
        if 9 < value < 13:
            return {"label": "Basa Sedang", "color": self._ph_color(value)}
        if 13 <= value <= 14:
            return {"label": "Sangat Basa", "color": self._ph_color(value)}
        return {"label": "Bahaya", "color": "#E74C3C"}

    def _dot_color(self, value):
        if self.mode == "suhu":
            return self._temperature_color(value)
        return self._ph_color(value)

    def _temperature_color(self, temperature):
        return self._temperature_status(temperature)["color"]

    def _ph_color(self, ph):
        try:
            value = float(ph)
        except (TypeError, ValueError):
            return "#E74C3C"
        if value < 1:
            return "#E74C3C"
        if value < 2:
            return "#D71920"
        if value < 3:
            return "#F05A24"
        if value < 4:
            return "#F7941D"
        if value < 5:
            return "#FFD21F"
        if value < 6:
            return "#FFF200"
        if value < 7:
            return "#D7DF23"
        if value <= 8:
            return "#37B34A"
        if value <= 9:
            return "#55C7DF"
        if value <= 10:
            return "#2F80C8"
        if value <= 11:
            return "#2464AD"
        if value <= 12:
            return "#6F63BF"
        if value < 13:
            return "#6B3FA0"
        if value <= 14:
            return "#3F1D78"
        return "#E74C3C"

    def _mix_color(self, start_color, end_color, ratio):
        ratio = max(0, min(1, ratio))

        def channels(color):
            color = color.lstrip("#")
            return [int(color[index:index + 2], 16) for index in (0, 2, 4)]

        start_channels = channels(start_color)
        end_channels = channels(end_color)
        mixed = [
            round(start + (end - start) * ratio)
            for start, end in zip(start_channels, end_channels)
        ]
        return f"#{mixed[0]:02X}{mixed[1]:02X}{mixed[2]:02X}"

    def _bucket_range_label(self, index):
        start_hour = index * 4
        if index == len(FOUR_HOUR_LABELS) - 1:
            return f"{start_hour:02d}.00-00.59"
        end_hour = start_hour + 3
        return f"{start_hour:02d}.00-{end_hour:02d}.59"

    def _format_number(self, value):
        if value is None:
            return "-"
        text = f"{float(value):.1f}"
        return text.rstrip("0").rstrip(".")

    def _format_today(self, last_synced):
        current = last_synced if isinstance(last_synced, datetime) else datetime.now()
        days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        months = [
            "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember",
        ]
        return f"{days[current.weekday()]}, {current.day} {months[current.month - 1]} {current.year}"

    def _sidebar_hitbox(self, canvas, sx, sy, y1, y2, tag):
        # Area klik sidebar dibuat lebih besar dari icon agar mudah disentuh di LCD.
        canvas.create_rectangle(sx(0), sy(y1), sx(78), sy(y2), fill="", outline="", tags=tag)
