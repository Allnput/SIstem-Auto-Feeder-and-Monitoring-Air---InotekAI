import calendar
import csv
from datetime import date, datetime, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import messagebox


PRIMARY = "#9157f5"
FIGMA_WIDTH = 960
FIGMA_HEIGHT = 640
CONTENT_HEIGHT = 1040
TEMP_MIN = 10
TEMP_MAX = 35
TEMP_TICKS = [10, 15, 20, 25, 30, 35]
TEMP_NORMAL_MIN = 23
TEMP_NORMAL_MAX = 28
PH_MIN = 0
PH_MAX = 15
PH_TICKS = [0, 3, 6, 9, 12, 15]
SHORT_MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
MONTH_NAMES = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]
SYSTEM_START_DATE = date(2026, 5, 1)


class RiwayatWaterMonitoringPage:
    def __init__(self, app, mode="suhu"):
        self.app = app
        self.mode = mode if mode in ("suhu", "ph") else "suhu"
        self.period = "Mingguan"
        today = datetime.now().date()
        self.selected_date = today
        self.selected_week_start = today - timedelta(days=today.weekday())
        self.selected_month = today.month
        self.selected_year = today.year
        self.show_period_popup = False
        self.canvas = None
        self._last_canvas_size = None
        self.selected_point = None

    def render(self):
        self.app.clear()
        self.app.lock_window_size()

        self.canvas = tk.Canvas(self.app.window, bg="#f8f5fc", highlightthickness=0, bd=0)
        self.canvas.pack(side="left", expand=True, fill="both")
        self._bind_actions()
        self.canvas.update_idletasks()
        self.draw()
        self.canvas.bind("<Configure>", self._redraw_when_resized)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

    def _bind_actions(self):
        self.canvas.tag_bind("home-nav", "<Button-1>", lambda _event: self.app.show_dashboard(self.app.current_user_name))
        self.canvas.tag_bind("water-nav", "<Button-1>", lambda _event: self.app.show_water_monitoring_page(self.mode))
        self.canvas.tag_bind("feed-nav", "<Button-1>", lambda _event: self.app.show_schedule_page())
        self.canvas.tag_bind("tab-suhu", "<Button-1>", lambda _event: self._switch_mode("suhu"))
        self.canvas.tag_bind("tab-ph", "<Button-1>", lambda _event: self._switch_mode("ph"))
        self.canvas.tag_bind("download", "<Button-1>", lambda _event: self._download_csv())
        self.canvas.tag_bind("period", "<Button-1>", lambda _event: self._toggle_period_popup())
        self.canvas.tag_bind("popup-close", "<Button-1>", lambda _event: self._close_period_popup())
        self.canvas.tag_bind("period-prev", "<Button-1>", lambda _event: self._move_period_range(-1))
        self.canvas.tag_bind("period-next", "<Button-1>", lambda _event: self._move_period_range(1))
        for period in ("Pilih tanggal", "Mingguan", "Bulan", "Tahunan"):
            self.canvas.tag_bind(f"period-{period}", "<Button-1>", lambda _event, value=period: self._select_period(value))

    def _redraw_when_resized(self, event):
        size = (event.width, event.height)
        if size == self._last_canvas_size:
            return
        self._last_canvas_size = size
        self.draw()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.draw()
        return "break"

    def _switch_mode(self, mode):
        self.mode = mode
        self.selected_point = None
        self.draw()

    def _select_period(self, period):
        self.period = period
        self.show_period_popup = True
        self.selected_point = None
        self.draw()

    def _toggle_period_popup(self):
        self.show_period_popup = not self.show_period_popup
        self.draw()

    def _close_period_popup(self):
        self.show_period_popup = False
        self.draw()

    def _move_period_range(self, direction):
        if self.period == "Pilih tanggal":
            self.selected_date = self._clamp_date(self.selected_date + timedelta(days=direction))
        elif self.period == "Mingguan":
            self.selected_week_start = self._clamp_week_start(self.selected_week_start + timedelta(days=7 * direction))
        elif self.period == "Bulan":
            year = self.selected_year
            month = self.selected_month + direction
            if month < 1:
                month = 12
                year -= 1
            elif month > 12:
                month = 1
                year += 1
            if self._month_is_available(year, month):
                self.selected_year = year
                self.selected_month = month
        elif self.period == "Tahunan":
            next_year = self.selected_year + direction
            if SYSTEM_START_DATE.year <= next_year <= datetime.now().year:
                self.selected_year = next_year
        self.selected_point = None
        self.draw()

    def draw(self):
        canvas = self.canvas
        self._last_canvas_size = (canvas.winfo_width(), canvas.winfo_height())
        canvas.delete("all")

        width = max(canvas.winfo_width(), self.app.width)
        height = max(canvas.winfo_height(), self.app.height)
        scale = min(width / self.app.width, height / self.app.height)
        ox = (width - self.app.width * scale) / 2
        x_ratio = self.app.width / FIGMA_WIDTH
        y_ratio = self.app.height / FIGMA_HEIGHT

        def sx(value):
            return ox + value * x_ratio * scale

        def sy(value):
            return value * y_ratio * scale

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

        canvas.configure(scrollregion=(0, 0, width, sy(CONTENT_HEIGHT)))
        canvas.create_rectangle(0, 0, width, sy(CONTENT_HEIGHT), fill="#f8f5fc", outline="#f8f5fc")

        rows = self._history_rows()
        chart = self._build_chart(rows)
        summary = self._summary(chart)

        self._draw_sidebar(canvas, sx, sy, scale, y_ratio * scale, rect, text)
        rect(90, 20, 845, 600, 45, "#ffffff", shadow=True)
        rect(90, 650, 845, 340, 45, "#ffffff", shadow=True)

        self.app._draw_icon_image(canvas, sx, sy, scale, "water ungu.png", 116, 38, 58, 58, fallback=lambda: self.app._draw_water_icon(canvas, sx, sy, scale, 120, 40, label=True, color=PRIMARY))
        text(190, 42, "Riwayat Kondisi Air", 27, "bold")
        self._draw_tabs(rect, text)
        # line(150, 120, 875, 120, PRIMARY, 1)

        # def _draw_arrow_image(self, canvas, sx, sy, filename, x, y, width, height, direction, tag):
        #     image = self._load_arrow_image(filename, width, height, direction)

        rect(740, 51, 120, 38, 28, PRIMARY, tags="download")
        text(773, 59, "Unduh", 14, "bold", "#ffffff", tags="download")
        line(150, 130, 850, 130, PRIMARY, 1)

        text(195, 95, "Periode", 16, "bold", "#333333")
        rect(280, 94, 115, 27, 16, "#e6e1ff", tags="period")
        text(290, 95, self.period, 12, "bold", "#42404a", tags="period")
        # self._draw_arrow_image(canvas, sx, sy, "arrow.png", 375, 101, 8, 8, "up" if self.show_period_popup else "down", "period")
        # text(390, 140, self._period_range_text(), 18, "bold", "#333333")
        


        # text(152, 125, "Periode", 15, "bold", "#a5a0a8")
        # self._draw_period_button(rect, text)
        text(154, 154, self._period_range_text(), 16, "bold", "#111111")
        # rect(782, 128, 118, 35, 8, PRIMARY, tags="download")
        # text(824, 136, "Unduh", 13, "bold", "#ffffff", tags="download")
        text(805, 133, "↓", 15, "bold", "#ffffff", tags="download")

        self._summary_card(rect, text, 110, 190, "Rata-rata " + ("suhu" if self.mode == "suhu" else "pH"), self._format_number(summary["average"]), "#eeedfe", PRIMARY)
        self._summary_card(rect, text, 315, 190, "Terendah", self._format_number(summary["min"]), "#eeedfe", PRIMARY, summary["min_label"])
        self._summary_card(rect, text, 520, 190, "Tertinggi", self._format_number(summary["max"]), "#eeedfe", PRIMARY, summary["max_label"])
        self._summary_card(rect, text, 725, 190, "Status", summary["status"]["label"], "#e6f1fb", summary["status"]["color"])

        title = "Grafik Suhu" if self.mode == "suhu" else "Grafik pH air"
        text(165, 305, title, 18, "bold")
        canvas.create_rectangle(sx(565), sy(325), sx(576), sy(336), fill=PRIMARY, outline=PRIMARY)
        text(582, 318, "Status air", 11)
        line(662, 331, 690, 331, "#000000", 1, dash=(4, 2))
        text(696, 318, "Batas normal", 11)
        self._draw_chart(canvas, sx, sy, fs, line, text, chart)
        self._draw_table(canvas, sx, sy, fs, rect, text, line, rows)
        if self.show_period_popup:
            self._draw_period_popup(canvas, sx, sy, fs, rect, text, line, y_ratio * scale)

    def _draw_tabs(self, rect, text):

        self._tab(rect, text, "Suhu", 270, 53, self.mode == "suhu", "tab-suhu")
        self._tab(rect, text, "pH air", 360, 53, self.mode == "ph", "tab-ph")
        
        # self._tab(rect, text, "Suhu", 616, self.mode == "suhu", "tab-suhu")
        # self._tab(rect, text, "pH air", 710, self.mode == "ph", "tab-ph")

    def _tab(self, rect, text, label, x, y, active, tag):
        fill = "#eeedfe" if active else "#d9d9d9"
        fg = "#000000" if active else "#555555"
        rect(x + 225, y - 2, 85, 26, 14, fill, "#c8c8c8", 1, tags=tag)
        text(x + 250, y, label, 11, "bold", fg, tags=tag)

    def _draw_period_button(self, rect, text):
        width = 118 if self.period == "Pilih tanggal" else 96
        rect(230, 124, width, 27, 8, "#e6e1ff", "#d6d0e6", 1, tags="period")
        text(240, 128, self.period, 9, "bold", "#42395a", tags="period")
        text(230 + width - 18, 126, "v", 11, "bold", PRIMARY, tags="period")

    def _draw_period_popup(self, canvas, sx, sy, fs, rect, text, line, y_unit):
        top = self.canvas.canvasy(0)
        canvas.create_rectangle(0, top, self.canvas.winfo_width(), top + self.canvas.winfo_height(),
                                fill="#000000", stipple="gray25", outline="", tags="popup")

        popup_width = 430
        popup_height = 330
        y_offset = top / y_unit
        visible_height = self.canvas.winfo_height() / y_unit
        x0 = (FIGMA_WIDTH - popup_width) / 2
        y0 = y_offset + max(20, (visible_height - popup_height) / 2)

        rect(x0, y0, popup_width, popup_height, 20, "#ffffff", shadow=True, tags="popup")
        text(x0 + 22, y0 + 20, "Interval Waktu", 20, "bold", tags="popup")
        text(x0 + 365, y0 + 282, "Batal", 12, "bold", "#6f6876", tags=("popup", "popup-close"))
        line(x0 + 215, y0 + 75, x0 + 215, y0 + 220, "#d5b6ff", 1)
        line(x0 + 40, y0 + 150, x0 + 390, y0 + 150, "#d5b6ff", 1)

        self._period_choice(rect, text, x0 + 60, y0 + 92, "Pilih tanggal")
        self._period_choice(rect, text, x0 + 262, y0 + 92, "Tahunan")
        self._period_choice(rect, text, x0 + 70, y0 + 178, "Mingguan")
        self._period_choice(rect, text, x0 + 272, y0 + 178, "Bulan")

        text(x0 + 64, y0 + 238, "<", 22, "bold", PRIMARY, tags=("popup", "period-prev"))
        text(x0 + 365, y0 + 238, ">", 22, "bold", PRIMARY, tags=("popup", "period-next"))
        text(x0 + 118, y0 + 244, self._period_range_text(), 11, "bold", "#333333", tags="popup")

    def _period_choice(self, rect, text, x, y, label):
        active = self.period == label
        rect(x - 14, y - 8, 132, 44, 14, PRIMARY if active else "#f4efff", "#e2d8ff", 1, tags=("popup", f"period-{label}"))
        text(x, y + 5, label, 11, "bold", "#ffffff" if active else "#6f6876", tags=("popup", f"period-{label}"))

    def _draw_sidebar(self, canvas, sx, sy, scale, y_unit, rect, text):
        y_offset = self.canvas.canvasy(0) / y_unit
        rect(0, y_offset, 78, 640, 0, "#ffffff", shadow=True)
        rect(8, y_offset + 20, 61, 52, 0, "#faf7ff")
        self.app._draw_icon_image(canvas, sx, sy, scale, "logo inotekai.jpeg", 8, y_offset + 20, 61, 52, fallback=lambda: text(12, y_offset + 35, "InotekAI", 10, "bold", PRIMARY))
        self.app._draw_icon_image(canvas, sx, sy, scale, "home hitam.png", 22, y_offset + 235, 38, 38, fallback=lambda: self.app._draw_home_icon(canvas, sx, sy, scale, 24, y_offset + 243))
        self.app._draw_icon_image(canvas, sx, sy, scale, "water ungu.png", 22, y_offset + 300, 42, 42, fallback=lambda: self.app._draw_water_icon(canvas, sx, sy, scale, 21, y_offset + 302, label=True, color=PRIMARY))
        self.app._draw_icon_image(canvas, sx, sy, scale, "fish hitam.png", 15, y_offset + 360, 50, 50, fallback=lambda: self.app._draw_fish_icon(canvas, sx, sy, scale, 17, y_offset + 367))
        canvas.create_rectangle(sx(0), sy(y_offset + 206), sx(78), sy(y_offset + 284), fill="", outline="", tags="home-nav")
        canvas.create_rectangle(sx(0), sy(y_offset + 284), sx(78), sy(y_offset + 352), fill="", outline="", tags="water-nav")
        canvas.create_rectangle(sx(0), sy(y_offset + 352), sx(78), sy(y_offset + 430), fill="", outline="", tags="feed-nav")

    def _summary_card(self, rect, text, x, y, title, value, bg, value_color, subtitle=""):
        rect(x, y, 185, 92, 20, bg, shadow=True)
        text(x + 15, y + 13, title, 15)
        text(x + 15, y + 40, value, 27, "bold", value_color)
        if subtitle:
            text(x + 15, y + 70, subtitle, 10, fill="#666666")

    def _draw_chart(self, canvas, sx, sy, fs, line, text, chart):
        left, top, right, bottom = 140, 355, 910, 555
        chart_min = TEMP_MIN if self.mode == "suhu" else PH_MIN
        chart_max = TEMP_MAX if self.mode == "suhu" else PH_MAX
        ticks = TEMP_TICKS if self.mode == "suhu" else PH_TICKS

        def y_for(value):
            bounded = max(chart_min, min(chart_max, float(value)))
            return bottom - ((bounded - chart_min) / (chart_max - chart_min)) * (bottom - top)

        def x_for(index):
            denominator = max(1, len(chart) - 1)
            return left + (index / denominator) * (right - left)

        for tick in ticks:
            y = y_for(tick)
            line(left, y, right, y, "#dddddd", 1, dash=(2, 2))
            text(left - 30, y - 7, str(tick), 9, fill="#a0a0a0")
        line(left, bottom, right, bottom, "#aaaaaa", 1)
        line(left, top, left, bottom, "#aaaaaa", 1)
        if self.mode == "suhu":
            for boundary in (TEMP_NORMAL_MIN, TEMP_NORMAL_MAX):
                line(left, y_for(boundary), right, y_for(boundary), "#000000", 1, dash=(4, 2))
        else:
            for boundary in (6, 8):
                line(left, y_for(boundary), right, y_for(boundary), "#000000", 1, dash=(4, 2))

        point_items = []
        points = []
        for index, item in enumerate(chart):
            if item["value"] is None:
                continue
            x = x_for(index)
            y = y_for(item["value"])
            point_items.append((index, item["value"], x, y))
            points.extend([sx(x), sy(y)])
        if point_items:
            color_for = self._temperature_color if self.mode == "suhu" else self._ph_color
            self._draw_gradient_fill(canvas, sx, sy, point_items, bottom, color_for)
        if len(points) >= 4:
            canvas.create_line(points, fill="#19a8ff" if self.mode == "suhu" else PRIMARY, width=max(2, int(2 * self.app.height / FIGMA_HEIGHT)), smooth=True)
        for index, value, x, y in point_items:
            color = self._temperature_color(value) if self.mode == "suhu" else self._ph_color(value)
            tag = f"chart-point-{index}"
            canvas.create_oval(sx(x) - 4, sy(y) - 4, sx(x) + 4, sy(y) + 4, fill=color, outline="#ffffff", tags=tag)
            canvas.tag_bind(tag, "<Button-1>", lambda _event, selected=index: self._select_point(selected))
        for index, item in enumerate(chart):
            text(x_for(index), bottom + 15, item["label"], 8, fill="#a0a0a0", anchor="n")
        if self.selected_point is not None and 0 <= self.selected_point < len(chart):
            self._draw_tooltip(canvas, sx, sy, text, chart, x_for, y_for)

    def _draw_tooltip(self, canvas, sx, sy, text, chart, x_for, y_for):
        item = chart[self.selected_point]
        if item["value"] is None:
            return
        x = min(770, max(150, x_for(self.selected_point) - 55))
        y = max(365, y_for(item["value"]) - 55)
        self.app._dashboard_round_rect(canvas, sx(x), sy(y), sx(x + 135), sy(y + 44), 4, "#000000", "#000000", 0, "chart-tooltip")
        color = self._temperature_color(item["value"]) if self.mode == "suhu" else self._ph_color(item["value"])
        canvas.create_rectangle(sx(x + 12), sy(y + 16), sx(x + 24), sy(y + 28), fill=color, outline=color, tags="chart-tooltip")
        label = "Suhu" if self.mode == "suhu" else "pH air"
        text(x + 30, y + 7, item["tooltip"], 8, fill="#ffffff", tags="chart-tooltip")
        text(x + 30, y + 23, f"{label}: {self._format_number(item['value'])}", 10, "bold", "#ffffff", tags="chart-tooltip")

    def _select_point(self, index):
        self.selected_point = index
        self.draw()

    def _draw_table(self, canvas, sx, sy, fs, rect, text, line, rows):
        table_title = "Riwayat Data Suhu Air" if self.mode == "suhu" else "Riwayat Data pH Air"
        text(115, 675, table_title, 20, "bold")
        rect(745, 672, 120, 36, 18, PRIMARY, tags="download")
        text(770, 680, "Show CSV", 13, "bold", "#ffffff", tags="download")
        metric_header = "Suhu" if self.mode == "suhu" else "pH Air"
        headers = ["No", "Tanggal", "Waktu", metric_header, "Status"]
        xs = [118, 185, 345, 510, 685]
        for x, header in zip(xs, headers):
            text(x, 735, header, 15, "bold", "#7169e8")
        visible = rows[:5]
        if not visible:
            text(125, 795, "Belum ada riwayat kondisi air.", 17, "bold", "#8b8b8b")
            return
        for index, row in enumerate(visible):
            y = 780 + index * 48
            status = self._row_status(row)
            values = [
                str(index + 1),
                row["synced_at"].strftime("%d/%m/%y"),
                row["synced_at"].strftime("%H:%M"),
                self._format_number(row["temperature"] if self.mode == "suhu" else row["ph"]),
                status["label"],
            ]
            for x, value in zip(xs, values):
                fill = status["color"] if x == 685 else "#111111"
                text(x, y, value, 14, "bold", fill)
            line(112, y + 32, 860, y + 32, "#a68cff", 1)

    def _history_rows(self):
        try:
            raw_rows = self.app.db.get_water_history(1000)
        except Exception as exc:
            self.app._warn_database_once(exc)
            raw_rows = []
        rows = [self._normalize_row(row) for row in raw_rows]
        rows = [row for row in rows if row and self._inside_period(row["synced_at"])]
        rows.sort(key=lambda item: item["synced_at"])
        return rows or self._dummy_rows()

    def _normalize_row(self, row):
        try:
            if isinstance(row, dict):
                synced_at = row.get("last_synced")
                status_label = row.get("status_label")
                status_color = row.get("status_color")
                temperature = row.get("temperature")
                ph = row.get("ph")
            else:
                temperature, ph, _water_level, status_label, _feed_percentage, synced_at = row
                status_color = None
            if not isinstance(synced_at, datetime):
                synced_at = datetime.now()
            return {
                "temperature": float(temperature),
                "ph": float(ph),
                "synced_at": synced_at,
                "status_label": status_label,
                "status_color": status_color,
            }
        except (TypeError, ValueError):
            return None

    def _inside_period(self, synced_at):
        if self.period == "Pilih tanggal":
            return synced_at.date() == self.selected_date
        if self.period == "Bulan":
            return synced_at.year == self.selected_year and synced_at.month == self.selected_month
        if self.period == "Tahunan":
            return synced_at.year == self.selected_year
        start = self.selected_week_start
        end = start + timedelta(days=6)
        return start <= synced_at.date() <= end

    def _build_chart(self, rows):
        buckets = self._chart_buckets()
        metric = "temperature" if self.mode == "suhu" else "ph"
        for row in rows:
            bucket = self._bucket_for(row["synced_at"], buckets)
            if bucket is not None:
                bucket["values"].append(row[metric])
        for bucket in buckets:
            values = bucket["values"]
            bucket["value"] = sum(values) / len(values) if values else None
        return buckets

    def _chart_buckets(self):
        if self.period == "Pilih tanggal":
            base = datetime.combine(self.selected_date, datetime.min.time())
            return [{"label": f"{hour:02d}.00", "tooltip": f"{hour:02d}.00-{min(hour + 3, 23):02d}.59", "start": base.replace(hour=hour), "values": []} for hour in range(0, 24, 4)]
        if self.period == "Bulan":
            _, last_day = calendar.monthrange(self.selected_year, self.selected_month)
            return [{"label": f"M-{index + 1}", "tooltip": f"Minggu ke-{index + 1}", "week_index": index, "values": []} for index in range((last_day + 6) // 7)]
        if self.period == "Tahunan":
            return [{"label": SHORT_MONTH_NAMES[index], "tooltip": f"{MONTH_NAMES[index]} {self.selected_year}", "month": index + 1, "values": []} for index in range(12)]
        start = self.selected_week_start
        return [{"label": (start + timedelta(days=offset)).strftime("%d %b"), "tooltip": (start + timedelta(days=offset)).strftime("%d/%m/%Y"), "date": start + timedelta(days=offset), "values": []} for offset in range(7)]

    def _bucket_for(self, synced_at, buckets):
        if self.period == "Pilih tanggal":
            return buckets[synced_at.hour // 4]
        if self.period == "Bulan":
            return buckets[min((synced_at.day - 1) // 7, len(buckets) - 1)]
        if self.period == "Tahunan":
            return buckets[synced_at.month - 1]
        for bucket in buckets:
            if bucket["date"] == synced_at.date():
                return bucket
        return None

    def _summary(self, chart):
        available = [item for item in chart if item["value"] is not None]
        if not available:
            return {"average": None, "min": None, "max": None, "min_label": "", "max_label": "", "status": {"label": "-", "color": "#95A5A6"}}
        values = [item["value"] for item in available]
        average = sum(values) / len(values)
        low = min(available, key=lambda item: item["value"])
        high = max(available, key=lambda item: item["value"])
        status = self._temperature_status(average) if self.mode == "suhu" else self._ph_status(average)
        return {"average": average, "min": low["value"], "max": high["value"], "min_label": low["label"], "max_label": high["label"], "status": status}

    def _current_status(self):
        rows = self._history_rows()
        if rows:
            latest = rows[-1]
            return self._temperature_status(latest["temperature"]) if self.mode == "suhu" else self._ph_status(latest["ph"])
        return {"label": "Tidak Aktif", "color": "#95A5A6"}

    def _row_status(self, row):
        if self.mode == "suhu":
            return self._temperature_status(row["temperature"])
        return self._ph_status(row["ph"])

    def _temperature_status(self, temperature):
        try:
            value = float(temperature)
        except (TypeError, ValueError):
            return {"label": "Bahaya", "color": "#E74C3C"}
        if TEMP_NORMAL_MIN <= value <= TEMP_NORMAL_MAX:
            return {"label": "Normal", "color": "#2ECC71"}
        return {"label": "Bahaya", "color": "#E74C3C"}

    def _temperature_color(self, temperature):
        return self._temperature_status(temperature)["color"]

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

    def _draw_gradient_fill(self, canvas, sx, sy, point_items, bottom, color_for_value):
        if len(point_items) == 1:
            _index, value, x, y = point_items[0]
            canvas.create_polygon(sx(x - 8), sy(bottom), sx(x), sy(y), sx(x + 8), sy(bottom), fill=color_for_value(value), outline="", stipple="gray50")
            return
        for item_index in range(len(point_items) - 1):
            _start_index, start_value, start_x, start_y = point_items[item_index]
            _end_index, end_value, end_x, end_y = point_items[item_index + 1]
            for step in range(18):
                ratio_a = step / 18
                ratio_b = (step + 1) / 18
                x1 = start_x + (end_x - start_x) * ratio_a
                y1 = start_y + (end_y - start_y) * ratio_a
                x2 = start_x + (end_x - start_x) * ratio_b
                y2 = start_y + (end_y - start_y) * ratio_b
                color = self._mix_color(color_for_value(start_value), color_for_value(end_value), (ratio_a + ratio_b) / 2)
                canvas.create_polygon(sx(x1), sy(bottom), sx(x1), sy(y1), sx(x2), sy(y2), sx(x2), sy(bottom), fill=color, outline="", stipple="gray50")

    def _mix_color(self, start_color, end_color, ratio):
        ratio = max(0, min(1, ratio))

        def channels(color):
            color = color.lstrip("#")
            return [int(color[index:index + 2], 16) for index in (0, 2, 4)]

        return "#%02X%02X%02X" % tuple(
            round(start + (end - start) * ratio)
            for start, end in zip(channels(start_color), channels(end_color))
        )

    def _download_csv(self):
        rows = self._history_rows()
        if not rows:
            messagebox.showinfo("Unduh", "Belum ada riwayat kondisi air.")
            return
        path = Path(__file__).resolve().parent / f"riwayat_kondisi_air_{self.mode}_{self.period.lower()}.csv"
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            metric_label = "suhu" if self.mode == "suhu" else "ph_air"
            writer.writerow(["tanggal", "waktu", metric_label, "status"])
            for row in rows:
                status = self._row_status(row)
                writer.writerow([
                    row["synced_at"].strftime("%d/%m/%Y"),
                    row["synced_at"].strftime("%H:%M"),
                    self._format_number(row["temperature"] if self.mode == "suhu" else row["ph"]),
                    status["label"],
                ])
        messagebox.showinfo("Unduh", f"CSV disimpan:\n{path}")

    def _dummy_rows(self):
        values = [(24.0, 3.0), (26.5, 5.5), (29.5, 7.2), (27.0, 8.8), (22.0, 11.0), (31.0, 13.0), (25.8, 7.6)]
        rows = []
        for index, (temp, ph) in enumerate(values):
            if self.period == "Pilih tanggal":
                synced_at = datetime.combine(self.selected_date, datetime.min.time()).replace(hour=(index % 6) * 4, minute=20)
            elif self.period == "Bulan":
                day = min(index * 4 + 1, calendar.monthrange(self.selected_year, self.selected_month)[1])
                synced_at = datetime(self.selected_year, self.selected_month, day, 8 + index % 4, 20)
            elif self.period == "Tahunan":
                month = min(index + 1, 12)
                synced_at = datetime(self.selected_year, month, 12, 8 + index % 4, 20)
            else:
                synced_at = datetime.combine(self.selected_week_start + timedelta(days=index), datetime.min.time()).replace(hour=8 + index % 4, minute=20)
            rows.append({"temperature": temp, "ph": ph, "synced_at": synced_at, "status_label": None, "status_color": None})
        return rows

    def _period_range_text(self):
        if self.period == "Pilih tanggal":
            return self._format_full_date(self.selected_date)
        if self.period == "Bulan":
            return f"{MONTH_NAMES[self.selected_month - 1]} {self.selected_year}"
        if self.period == "Tahunan":
            return str(self.selected_year)
        start = self.selected_week_start
        end = start + timedelta(days=6)
        return f"{self._format_full_date(start)} - {self._format_full_date(end)}"

    def _clamp_date(self, value):
        return max(SYSTEM_START_DATE, min(datetime.now().date(), value))

    def _clamp_week_start(self, value):
        today = datetime.now().date()
        current_week_start = today - timedelta(days=today.weekday())
        first_week_start = SYSTEM_START_DATE - timedelta(days=SYSTEM_START_DATE.weekday())
        return max(first_week_start, min(current_week_start, value))

    def _month_is_available(self, year, month):
        first_day = date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        last_date = date(year, month, last_day)
        today = datetime.now().date()
        return last_date >= SYSTEM_START_DATE and first_day <= today

    def _format_full_date(self, value):
        return f"{value.day} {MONTH_NAMES[value.month - 1]} {value.year}"

    def _format_number(self, value):
        if value is None:
            return "-"
        text = f"{float(value):.1f}"
        return text.rstrip("0").rstrip(".")
