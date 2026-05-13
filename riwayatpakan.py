import calendar
from datetime import date, datetime, timedelta
from pathlib import Path
import re
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox

try:
    from PIL import Image, ImageOps, ImageTk
except ImportError:
    Image = None
    ImageOps = None
    ImageTk = None


PRIMARY = "#9157f5"
BLUE = "#8FD3FF"
FIGMA_WIDTH = 960
FIGMA_HEIGHT = 640
CONTENT_HEIGHT = 1230
DEFAULT_FEED_OUT_PERCENT_PER_EVENT = 5.0
ICON_DIR = Path(__file__).resolve().parent / "icon"
SYSTEM_START_DATE = date(2026, 5, 1)
DAY_NAMES = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
SHORT_DAY_NAMES = ["S", "S", "R", "K", "J", "S", "M"]
MONTH_NAMES = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
SHORT_MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


class RiwayatPakanPage:
    def __init__(self, app):
        self.app = app
        self.canvas = None
        self._last_canvas_size = None
        self.period = "Pilih tanggal"
        self.pending_period = self.period
        self.selected_day = None
        today = self._today()
        self.selected_date = today
        self.selected_week_start = today - timedelta(days=today.weekday())
        self.selected_month = today.month
        self.selected_year = today.year
        self.calendar_month = today.month
        self.calendar_year = today.year
        self.temp_date = today
        self.temp_month = today.month
        self.temp_year = today.year
        self.show_period_popup = False
        self.show_picker_popup = False
        self.image_cache = {}
        self.table_scroll_index = 0
        self.table_area = None
        self.table_rows_count = 0
        self.table_scrollbar = None

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
        self.canvas.tag_bind("water-nav", "<Button-1>", lambda _event: self.app.show_water_monitoring_page("suhu"))
        self.canvas.tag_bind("feed-nav", "<Button-1>", lambda _event: self.app.show_schedule_page())
        self.canvas.tag_bind("period", "<Button-1>", lambda _event: self._toggle_period_popup())
        self.canvas.tag_bind("download", "<Button-1>", lambda _event: messagebox.showinfo("Unduh", "File telah diunduh."))
        self.canvas.tag_bind("popup-close", "<Button-1>", lambda _event: self._close_period_popup())
        self.canvas.tag_bind("picker-done", "<Button-1>", lambda _event: self._finish_picker())
        self.canvas.tag_bind("picker-prev-month", "<Button-1>", lambda _event: self._move_calendar_month(-1))
        self.canvas.tag_bind("picker-next-month", "<Button-1>", lambda _event: self._move_calendar_month(1))
        self.canvas.tag_bind("picker-prev-year", "<Button-1>", lambda _event: self._move_picker_year(-1))
        self.canvas.tag_bind("picker-next-year", "<Button-1>", lambda _event: self._move_picker_year(1))
        self.canvas.tag_bind("table-scrollbar", "<Button-1>", self._scroll_table_from_pointer)
        self.canvas.tag_bind("table-scrollbar", "<B1-Motion>", self._scroll_table_from_pointer)
        for label in ["Pilih tanggal", "Tahunan", "Mingguan", "Bulan"]:
            self.canvas.tag_bind(f"period-{label}", "<Button-1>", lambda _event, value=label: self._select_period(value))
        for index in range(42):
            self.canvas.tag_bind(f"picker-day-{index}", "<Button-1>", lambda _event, value=index: self._select_picker_day(value))
        for month in range(1, 13):
            self.canvas.tag_bind(f"picker-month-{month}", "<Button-1>", lambda _event, value=month: self._select_picker_month(value))
        for index in range(12):
            self.canvas.tag_bind(f"bar-{index}", "<Button-1>", lambda _event, value=index: self._select_day(value))

    def _redraw_when_resized(self, event):
        size = (event.width, event.height)
        if size == self._last_canvas_size:
            return
        self._last_canvas_size = size
        self.draw()

    def _on_mousewheel(self, event):
        if self._mouse_inside_table(event) and self.table_rows_count > 6:
            direction = 1 if event.delta < 0 else -1
            max_index = max(0, self.table_rows_count - 6)
            self.table_scroll_index = max(0, min(max_index, self.table_scroll_index + direction))
            self.draw()
            return "break"

        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.draw()
        return None

    def _mouse_inside_table(self, event):
        if not self.table_area:
            return False
        x1, y1, x2, y2 = self.table_area
        y = self.canvas.canvasy(event.y)
        return x1 <= event.x <= x2 and y1 <= y <= y2

    def _scroll_table_from_pointer(self, event):
        if not self.table_scrollbar or self.table_rows_count <= 6:
            return "break"

        track_top, track_bottom = self.table_scrollbar
        pointer_y = self.canvas.canvasy(event.y)
        max_index = max(0, self.table_rows_count - 6)
        usable_height = max(1, track_bottom - track_top)
        ratio = (pointer_y - track_top) / usable_height
        next_index = round(max(0, min(1, ratio)) * max_index)

        if next_index != self.table_scroll_index:
            self.table_scroll_index = next_index
            self.draw()
        return "break"

    def _toggle_period_popup(self):
        self.show_period_popup = not self.show_period_popup
        if self.show_period_popup:
            self.pending_period = self.period
        self.draw()

    def _close_period_popup(self):
        self.pending_period = self.period
        self.show_period_popup = False
        self.show_picker_popup = False
        self.draw()

    def _select_period(self, value):
        self.pending_period = value
        self.show_period_popup = False
        self.show_picker_popup = True
        self._prepare_picker_state()
        self.draw()

    def _select_day(self, index):
        self.selected_day = None if self.selected_day == index else index
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

        def line(x1, y1, x2, y2, fill=PRIMARY, width=1):
            canvas.create_line(sx(x1), sy(y1), sx(x2), sy(y2), fill=fill, width=max(1, int(width * scale)))

        canvas.configure(scrollregion=(0, 0, width, sy(CONTENT_HEIGHT)))
        canvas.create_rectangle(0, 0, width, sy(CONTENT_HEIGHT), fill="#f8f5fc", outline="#f8f5fc")

        rows = self._history_rows()
        chart = self._build_chart(rows)
        total_auto = sum(item["auto"] for item in chart)
        total_manual = sum(item["manual"] for item in chart)
        feed_out_percent = min(100.0, sum(row["feed_out_percent"] for row in rows))

        self._draw_sidebar(canvas, sx, sy, scale, y_ratio * scale, rect, text)
        rect(90, 20, 845, 610, 45, "#ffffff", shadow=True)
        rect(90, 650, 845, 550, 45, "#ffffff", shadow=True)

        self.app._draw_icon_image(canvas, sx, sy, scale, "fish ungu.png", 118, 42, 64, 64, fallback=lambda: self.app._draw_fish_icon(canvas, sx, sy, scale, 120, 45, PRIMARY))
        text(193, 48, "Riwayat Pakan", 24, "bold")

        rect(740, 51, 120, 38, 28, PRIMARY, tags="download")
        text(773, 59, "Unduh", 14, "bold", "#ffffff", tags="download")
        line(150, 130, 850, 130, PRIMARY, 1)

        text(195, 95, "Periode", 16, "bold", "#333333")
        rect(280, 94, 115, 27, 16, "#e6e1ff", tags="period")
        text(290, 95, self.period, 12, "bold", "#42404a", tags="period")
        self._draw_arrow_image(canvas, sx, sy, "arrow.png", 375, 101, 8, 8, "up" if self.show_period_popup else "down", "period")
        text(390, 140, self._period_range_text(), 18, "bold", "#333333")

        self._summary_card(rect, text, 110, 175, 190, "Pakan keluar", f"{feed_out_percent:.1f}%", "#eeedfe", "#333333")
        self._summary_card(rect, text, 310, 175, 190, "Auto feeder", str(total_auto), "#eeedfe", PRIMARY)
        self._summary_card(rect, text, 510, 175, 190, "Manual feed", str(total_manual), "#eeedfe", PRIMARY)
        self._summary_card(rect, text, 710, 175, 190, "Total feeder", str(total_auto + total_manual), "#e6f1fb", "#333333")

        text(200, 310, "Grafik Penggunaan", 18, "bold")
        self._draw_chart(canvas, sx, sy, fs, line, text, chart)
        self._draw_table(canvas, sx, sy, fs, rect, text, line, rows)

        if self.show_period_popup:
            self._draw_period_popup(canvas, sx, sy, fs, rect, text, line, y_ratio * scale)
        if self.show_picker_popup:
            self._draw_picker_popup(canvas, sx, sy, fs, rect, text, line, y_ratio * scale)

    def _draw_sidebar(self, canvas, sx, sy, scale, y_unit, rect, text):
        y_offset = self.canvas.canvasy(0) / y_unit
        rect(0, y_offset, 78, 640, 0, "#ffffff", shadow=True)
        rect(8, y_offset + 20, 61, 52, 0, "#faf7ff")
        self.app._draw_icon_image(canvas, sx, sy, scale, "logo inotekai.jpeg", 8, y_offset + 20, 61, 52, fallback=lambda: text(12, y_offset + 35, "InotekAI", 10, "bold", PRIMARY))
        self.app._draw_icon_image(canvas, sx, sy, scale, "home hitam.png", 22, y_offset + 235, 38, 38, fallback=lambda: self.app._draw_home_icon(canvas, sx, sy, scale, 24, y_offset + 243))
        self.app._draw_icon_image(canvas, sx, sy, scale, "water hitam.png", 22, y_offset + 300, 42, 42, fallback=lambda: self.app._draw_water_icon(canvas, sx, sy, scale, 21, y_offset + 302, label=True))
        self.app._draw_icon_image(canvas, sx, sy, scale, "fish ungu.png", 15, y_offset + 360, 50, 50, fallback=lambda: self.app._draw_fish_icon(canvas, sx, sy, scale, 17, y_offset + 367, color=PRIMARY))
        canvas.create_rectangle(sx(0), sy(y_offset + 206), sx(78), sy(y_offset + 284), fill="", outline="", tags="home-nav")
        canvas.create_rectangle(sx(0), sy(y_offset + 284), sx(78), sy(y_offset + 352), fill="", outline="", tags="water-nav")
        canvas.create_rectangle(sx(0), sy(y_offset + 352), sx(78), sy(y_offset + 430), fill="", outline="", tags="feed-nav")

    def _summary_card(self, rect, text, x, y, width, title, value, bg, fg):
        rect(x, y, width, 92, 18, bg, shadow=True)
        text(x + 22, y + 17, title, 16, fill="#333333")
        text(x + 22, y + 45, value, 28, "bold", fg)

    def _draw_chart(self, canvas, sx, sy, fs, line, text, chart):
        left, top, bottom = 210, 360, 585
        if self.period in ("Bulan", "Tahunan"):
            max_value = 100
            axis_values = range(0, 101, 20)
        else:
            max_value = max(10, max([item["auto"] for item in chart] + [item["manual"] for item in chart] + [1]))
            axis_values = range(0, max_value + 1, max(1, max_value // 5))

        for value in axis_values:
            y = bottom - (value / max_value) * (bottom - top)
            line(left, y, 835, y, "#eeeeee", 1)
            text(left - 32, y - 7, str(value), 9, fill="#9aa9bc")

        canvas.create_rectangle(sx(725), sy(303), sx(735), sy(313), fill=PRIMARY, outline=PRIMARY)
        text(740, 295, "Auto feeder", 10)
        canvas.create_rectangle(sx(725), sy(323), sx(735), sy(333), fill=BLUE, outline=BLUE)
        text(740, 315, "Manual feed", 10)

        spacing = 85 if len(chart) <= 7 else 50
        bar_width = 20 if len(chart) <= 7 else 14
        label_size = 9 if len(chart) <= 7 else 8
        for index, item in enumerate(chart):
            x = left + 15 + index * spacing
            auto_height = (item["auto"] / max_value) * (bottom - top)
            manual_height = (item["manual"] / max_value) * (bottom - top)
            canvas.create_rectangle(sx(x), sy(bottom - auto_height), sx(x + bar_width), sy(bottom), fill=PRIMARY, outline=PRIMARY, tags=f"bar-{index}")
            canvas.create_rectangle(sx(x + bar_width + 5), sy(bottom - manual_height), sx(x + bar_width * 2 + 5), sy(bottom), fill=BLUE, outline=BLUE, tags=f"bar-{index}")
            text(x, bottom + 5, item["label"], label_size, fill="#95a1b8")

        if self.selected_day is not None and self.selected_day < len(chart):
            selected = chart[self.selected_day]
            tooltip_font = tkfont.Font(family="Segoe UI", size=fs(9), weight="bold")
            detail_font = tkfont.Font(family="Segoe UI", size=fs(10), weight="normal")
            x_unit = max(0.001, sx(1) - sx(0))
            tooltip_text_width = max(
                tooltip_font.measure(selected["tooltip"]) / x_unit,
                28 + detail_font.measure(f"Auto: {selected['auto']}") / x_unit,
                28 + detail_font.measure(f"Manual: {selected['manual']}") / x_unit,
                detail_font.measure(f"Jarak lontar: {selected['distance']}m") / x_unit,
            )
            tooltip_width = max(200, min(835 - left, tooltip_text_width + 34))
            tooltip_x = min(835 - tooltip_width, left + 30 + self.selected_day * spacing + 20)
            tooltip_y = 475
            self.app._dashboard_round_rect(canvas, sx(tooltip_x), sy(tooltip_y), sx(tooltip_x + tooltip_width), sy(tooltip_y + 82), 4, "#ffffff", "#000000", 1, None)
            text(tooltip_x + 10, tooltip_y + 7, selected["tooltip"], 9, "bold", "#111111")
            canvas.create_rectangle(sx(tooltip_x + 10), sy(tooltip_y + 28), sx(tooltip_x + 20), sy(tooltip_y + 38), fill=PRIMARY, outline=PRIMARY)
            text(tooltip_x + 28, tooltip_y + 22, f"Auto: {str(selected['auto'])}", 10, fill="#111111")
            canvas.create_rectangle(sx(tooltip_x + 10), sy(tooltip_y + 43), sx(tooltip_x + 20), sy(tooltip_y + 53), fill=BLUE, outline=BLUE)
            text(tooltip_x + 28, tooltip_y + 38, f"Manual: {str(selected['manual'])}", 10, fill="#111111")
            text(tooltip_x + 10, tooltip_y + 58, f"Jarak lontar: {selected['distance']}m", 10, fill="#111111")

    def _draw_table(self, canvas, sx, sy, fs, rect, text, line, rows):
        y = 655
        self.table_rows_count = len(rows)
        self.table_scroll_index = min(self.table_scroll_index, max(0, len(rows) - 6))
        self.table_area = (sx(105), sy(760), sx(865), sy(1180))
        self.table_scrollbar = None

        text(105, 663, "Riwayat Data Auto Feeder", 20, "bold")
        rect(740, 660, 120, 38, 28, PRIMARY, tags="download")
        text(765, 668, "Show CSV", 14, "bold", "#ffffff", tags="download")
        text(112, y + 58, "No", 18, "bold", "#7169e8")
        text(167, y + 58, "Tanggal", 18, "bold", "#7169e8")
        text(313, y + 58, "Jam", 18, "bold", "#7169e8")
        text(455, y + 58, "Jarak Lontar", 18, "bold", "#7169e8")
        text(715, y + 58, "Teknik pakan", 18, "bold", "#7169e8")

        if not rows:
            text(125, y + 125, "Belum ada riwayat pakan.", 18, "bold", "#8b8b8b")
            return

        visible_rows = rows[self.table_scroll_index:self.table_scroll_index + 7]
        for visible_index, row in enumerate(visible_rows):
            actual_index = self.table_scroll_index + visible_index
            row_y = y + 105 + visible_index * 64
            text(122, row_y, str(actual_index + 1), 18, "bold")
            text(168, row_y, row["date"], 18, "bold")
            text(315, row_y, row["time"], 18, "bold")
            text(515, row_y, str(row["distance"]), 18, "bold")
            label = "Auto feeder" if row["type"] == "auto" else "Manual feed"
            bg = "#aee7ce" if row["type"] == "auto" else "#98d5ff"
            fg = "#0e7a48" if row["type"] == "auto" else "#155e92"
            self.app._pill(canvas, sx, sy, fs, 728, row_y - 5, 105, label, bg, fg)
            line(110, row_y + 42, 860, row_y + 42, "#a68cff", 1)

        if len(rows) > 6:
            track_y = y + 105
            track_h = 390
            thumb_h = max(38, track_h * 6 / len(rows))
            max_index = max(1, len(rows) - 6)
            thumb_y = track_y + (track_h - thumb_h) * self.table_scroll_index / max_index
            self.table_scrollbar = (sy(track_y), sy(track_y + track_h))
            self.app._dashboard_round_rect(canvas, sx(875), sy(track_y), sx(883), sy(track_y + track_h), 4, "#e5dcff", "#e5dcff", 0, "table-scrollbar")
            self.app._dashboard_round_rect(canvas, sx(874), sy(thumb_y), sx(884), sy(thumb_y + thumb_h), 5, PRIMARY, PRIMARY, 0, "table-scrollbar")

    def _today(self):
        return datetime.now().date()

    def _clamp_date(self, value):
        return max(SYSTEM_START_DATE, min(self._today(), value))

    def _format_full_date(self, value):
        return f"{value.day} {MONTH_NAMES[value.month - 1]} {value.year}"

    def _month_is_available(self, year, month):
        first_day = date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        last_date = date(year, month, last_day)
        return last_date >= SYSTEM_START_DATE and first_day <= self._today()

    def _prepare_picker_state(self):
        period = self.pending_period
        if period == "Pilih tanggal":
            self.temp_date = self.selected_date
        elif period == "Mingguan":
            self.temp_date = self.selected_week_start
        else:
            self.temp_year = self.selected_year
            self.temp_month = self.selected_month
        self.calendar_year = self.temp_date.year if period in ("Pilih tanggal", "Mingguan") else self.temp_year
        self.calendar_month = self.temp_date.month if period in ("Pilih tanggal", "Mingguan") else self.temp_month

    def _move_calendar_month(self, delta):
        year = self.calendar_year
        month = self.calendar_month + delta
        if month < 1:
            month = 12
            year -= 1
        elif month > 12:
            month = 1
            year += 1
        if not self._month_is_available(year, month):
            return
        self.calendar_year = year
        self.calendar_month = month
        self.draw()

    def _move_picker_year(self, delta):
        next_year = self.temp_year + delta
        if SYSTEM_START_DATE.year <= next_year <= self._today().year:
            self.temp_year = next_year
            if self.pending_period == "Bulan" and not self._month_is_available(self.temp_year, self.temp_month):
                self.temp_month = self._first_available_month(self.temp_year)
            self.draw()

    def _first_available_month(self, year):
        for month in range(1, 13):
            if self._month_is_available(year, month):
                return month
        return self._today().month

    def _select_picker_day(self, index):
        first_weekday, last_day = calendar.monthrange(self.calendar_year, self.calendar_month)
        day_number = index - first_weekday + 1
        if not (1 <= day_number <= last_day):
            return
        selected = date(self.calendar_year, self.calendar_month, day_number)
        if SYSTEM_START_DATE <= selected <= self._today():
            self.temp_date = selected
            self.draw()

    def _select_picker_month(self, month):
        if self._month_is_available(self.temp_year, month):
            self.temp_month = month
            self.draw()

    def _finish_picker(self):
        period = self.pending_period
        if period == "Pilih tanggal":
            self.selected_date = self._clamp_date(self.temp_date)
        elif period == "Mingguan":
            selected = self._clamp_date(self.temp_date)
            self.selected_week_start = selected - timedelta(days=selected.weekday())
        elif period == "Bulan":
            self.selected_year = self.temp_year
            self.selected_month = self.temp_month
        elif period == "Tahunan":
            self.selected_year = self.temp_year
        self.period = period
        self.selected_day = None
        self.show_picker_popup = False
        self.table_scroll_index = 0
        self.draw()

    def _draw_picker_popup(self, canvas, sx, sy, fs, rect, text, line, y_unit):
        top = self.canvas.canvasy(0)
        canvas.create_rectangle(0, top, self.canvas.winfo_width(), top + self.canvas.winfo_height(),
                                fill="#000000", stipple="gray25", outline="", tags="popup")

        popup_width = 470
        period = self.pending_period
        popup_height = 430 if period in ("Pilih tanggal", "Mingguan") else 350
        y_offset = top / y_unit
        visible_height = self.canvas.winfo_height() / y_unit
        x0 = (FIGMA_WIDTH - popup_width) / 2
        y0 = y_offset + max(18, (visible_height - popup_height) / 2)

        rect(x0, y0, popup_width, popup_height, 20, "#ffffff", shadow=True, tags="popup")
        title = {
            "Pilih tanggal": "Pilih Tanggal",
            "Mingguan": "Pilih Minggu",
            "Bulan": "Pilih Bulan",
            "Tahunan": "Pilih Tahun",
        }.get(period, "Pilih Waktu")
        text(x0 + 24, y0 + 20, title, 20, "bold", tags="popup")
        text(x0 + popup_width - 70, y0 + 24, "Batal", 12, "bold", "#6f6876", tags=("popup", "popup-close"))

        if period in ("Pilih tanggal", "Mingguan"):
            self._draw_calendar_picker(canvas, sx, sy, fs, rect, text, x0, y0)
        elif period == "Bulan":
            self._draw_month_picker(canvas, sx, sy, fs, rect, text, x0, y0)
        else:
            self._draw_year_picker(canvas, sx, sy, fs, rect, text, x0, y0)

        rect(x0 + popup_width - 120, y0 + popup_height - 54, 92, 34, 18, PRIMARY, tags=("popup", "picker-done"))
        text(x0 + popup_width - 98, y0 + popup_height - 48, "Selesai", 12, "bold", "#ffffff", tags=("popup", "picker-done"))

    def _draw_calendar_picker(self, canvas, sx, sy, fs, rect, text, x0, y0):
        header = f"{MONTH_NAMES[self.calendar_month - 1]} {self.calendar_year}"
        text(x0 + 170, y0 + 68, header, 16, "bold", "#333333", tags="popup")
        text(x0 + 42, y0 + 67, "<", 18, "bold", PRIMARY, tags=("popup", "picker-prev-month"))
        text(x0 + 410, y0 + 67, ">", 18, "bold", PRIMARY, tags=("popup", "picker-next-month"))

        for index, day_name in enumerate(SHORT_DAY_NAMES):
            text(x0 + 48 + index * 56, y0 + 112, day_name, 12, "bold", "#7169e8", tags="popup")

        first_weekday, last_day = calendar.monthrange(self.calendar_year, self.calendar_month)
        week_start = self.temp_date - timedelta(days=self.temp_date.weekday()) if self.pending_period == "Mingguan" else None
        week_end = week_start + timedelta(days=6) if week_start else None
        for index in range(42):
            day_number = index - first_weekday + 1
            col = index % 7
            row = index // 7
            x = x0 + 34 + col * 56
            y = y0 + 145 + row * 38
            if not (1 <= day_number <= last_day):
                continue
            current = date(self.calendar_year, self.calendar_month, day_number)
            disabled = current < SYSTEM_START_DATE or current > self._today()
            selected = current == self.temp_date
            in_week = self.pending_period == "Mingguan" and week_start <= current <= week_end
            fill = "#e6e1ff" if in_week else "#ffffff"
            if selected:
                fill = PRIMARY
            rect(x, y, 34, 30, 10, fill, outline="#e6e1ff", width=1, tags=("popup", f"picker-day-{index}"))
            color = "#ffffff" if selected else "#b7b2c0" if disabled else "#333333"
            text(x + 10, y + 5, str(day_number), 11, "bold", color, tags=("popup", f"picker-day-{index}"))

    def _draw_month_picker(self, canvas, sx, sy, fs, rect, text, x0, y0):
        text(x0 + 175, y0 + 66, str(self.temp_year), 18, "bold", "#333333", tags="popup")
        text(x0 + 42, y0 + 67, "<", 18, "bold", PRIMARY, tags=("popup", "picker-prev-year"))
        text(x0 + 410, y0 + 67, ">", 18, "bold", PRIMARY, tags=("popup", "picker-next-year"))
        for index, month_name in enumerate(SHORT_MONTH_NAMES):
            month = index + 1
            col = index % 4
            row = index // 4
            x = x0 + 45 + col * 96
            y = y0 + 118 + row * 52
            disabled = not self._month_is_available(self.temp_year, month)
            selected = self.temp_month == month
            fill = PRIMARY if selected else "#f4efff"
            fg = "#ffffff" if selected else "#b7b2c0" if disabled else "#333333"
            rect(x, y, 70, 36, 14, fill, outline="#e6e1ff", width=1, tags=("popup", f"picker-month-{month}"))
            text(x + 19, y + 8, month_name, 11, "bold", fg, tags=("popup", f"picker-month-{month}"))

    def _draw_year_picker(self, canvas, sx, sy, fs, rect, text, x0, y0):
        text(x0 + 42, y0 + 135, "<", 22, "bold", PRIMARY, tags=("popup", "picker-prev-year"))
        text(x0 + 404, y0 + 135, ">", 22, "bold", PRIMARY, tags=("popup", "picker-next-year"))
        rect(x0 + 130, y0 + 110, 210, 80, 20, "#f4efff", outline="#e6e1ff", width=1, tags="popup")
        text(x0 + 202, y0 + 128, str(self.temp_year), 28, "bold", PRIMARY, tags="popup")

# KALENDER SELEKSION
    def _draw_period_popup(self, canvas, sx, sy, fs, rect, text, line, y_unit):
        top = self.canvas.canvasy(0)
        canvas.create_rectangle(0, top, self.canvas.winfo_width(), top + self.canvas.winfo_height(),
                                fill="#000000", stipple="gray25", outline="", tags="popup")

        popup_width = 430
        popup_height = 310
        y_offset = top / y_unit
        visible_height = self.canvas.winfo_height() / y_unit
        x0 = (FIGMA_WIDTH - popup_width) / 2
        y0 = y_offset + max(20, (visible_height - popup_height) / 2)

        # Kotak popup utama
        rect(x0, y0, popup_width, popup_height, 20, "#ffffff", shadow=True, tags="popup")
        text(x0 + 22, y0 + 20, "Interval Waktu", 20, "bold", tags="popup")

        # Garis pembatas
        line(x0 + 215, y0 + 75, x0 + 215, y0 + 250, "#d5b6ff", 1)
        line(x0 + 40, y0 + 160, x0 + 390, y0 + 160, "#d5b6ff", 1)

        # --- Baris atas ---
        # Tanggal
        self._draw_period_icon(canvas, sx, sy, "Tanggal", x0 + 90 + 23, y0 + 120 - 50, "period-Pilih tanggal")
        text(x0 + 70, y0 + 120, "Pilih tanggal", 15, "bold", "#6f6876", tags=("popup", "period-Pilih tanggal"))

        # Tahunan
        self._draw_period_icon(canvas, sx, sy, "Tahunan", x0 + 270 + 23, y0 + 120 - 50, "period-Tahunan")
        text(x0 + 262, y0 + 120, "Pilih tahun", 15, "bold", "#6f6876", tags=("popup", "period-Tahunan"))

        # --- Baris bawah ---
        # Mingguan
        self._draw_period_icon(canvas, sx, sy, "Mingguan", x0 + 80 + 33, y0 + 230 - 50, "period-Mingguan")
        text(x0 + 70, y0 + 230, "Pilih minggu", 15, "bold", "#6f6876", tags=("popup", "period-Mingguan"))

        # Bulan
        self._draw_period_icon(canvas, sx, sy, "Bulanan", x0 + 283 + 13, y0 + 230 - 50, "period-Bulan")
        text(x0 + 262, y0 + 230, "Pilih bulan", 15, "bold", "#6f6876", tags=("popup", "period-Bulan"))

        # Tombol Batal
        text(x0 + 365, y0 + 275, "Batal", 12, "bold", "#6f6876", tags=("popup", "popup-close"))
    def _draw_period_icon(self, canvas, sx, sy, label, x, y, tag):
        filenames = {
            "Tanggal": "tanggal.png",
            "Mingguan": "minggu.png",
            "Tahunan": "tahun.png",
            "Bulanan": "bulan.png",
        }
        image = self._load_icon_image(filenames.get(label, "tanggal.png"), 25, 25)
        if image:
            canvas.create_image(sx(x -14), sy(y), image=image, anchor="nw", tags=("popup", tag))
            return

    def _draw_arrow_image(self, canvas, sx, sy, filename, x, y, width, height, direction, tag):
        image = self._load_arrow_image(filename, width, height, direction)
        if image:
            canvas.create_image(sx(x), sy(y), image=image, anchor="nw", tags=tag)
            return

        points = [sx(x + width / 2), sy(y + height), sx(x), sy(y), sx(x + width), sy(y)] if direction == "down" else [sx(x + width / 2), sy(y), sx(x), sy(y + height), sx(x + width), sy(y + height)]
        canvas.create_polygon(points, fill="#42404a", outline="#42404a", tags=tag)

    def _load_arrow_image(self, filename, width, height, direction):
        key = (filename, width, height, direction)
        if key in self.image_cache:
            return self.image_cache[key]
        if Image is None or ImageTk is None:
            return None

        path = ICON_DIR / filename
        if not path.exists():
            return None

        resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
        image = Image.open(path).convert("RGBA")
        if direction == "down" and ImageOps is not None:
            image = ImageOps.flip(image)
        image = image.resize((max(1, width), max(1, height)), resample)
        photo = ImageTk.PhotoImage(image)
        self.image_cache[key] = photo
        return photo

    def _load_icon_image(self, filename, width, height):
        key = (filename, width, height)
        if key in self.image_cache:
            return self.image_cache[key]
        if Image is None or ImageTk is None:
            return None

        path = ICON_DIR / filename
        if not path.exists():
            return None

        resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
        image = Image.open(path).convert("RGBA")
        image = image.resize((max(1, width), max(1, height)), resample)
        photo = ImageTk.PhotoImage(image)
        self.image_cache[key] = photo
        return photo

    def _history_rows(self):
        try:
            raw_rows = self.app.db.get_feed_history(1000)
        except Exception as exc:
            self.app._warn_database_once(exc)
            raw_rows = []

        rows = []
        for raw in raw_rows:
            if isinstance(raw, dict):
                action_type = raw.get("action_type", "manual")
                message = raw.get("message", "")
                created_at = raw.get("created_at", datetime.now())
            else:
                action_type, _status, message, _feed_percentage, created_at = raw
            if not isinstance(created_at, datetime):
                created_at = datetime.now()
            if not self._inside_selected_period(created_at):
                continue
            rows.append(
                {
                    "date": created_at.strftime("%d/%m/%y"),
                    "created_at": created_at,
                    "time": created_at.strftime("%H:%M"),
                    "weekday": created_at.weekday(),
                    "distance": self._distance_from_message(message),
                    "feed_out_percent": self._feed_out_percent_from_message(message),
                    "type": "auto" if str(action_type).lower().startswith("auto") else "manual",
                }
            )
        return rows

    def _inside_selected_period(self, created_at):
        item_date = created_at.date()
        if self.period == "Tahunan":
            return created_at.year == self.selected_year
        if self.period == "Bulan":
            return created_at.year == self.selected_year and created_at.month == self.selected_month
        if self.period == "Pilih tanggal":
            return item_date == self.selected_date

        start = self.selected_week_start
        end = start + timedelta(days=6)
        return start <= item_date <= end

    def _build_chart(self, rows):
        if self.period == "Pilih tanggal":
            return self._daily_chart(rows)
        if self.period == "Bulan":
            return self._monthly_chart(rows)
        if self.period == "Tahunan":
            return self._yearly_chart(rows)
        return self._weekly_chart(rows)

    def _empty_bucket(self, label, tooltip):
        return {"label": label, "tooltip": tooltip, "auto": 0, "manual": 0, "distance": 0}

    def _add_row_to_bucket(self, bucket, row):
        bucket[row["type"]] += 1
        bucket["distance"] = max(bucket["distance"], row["distance"])

    def _daily_chart(self, rows):
        bucket = self._empty_bucket(DAY_NAMES[self.selected_date.weekday()], self._format_full_date(self.selected_date))
        for row in rows:
            self._add_row_to_bucket(bucket, row)
        return [bucket]

    def _weekly_chart(self, rows):
        chart = []
        for offset in range(7):
            day = self.selected_week_start + timedelta(days=offset)
            chart.append(self._empty_bucket(DAY_NAMES[offset], self._format_full_date(day)))
        for row in rows:
            bucket = chart[row["weekday"]]
            self._add_row_to_bucket(bucket, row)
        return chart

    def _monthly_chart(self, rows):
        _, last_day = calendar.monthrange(self.selected_year, self.selected_month)
        chart = []
        start_day = 1
        while start_day <= last_day:
            end_day = min(start_day + 6, last_day)
            start = date(self.selected_year, self.selected_month, start_day)
            end = date(self.selected_year, self.selected_month, end_day)
            label = f"Minggu ke-{len(chart) + 1}"
            tooltip = f"{self._format_full_date(start)} - {self._format_full_date(end)}"
            chart.append(self._empty_bucket(label, tooltip))
            start_day = end_day + 1
        for row in rows:
            week_index = min((row["created_at"].day - 1) // 7, len(chart) - 1)
            self._add_row_to_bucket(chart[week_index], row)
        return chart

    def _yearly_chart(self, rows):
        chart = [
            self._empty_bucket(SHORT_MONTH_NAMES[index], f"{MONTH_NAMES[index]} {self.selected_year}")
            for index in range(12)
        ]
        for row in rows:
            self._add_row_to_bucket(chart[row["created_at"].month - 1], row)
        return chart

    def _distance_from_message(self, message):
        text = str(message).lower().replace("-", " ")
        match = re.search(r"\d+", text)
        if match:
            return int(match.group(0))
        return 3

    def _feed_out_percent_from_message(self, message):
        match = re.search(r"(\d+(?:[.,]\d+)?)\s*%", str(message))
        if not match:
            return DEFAULT_FEED_OUT_PERCENT_PER_EVENT
        return float(match.group(1).replace(",", "."))

    def _period_range_text(self):
        start = self.selected_week_start
        end = start + timedelta(days=6)
        if self.period == "Tahunan":
            return str(self.selected_year)
        if self.period == "Bulan":
            return f"{MONTH_NAMES[self.selected_month - 1]} {self.selected_year}"
        if self.period == "Pilih tanggal":
            return self._format_full_date(self.selected_date)
        return f"{self._format_full_date(start)} - {self._format_full_date(end)}"
