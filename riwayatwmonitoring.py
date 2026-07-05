import calendar
from datetime import date, datetime, timedelta, time
from pathlib import Path
import openpyxl
from database import Database
import tkinter as tk
from tkinter import messagebox
from tkcalendar import Calendar
from tkinter import ttk


PRIMARY = "#9157f5"
FIGMA_WIDTH = 960
FIGMA_HEIGHT = 640
CONTENT_HEIGHT = 1270
PH_MIN = 0
PH_MAX = 15
PH_TICKS = [0, 3, 6, 9, 12, 15]
SHORT_DAY_NAMES = ["S", "S", "R", "K", "J", "S", "M"]
SHORT_MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
MONTH_NAMES = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]
SYSTEM_START_DATE = date(2026, 5, 1)


class RiwayatWaterMonitoringPage:
    def __init__(self, app, mode="ph"):
        self.app = app
        self.db = Database()
        self.data = []
        self.mode = mode
        self.period = "Mingguan"
        today = datetime.now().date()
        today = self._today()
        self.selected_date = today
        self.selected_week_start = today - timedelta(days=today.weekday())
        self.selected_month = today.month
        self.selected_year = today.year
        self.show_period_popup = False
        self.canvas = None
        self._last_canvas_size = None
        self.selected_point = None
        self.show_picker_popup = False

        self.calendar_year = today.year
        self.calendar_month = today.month

        self.picker_year = today.year
        self.picker_month = today.month
        self.table_scroll_index = 0
        self.current_rows = []
        self._is_dragging_scroll = False
            
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure("Inotek.TCombobox",
                        fieldbackground="#ffffff",     # Warna latar area teks
                        background=PRIMARY,            # Warna latar tombol panah (Ungu)
                        foreground="#000000",          # Warna teks
                        arrowcolor="#ffffff",          # Warna ikon panah (Putih)
                        bordercolor=PRIMARY,           # Warna garis pinggir (Ungu)
                        lightcolor=PRIMARY,
                        darkcolor=PRIMARY,
                        padding=2)                     # Padding internal (memperbesar tinggi kotak)
        style.map("Inotek.TCombobox",
                fieldbackground=[("readonly", "#ffffff")],
                selectbackground=[("readonly", PRIMARY)],
                selectforeground=[("readonly", "#ffffff")])

    def render(self):
        self.app.clear()
        self.app.lock_window_size()

        self.canvas = tk.Canvas(self.app.window, bg="#f8f5fc", highlightthickness=0, bd=0)
        self.canvas.pack(side="left", expand=True, fill="both")
        self.sidebar_canvas = tk.Canvas(self.app.window, bg="#ffffff", highlightthickness=0, bd=0)

        self._bind_actions()
        self.canvas.update_idletasks()
        self._load_data()
        self.canvas.bind("<Configure>", self._redraw_when_resized)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        
    def _load_data(self):
        self.current_rows = self._history_rows()
        self.table_scroll_index = 0
        self.draw()

    def _bind_actions(self):
        self.sidebar_canvas.tag_bind("home-nav", "<Button-1>", lambda _event: self.app.show_dashboard(self.app.current_user_name))
        self.sidebar_canvas.tag_bind("water-nav", "<Button-1>", lambda _event: self.app.show_water_history())
        self.sidebar_canvas.tag_bind("notif-nav", "<Button-1>", lambda _event: self.app.show_notification())
        self.canvas.tag_bind("period", "<Button-1>", lambda _event: self._toggle_period_popup())
        self.canvas.tag_bind("scroll-thumb", "<Button-1>", self._start_scroll)
        self.canvas.tag_bind("scroll-track", "<Button-1>", self._click_track)
        self.canvas.bind("<B1-Motion>", self._drag_scroll)
        self.canvas.bind("<ButtonRelease-1>", self._stop_scroll)
        self.canvas.tag_bind("download", "<Button-1>", lambda _event: self._download_excel())
        self.canvas.tag_bind("popup-close", "<Button-1>", lambda _event: self._cancel_picker())
        self.canvas.tag_bind("picker-done", "<Button-1>", lambda _event: self._finish_picker())
        for label in ["tanggal", "Tahunan", "Mingguan", "Bulan"]:
            self.canvas.tag_bind(f"period-{label}", "<Button-1>", lambda _event, value=label: self._select_period(value))
        for index in range(12):
            self.canvas.tag_bind(f"bar-{index}", "<Button-1>", lambda _event, value=index: self._select_day(value))

    def _redraw_when_resized(self, event):
        size = (event.width, event.height)
        if size == self._last_canvas_size:
            return
        self._last_canvas_size = size
        self.draw()

    def _on_mousewheel(self, event):
        y = self.canvas.canvasy(event.y)
        if 675 <= y <= 1300 and hasattr(self, 'current_rows') and len(self.current_rows) > 10:
            direction = -1 if event.delta > 0 else 1
            max_scroll = len(self.current_rows) - 10
            
            new_index = self.table_scroll_index + direction
            self.table_scroll_index = max(0, min(max_scroll, new_index))
            self.draw()
            return "break"
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _switch_mode(self, mode):
        self.mode = mode
        self.selected_point = None
        self.draw()

    def _select_period(self, value):
        self.pending_period = value
        self._backup_state()   # <-- TAMBAH INI
        self.show_period_popup = False
        self.show_picker_popup = True
        self._prepare_picker_state()
        self.draw()

    def _toggle_period_popup(self):
        self.show_period_popup = not self.show_period_popup
        self.draw()

    def draw(self):
        canvas = self.canvas
        rows = self.current_rows
        self._last_canvas_size = (canvas.winfo_width(), canvas.winfo_height())
        canvas.delete("all")

        width = max(canvas.winfo_width(), self.app.width)
        height = max(canvas.winfo_height(), self.app.height)
        scale = min(width / self.app.width, height / self.app.height)
        ox = (width - self.app.width * scale) / 2
        x_ratio = self.app.width / FIGMA_WIDTH
        y_ratio = self.app.height / FIGMA_HEIGHT
        self._sy_factor = y_ratio * scale
        
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
        summary = self._summary(rows)

        self._draw_sidebar(sx, sy, scale, x_ratio, y_ratio)
        rect(90, 20, 845, 600, 45, "#ffffff", shadow=True)
        rect(90, 650, 845, 600, 45, "#ffffff", shadow=True)

        self.app._draw_icon_image(canvas, sx, sy, scale, "water ungu.png", 116, 38, 58, 58, fallback=lambda: self.app._draw_water_icon(canvas, sx, sy, scale, 120, 40, label=True, color=PRIMARY))
        text(190, 42, "Riwayat Kondisi Air", 27, "bold")
        # self._draw_tabs(rect, text)

        rect(740, 51, 120, 38, 28, PRIMARY, tags="download")
        text(773, 59, "Unduh", 14, "bold", "#ffffff", tags="download")
        line(150, 130, 850, 130, PRIMARY, 1)

        text(195, 95, "Periode", 16, "bold", "#333333")
        rect(280, 94, 115, 27, 16, "#e6e1ff", tags="period")
        text(290, 95, self.period, 12, "bold", "#42404a", tags="period")
        text(490, 150, self._period_range_text(), 16, "bold", "#111111", anchor="n")
        text(805, 133, "↓", 15, "bold", "#ffffff", tags="download")

        self._summary_card(rect, text, 110, 190, "Rata-rata " + ("pH"), self.app.format_number(summary["average"]), "#eeedfe", PRIMARY)
        self._summary_card(rect, text, 270, 190, "Terendah", self.app.format_number(summary["min"]), "#eeedfe", PRIMARY, summary["min_label"])
        self._summary_card(rect, text, 430, 190, "Tertinggi", self.app.format_number(summary["max"]), "#eeedfe", PRIMARY, summary["max_label"])
        self._summary_card_status(rect, text, line, 600, 190, "Status", summary["status"]["label"], "#e6f1fb", summary["status"]["color"])
        
        title = "Grafik pH air"
        text(165, 305, title, 18, "bold")
        canvas.create_rectangle(sx(565), sy(325), sx(576), sy(336), fill=summary["status"]["color"], outline="#000000")
        text(582, 318, "Status air", 11)
        line(662, 331, 685, 331, "#000000", 1, dash=(4, 2))
        text(696, 318, "Batas normal", 11)

        if self.period == "tanggal":
            half_hour_buckets = {}
            for h in range(24):
                half_hour_buckets[(h, 0)] = []
                half_hour_buckets[(h, 30)] = []
            for row in rows:
                if row["ph_level"] is not None:
                    hour = row["synced_at"].hour
                    minute_bucket = 0 if row["synced_at"].minute < 30 else 30
                    
                    half_hour_buckets[(hour, minute_bucket)].append(row["ph_level"])
            chart_data = []
            for (hour, minute), values in half_hour_buckets.items():
                if values:
                    avg_value = sum(values) / len(values)
                    dt = datetime.combine(self.selected_date, time(hour=hour, minute=minute, second=0))
                    
                    chart_data.append({
                        "time": dt, 
                        "value": avg_value
                    })
            self.app.draw_chart_today(canvas, sx, sy, fs, line, text, PRIMARY, PRIMARY, chart_data)
        else:
            self._draw_chart(canvas, sx, sy, fs, line, text, chart)

        self._draw_table(canvas, sx, sy, fs, rect, text, line, rows)
        if self.show_period_popup:
            self._draw_period_popup(canvas, sx, sy, fs, rect, text, line, y_ratio * scale)
        if self.show_picker_popup:
            self._draw_picker_popup(canvas, sx, sy, fs, rect, text, line, y_ratio * scale)

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

        self._period_choice(rect, text, x0 + 60, y0 + 92, "tanggal")
        self._period_choice(rect, text, x0 + 262, y0 + 92, "Tahunan")
        self._period_choice(rect, text, x0 + 70, y0 + 178, "Mingguan")
        self._period_choice(rect, text, x0 + 272, y0 + 178, "Bulan")

    def _period_choice(self, rect, text, x, y, label):
        active = self.period == label
        rect(x - 14, y - 8, 132, 44, 14, PRIMARY if active else "#f4efff", "#e2d8ff", 1, tags=("popup", f"period-{label}"))
        text(x, y + 5, label, 11, "bold", "#ffffff" if active else "#6f6876", tags=("popup", f"period-{label}"))

    def _draw_sidebar(self, sx_main, sy_main, scale, x_ratio, y_ratio):
        canvas = self.sidebar_canvas
        canvas.delete("all")
        sidebar_width = 78 * x_ratio * scale

        canvas.place(x=sx_main(0), y=0, width=sidebar_width, height=self.app.height)

        def sx(value): return value * x_ratio * scale
        def sy(value): return value * y_ratio * scale

        self.app._dashboard_round_rect(canvas, sx(4), sy(5), sx(78 + 4), sy(640 + 5), 0, "#c9c9c9", "#c9c9c9", 0, None)
        canvas.create_rectangle(sx(0), sy(0), sx(78), sy(640), fill="#ffffff", outline="")
        self.app._dashboard_round_rect(canvas, sx(8), sy(20), sx(69), sy(72), 0, "#faf7ff", "#faf7ff", 0, None)
        self.app._draw_icon_image(canvas, sx, sy, scale, "logo inotekai.jpeg", 8, 20, 61, 52, fallback=lambda: canvas.create_text(sx(12), sy(35), text="InotekAI", fill=PRIMARY))
        self.app._draw_icon_image(canvas, sx, sy, scale, "home hitam.png", 22, 235, 38, 38, fallback=lambda: self.app._draw_home_icon(canvas, sx, sy, scale, 24, 243))
        self.app._draw_icon_image(canvas, sx, sy, scale, "water ungu.png", 22, 300, 42, 42, fallback=lambda: self.app._draw_water_icon(canvas, sx, sy, scale, 21, 302, label=True, color=PRIMARY))
        self.app._draw_icon_image(canvas, sx, sy, scale, "notif hitam.png", 15, 360, 50, 50, fallback=lambda: self.app._draw_notif_icon(canvas, sx, sy, scale, 17, 367))
        canvas.create_rectangle(sx(0), sy(206), sx(78), sy(284), fill="", outline="", tags="home-nav")
        canvas.create_rectangle(sx(0), sy(284), sx(78), sy(352), fill="", outline="", tags="water-nav")
        canvas.create_rectangle(sx(0), sy(352), sx(78), sy(430), fill="", outline="", tags="notif-nav")
        
    def _summary_card(self, rect, text, x, y, title, value, bg, value_color, subtitle=""):
        rect(x, y, 145, 92, 20, bg, shadow=True)
        text(x + 15, y + 13, title, 15)
        text(x + 15, y + 35, value, 27, "bold", value_color)
        if subtitle:
            text(x + 15, y + 70, subtitle, 10, fill="#666666")
    
    def _summary_card_status(self, rect, text, line, x, y, title, value, fill, value_color):
        padding_y = 15
        width = 300
        height = 94
        rect(x, y, width, height, 18, fill, shadow=True)

        center_x = x + width / 2

        title_y = y + padding_y
        line_y = title_y + 37
        value_y = y + height / 2 + 15

        text(center_x, title_y + 8, title, 15, "bold", fill="#000000", anchor="center")
        line(x + 20, line_y - 7, x + width - 20, line_y - 7, "#000000", 1)
        text(center_x + 1, value_y + 5, value, 27, "bold", value_color, anchor="center")

    def _draw_chart(self, canvas, sx, sy, fs, line, text, chart):
        left, top, right, bottom = 140, 355, 910, 555

        def y_for(value):
            bounded = max(PH_MIN, min(PH_MAX, float(value)))
            return bottom - ((bounded - PH_MIN) / (PH_MAX - PH_MIN)) * (bottom - top)

        def x_for(index):
            denominator = max(1, len(chart) - 1)
            return left + (index / denominator) * (right - left)

        for tick in PH_TICKS:
            y = y_for(tick)
            line(left, y, right, y, "#dddddd", 1, dash=(2, 2))
            text(left - 30, y - 7, str(tick), 9, fill="#a0a0a0")
        line(left, bottom, right, bottom, "#aaaaaa", 1)
        line(left, top, left, bottom, "#aaaaaa", 1)
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
            self.app.draw_gradient_fill(canvas, sx, sy, point_items, bottom)
        if len(points) >= 4:
            canvas.create_line(points, fill=PRIMARY, width=max(2, int(2 * self.app.height / FIGMA_HEIGHT)), smooth=True)
        for index, value, x, y in point_items:
            color = self.app.ph_color(value)
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
        color = self.app.ph_color(item["value"])
        canvas.create_rectangle(sx(x + 12), sy(y + 16), sx(x + 24), sy(y + 28), fill=color, outline=color, tags="chart-tooltip")
        label = "pH air"
        text(x + 30, y + 7, item["tooltip"], 8, fill="#ffffff", tags="chart-tooltip")
        text(x + 30, y + 23, f"{label}: {self.app.format_number(item['value'])}", 10, "bold", "#ffffff", tags="chart-tooltip")

    def _select_point(self, index):
        self.selected_point = index
        self.draw()

    def _today(self):
        return datetime.now().date()
    
    def _draw_table(self, canvas, sx, sy, fs, rect, text, line, rows):
        table_title = "Riwayat Data pH Air"
        text(115, 675, table_title, 20, "bold")
        
        headers = ["No", "Tanggal", "Waktu", "pH Air", "Status"]
        xs = [118, 185, 345, 510, 685]
        for x, header in zip(xs, headers):
            text(x, 735, header, 15, "bold", "#7169e8")
        visible_count = 10
        total_count = len(rows)
        visible = rows[self.table_scroll_index : self.table_scroll_index + visible_count]
        
        if not visible:
            text(125, 795, "Belum ada riwayat kondisi air.", 17, "bold", "#8b8b8b")
            return
            
        for index, row in enumerate(visible):
            y = 780 + index * 48
            status = self._row_status(row)
            real_number = self.table_scroll_index + index + 1
            
            values = [
                str(real_number),
                row["synced_at"].strftime("%d/%m/%y"),
                row["synced_at"].strftime("%H:%M"),
                self.app.format_number(row["ph_level"]),
                status["label"],
            ]
            for x, value in zip(xs, values):
                fill = status["color"] if x == 685 else "#111111"
                text(x, y, value, 14, "bold", fill)
            line(112, y + 32, 860, y + 32, "#a68cff", 1)

        if total_count > visible_count:
            track_x = 880
            track_y1 = 770
            track_y2 = 1240
            track_h = track_y2 - track_y1

            rect(track_x, track_y1, 8, track_h, 4, "#e6e6e6", tags="scroll-track")
            thumb_h = max(40, track_h * (visible_count / total_count))
            scroll_ratio = self.table_scroll_index / (total_count - visible_count)
            thumb_y = track_y1 + scroll_ratio * (track_h - thumb_h)
            rect(track_x - 1, thumb_y, 10, thumb_h, 5, "#ffffff", PRIMARY, 2, tags="scroll-thumb")

    def _history_rows(self):
        if self.period == "tanggal":
            start_date = self.selected_date
            end_date = self.selected_date
            
        elif self.period == "Mingguan":
            start_date = self.selected_week_start
            end_date = start_date + timedelta(days=6)
            
        elif self.period == "Bulan":
            start_date = date(self.selected_year, self.selected_month, 1)
            _, last_day = calendar.monthrange(self.selected_year, self.selected_month)
            end_date = date(self.selected_year, self.selected_month, last_day)
            
        elif self.period == "Tahunan":
            start_date = date(self.selected_year, 1, 1)
            end_date = date(self.selected_year, 12, 31)

        raw_rows = self.db.get_water_history_by_date_range(start_date, end_date)
        rows = [self._normalize_row(row) for row in raw_rows]
        return [row for row in rows if row is not None]

    def _normalize_row(self, row):
        try:
            if isinstance(row, dict):
                synced_at = row.get("last_synced")
                ph_level = row.get("ph_level")
                ph_status_label = row.get("status_label_ph")
                ph_status_color = row.get("status_color_ph")
            else:
                (
                    ph_level,
                    ph_status_label,
                    ph_status_color,
                    timestamp
                ) = row
                synced_at = self.db._parse_datetime(timestamp)

            return {
                "ph_level": float(ph_level),
                "synced_at": synced_at,
                "status_label_ph": ph_status_label,
                "status_color_ph": ph_status_color,
            }

        except (TypeError, ValueError):
            return None
    def _inside_period(self, synced_at):
        if self.period == "tanggal":
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
        metric = "ph_level"
        for row in rows:
            bucket = self._bucket_for(row["synced_at"], buckets)
            if bucket is not None:
                bucket["values"].append(row[metric])
        for bucket in buckets:
            values = bucket["values"]
            bucket["value"] = sum(values) / len(values) if values else None
        return buckets

    def _chart_buckets(self):
        if self.period == "tanggal":
            base = datetime.combine(self.selected_date, datetime.min.time())
            return [{"label": f"{hour:02d}.00", "tooltip": f"{hour:02d}.00-{min(hour + 3, 23):02d}.59", "start": base.replace(hour=hour), "values": []} for hour in range(0, 24, 4)]
        if self.period == "Bulan":
            _, last_day = calendar.monthrange(self.selected_year, self.selected_month)
            buckets = []
            
            for day in range(1, last_day + 1):
                # Atur label bawah agar hanya muncul seminggu sekali
                if day == 1: label_bawah = "Minggu ke-1"
                elif day == 8: label_bawah = "Minggu ke-2"
                elif day == 15: label_bawah = "Minggu ke-3"
                elif day == 22: label_bawah = "Minggu ke-4"
                elif day == 29: label_bawah = "Minggu ke-5"
                else: label_bawah = "" # Kosongkan hari lainnya agar tidak menumpuk
                
                buckets.append({
                    "label": label_bawah, 
                    "tooltip": f"{day} {MONTH_NAMES[self.selected_month - 1]} {self.selected_year}", 
                    "day": day, 
                    "values": []
                })
            return buckets
        if self.period == "Tahunan":
            return [{"label": SHORT_MONTH_NAMES[index], "tooltip": f"{MONTH_NAMES[index]} {self.selected_year}", "month": index + 1, "values": []} for index in range(12)]
        start = self.selected_week_start
        return [{"label": (start + timedelta(days=offset)).strftime("%d %b"), "tooltip": (start + timedelta(days=offset)).strftime("%d/%m/%Y"), "date": start + timedelta(days=offset), "values": []} for offset in range(7)]

    def _bucket_for(self, synced_at, buckets):
        if self.period == "tanggal":
            return buckets[synced_at.hour // 4]
        if self.period == "Bulan":
            return buckets[synced_at.day - 1]
        if self.period == "Tahunan":
            return buckets[synced_at.month - 1]
        for bucket in buckets:
            if bucket["date"] == synced_at.date():
                return bucket
        return None

    def _summary(self, rows):
        available = [row for row in rows if row["ph_level"] is not None]
        
        if not available:
            return {"average": None, "min": None, "max": None, "min_label": "", "max_label": "", "status": {"label": "-", "color": "#95A5A6"}}
            

        values = [row["ph_level"] for row in available]
        average = sum(values) / len(values)
        low_row = min(available, key=lambda r: r["ph_level"])
        high_row = max(available, key=lambda r: r["ph_level"])
        if self.period == "tanggal":
            min_label = low_row["synced_at"].strftime("%H:%M")
            max_label = high_row["synced_at"].strftime("%H:%M")
        else:
            min_label = low_row["synced_at"].strftime("%d/%m")
            max_label = high_row["synced_at"].strftime("%d/%m")
            
        status = self.app.ph_status(average)
        
        return {
            "average": average, 
            "min": low_row["ph_level"], 
            "max": high_row["ph_level"], 
            "min_label": min_label, 
            "max_label": max_label, 
            "status": status
        }

    def _row_status(self, row):
        return self.app.ph_status(row["ph_level"])

    def _download_excel(self):
        if self.period == "tanggal":
            start_date = self.selected_date
            end_date = self.selected_date
        elif self.period == "Mingguan":
            start_date = self.selected_week_start
            end_date = start_date + timedelta(days=6)
        elif self.period == "Bulan":
            start_date = date(self.selected_year, self.selected_month, 1)
            _, last_day = calendar.monthrange(self.selected_year, self.selected_month)
            end_date = date(self.selected_year, self.selected_month, last_day)
        elif self.period == "Tahunan":
            start_date = date(self.selected_year, 1, 1)
            end_date = date(self.selected_year, 12, 31)

        # 3. Query KHUSUS ke Database untuk menarik 4 kolom spesifik
        query = """
            SELECT id_ph, ph_level, ph_status_label, timestamp
            FROM monitoring_air
            WHERE DATE(timestamp) BETWEEN ? AND ?
            ORDER BY timestamp DESC
        """
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # Eksekusi Query
        with self.db._connect() as conn:
            rows = conn.execute(query, (start_str, end_str)).fetchall()
            
        if not rows:
            messagebox.showinfo("Unduh", "Belum ada data untuk diunduh pada periode ini.")
            return

        # 4. Buat File Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Riwayat pH Air"
        
        # Tulis Header (Judul Kolom)
        ws.append(["id_ph", "ph_level", "ph_status_label", "timestamp"])
        
        # Tulis isi data dari database baris per baris
        for row in rows:
            ws.append([
                row[0], # id_ph
                row[1], # ph_level
                row[2], # ph_status_label
                row[3]  # timestamp
            ])
            
        bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                 "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        
        # Format string untuk tanggal mulai dan selesai
        start_name = f"{start_date.day}_{bulan[start_date.month - 1]}_{start_date.year}"
        end_name = f"{end_date.day}_{bulan[end_date.month - 1]}_{end_date.year}"
        
        # Logika penamaan berdasarkan rentang waktu
        if start_date == end_date:
            # Jika user memilih "Tanggal" (hanya 1 hari)
            filename = f"riwayat_kondisi_air_{start_name}.xlsx"
        else:
            # Jika user memilih Mingguan, Bulan, atau Tahunan (ada rentang)
            filename = f"riwayat_kondisi_air_{start_name}_sampai_{end_name}.xlsx"
            
        path = Path(__file__).resolve().parent / filename
        
        try:
            wb.save(path)
            messagebox.showinfo("Berhasil", f"File Excel berhasil disimpan ")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan file Excel:\n{e}")


    def _period_range_text(self):
        if self.period == "tanggal":
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

    def _prepare_picker_state(self):
        period = self.pending_period
        if period == "tanggal":
            self.temp_date = self.selected_date
        elif period == "Mingguan":
            self.temp_date = self.selected_week_start
        else:
            self.temp_year = self.selected_year
            self.temp_month = self.selected_month
        self.calendar_year = self.temp_date.year if period in ("tanggal", "Mingguan") else self.temp_year
        self.calendar_month = self.temp_date.month if period in ("tanggal", "Mingguan") else self.temp_month

    def _draw_picker_popup(self, canvas, sx, sy, fs, rect, text, line, y_unit):
        top = self.canvas.canvasy(0)
        canvas.create_rectangle(0, top, self.canvas.winfo_width(), top + self.canvas.winfo_height(),
                                fill="#000000", stipple="gray25", outline="", tags="popup")

        # Hitung posisi tengah
        popup_width = 350
        popup_height = 350
        y_offset = top / y_unit
        visible_height = self.canvas.winfo_height() / y_unit
        x0 = (FIGMA_WIDTH - popup_width) / 2
        y0 = y_offset + max(18, (visible_height - popup_height) / 2)
        rect(x0, y0, popup_width, popup_height, 20, "#ffffff", shadow=True, tags="popup")
        
        title = "Pilih Tanggal" if self.pending_period in ("tanggal", "Mingguan") else "Pilih Waktu"
        text(x0 + 24, y0 + 20, title, 18, "bold", tags="popup")
        text(x0 + popup_width - 70, y0 + 24, "Batal", 12, "bold", "#6f6876", tags=("popup", "popup-close"))

        self.picker_frame = tk.Frame(canvas, bg="#ffffff")
        if self.pending_period in ("tanggal", "Mingguan"):
            sel_bg = PRIMARY if self.pending_period == "tanggal" else "#d9d9d9"
            sel_fg = "#ffffff" if self.pending_period == "tanggal" else "#000000"
            self.cal = Calendar(self.picker_frame, selectmode='day',
                                year=self.temp_date.year, 
                                month=self.temp_date.month, 
                                day=self.temp_date.day,
                                background=PRIMARY, bordercolor="#ffffff",
                                headersbackground="#ffffff", normalbackground="#ffffff", 
                                foreground="#000000", normalforeground="#000000",
                                selectbackground=sel_bg, selectforeground=sel_fg,
                                showweeknumbers=False,
                                weekendbackground="#ffffff", weekendforeground="#000000",
                                maxdate=self._today(),
                                font=("Segoe UI", 6)) # <-- TAMBAHKAN PARAMETER FONT INI
            self.cal.pack(expand=True, fill="both", padx=1, pady=1) # Tambahkan sedikit padding
            if self.pending_period == "Mingguan":

                self.cal.tag_config("selected_week", background="#d9d9d9", foreground="#000000")
                self.cal.bind("<<CalendarSelected>>", self._highlight_week)
                self._highlight_week(None)
                
        elif self.pending_period == "Bulan":
            ttk.Label(self.picker_frame, text="Bulan:", background="#ffffff", font=("Segoe UI", 12, "bold")).pack(pady=(0, 2))
            self.cb_month = ttk.Combobox(self.picker_frame, values=MONTH_NAMES, state="readonly", 
                                        style="Inotek.TCombobox", font=("Segoe UI", 12), width=10)
            self.cb_month.current(self.temp_month - 1)
            self.cb_month.pack(pady=0)

            ttk.Label(self.picker_frame, text="Tahun:", background="#ffffff", font=("Segoe UI", 12, "bold")).pack(pady=(0, 2))
            self.cb_year = ttk.Combobox(self.picker_frame, values=list(range(2023, self._today().year + 1)), state="readonly", 
                                        style="Inotek.TCombobox", font=("Segoe UI", 12), width=10)
            self.cb_year.set(self.temp_year)
            self.cb_year.pack(pady=0)

        elif self.pending_period == "Tahunan":
            ttk.Label(self.picker_frame, text="Tahun:", background="#ffffff", font=("Segoe UI", 12, "bold")).pack(pady=(0, 2))
            self.cb_year = ttk.Combobox(self.picker_frame, values=list(range(2023, self._today().year + 1)), state="readonly", 
                                        style="Inotek.TCombobox", font=("Segoe UI", 12), width=10)
            self.cb_year.set(self.temp_year)
            self.cb_year.pack(pady=0)
        self.canvas.create_window(sx(x0 + 20), sy(y0 + 50), window=self.picker_frame, anchor="nw", width=sx(popup_width - 40), height=sy(popup_height - 105), tags="popup-widget")

        rect(x0 + popup_width - 120, y0 + popup_height - 54, 92, 34, 18, PRIMARY, tags=("popup", "picker-done"))
        text(x0 + popup_width - 98, y0 + popup_height - 48, "Selesai", 12, "bold", "#ffffff", tags=("popup", "picker-done"))

    def _finish_picker(self):
        period = self.pending_period
        if period in ("tanggal", "Mingguan"):
            selected_date = self.cal.selection_get()
            
            if period == "tanggal":
                self.selected_date = self._clamp_date(selected_date)
            else:
                selected = self._clamp_date(selected_date)
                self.selected_week_start = selected - timedelta(days=selected.weekday())
                
        elif period == "Bulan":
            self.selected_month = MONTH_NAMES.index(self.cb_month.get()) + 1
            self.selected_year = int(self.cb_year.get())
            
        elif period == "Tahunan":
            self.selected_year = int(self.cb_year.get())

        if hasattr(self, 'picker_frame'):
            self.picker_frame.destroy()

        self.period = period
        self.selected_day = None
        self.show_picker_popup = False
        self.table_scroll_index = 0
        self._load_data()
        
    def _backup_state(self):
        self._backup = {
            "period": self.period,
            "selected_date": self.selected_date,
            "selected_week_start": self.selected_week_start,
            "selected_month": self.selected_month,
            "selected_year": self.selected_year,
        }
        
    def _cancel_picker(self):
        if hasattr(self, 'picker_frame'):
            self.picker_frame.destroy()
            
        self.show_picker_popup = False
        self.show_period_popup = False
        self.pending_period = None
        self.draw()
        
    def _highlight_week(self, event):
        self.cal.calevent_remove('all')

        selected_date = self.cal.selection_get()
        start_of_week = selected_date - timedelta(days=selected_date.weekday())
        for i in range(7):
            current_day = start_of_week + timedelta(days=i)
            if current_day <= self._today():
                self.cal.calevent_create(current_day, 'Minggu Pilihan', 'selected_week')
    
    def _start_scroll(self, event):
        self._is_dragging_scroll = True

    def _stop_scroll(self, event):
        self._is_dragging_scroll = False

    def _click_track(self, event):
        self._is_dragging_scroll = True
        self._drag_scroll(event)

    def _drag_scroll(self, event):
        if not getattr(self, '_is_dragging_scroll', False):
            return
            
        if not hasattr(self, 'current_rows') or len(self.current_rows) <= 10:
            return

        total_count = len(self.current_rows)
        visible_count = 10
        max_scroll = total_count - visible_count

        y = self.canvas.canvasy(event.y)

        sy_factor = getattr(self, '_sy_factor', 1.0)
        figma_y = y / sy_factor if sy_factor != 0 else y
        
        track_y1 = 770
        track_y2 = 1240
        track_h = track_y2 - track_y1
        thumb_h = max(40, track_h * (visible_count / total_count))
        ratio = (figma_y - track_y1 - (thumb_h / 2)) / (track_h - thumb_h)
        ratio = max(0.0, min(1.0, ratio))
        
        new_index = int(round(ratio * max_scroll))
        if new_index != self.table_scroll_index:
            self.table_scroll_index = new_index
            self.draw()