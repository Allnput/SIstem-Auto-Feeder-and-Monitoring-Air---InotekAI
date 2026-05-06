from datetime import datetime
import tkinter as tk


PRIMARY = "#9157f5"
FIGMA_WIDTH = 960
FIGMA_HEIGHT = 640


class FeedPage:
    # Halaman jadwal pakan/autofeeder.
    def __init__(self, app):
        self.app = app
        self._last_canvas_size = None

    def render(self):
        self.app.clear()
        self.app.lock_window_size()

        canvas = tk.Canvas(self.app.window, bg="#f8f5fc", highlightthickness=0, bd=0)
        canvas.pack(expand=True, fill="both")
        canvas.tag_bind("home-nav", "<Button-1>", lambda _event: self.app.show_dashboard(self.app.current_user_name))
        canvas.tag_bind("water-nav", "<Button-1>", lambda _event: self.app.show_water_monitoring_page("suhu"))
        canvas.tag_bind("feed-nav", "<Button-1>", lambda _event: self.app.show_schedule_page())
        canvas.tag_bind("manual-feed", "<Button-1>", lambda _event: self._manual_feed_and_refresh(canvas))
        canvas.tag_bind("history-feed", "<Button-1>", lambda _event: self.app.show_feed_history_page())
        canvas.tag_bind("add-schedule", "<Button-1>", lambda _event: self.app.show_new_feed_page())
        for index in range(20):
            canvas.tag_bind(f"schedule-toggle-{index}", "<Button-1>", lambda _event, value=index: self.app.toggle_feed_schedule(value))
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
        feeder_health = self.app.get_device_health(reading, getattr(reading, "auto_feeder_status", "active"))
        today_schedule = self.app.get_today_schedule()
        total_feed_today = len(today_schedule) + self._manual_feed_count_today()

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

        canvas.create_rectangle(0, 0, width, height, fill="#f8f5fc", outline="#f8f5fc")

        rect(0, 0, 78, 640, 0, "#ffffff", shadow=True)
        rect(8, 20, 61, 52, 0, "#faf7ff")
        self.app._draw_icon_image(canvas, sx, sy, scale, "logo inotekai.jpeg", 8, 20, 61, 52, fallback=lambda: text(12, 35, "InotekAI", 10, "bold", PRIMARY))
        self.app._draw_icon_image(canvas, sx, sy, scale, "home hitam.png", 22, 235, 38, 38, fallback=lambda: self.app._draw_home_icon(canvas, sx, sy, scale, 24, 243))
        self.app._draw_icon_image(canvas, sx, sy, scale, "water hitam.png", 22, 300, 42, 42, fallback=lambda: self.app._draw_water_icon(canvas, sx, sy, scale, 21, 302, label=True))
        self.app._draw_icon_image(canvas, sx, sy, scale, "fish ungu.png", 15, 360, 50, 50, fallback=lambda: self.app._draw_fish_icon(canvas, sx, sy, scale, 17, 367, color=PRIMARY))
        self._sidebar_hitbox(canvas, sx, sy, 206, 284, "home-nav")
        self._sidebar_hitbox(canvas, sx, sy, 284, 352, "water-nav")
        self._sidebar_hitbox(canvas, sx, sy, 352, 430, "feed-nav")

        rect(93, 20, 610, 598, 40, "#ffffff", shadow=True)
        self.app._draw_icon_image(canvas, sx, sy, scale, "fish ungu.png", 118, 42, 64, 64, fallback=lambda: self.app._draw_fish_icon(canvas, sx, sy, scale, 120, 45, color=PRIMARY))
        text(193, 48, "Auto Feeder Status", 24, "bold")
        circle(198, 89, 12, feeder_health["color"])
        text(213, 82, feeder_health["label"], 16)
        
        rect(500, 35, 180, 50, 10, "#eeedfe", shadow=True, tags="history-feed")
        text(515, 48, "Riwayat Pakan", 16, "bold", tags="history-feed")
        text(657, 45, ">", 18, "bold", PRIMARY, tags="history-feed")
        line(133, 120, 672, 120, PRIMARY, 1)

        text(120, 150, "Jadwal Pakan", 24, "bold")
        if self.app.feed_schedules:
            for index, schedule in enumerate(self.app.feed_schedules[:4]):
                self._schedule_row(
                    canvas,
                    sx,
                    sy,
                    fs,
                    rect,
                    120,
                    195 + index * 80,
                    index,
                    schedule["time"],
                    schedule["detail"],
                    schedule["active"],
                )
        else:
            text(120, 215, "Belum ada jadwal pakan", 20, "bold", "#8b8b8b")
            text(120, 250, "Tekan tombol + untuk membuat jadwal baru.", 15, fill="#8b8b8b")
# KOTAK PLUS UNTUK TAMBAH JADWAL PAKAN
        rect(610, 535, 70, 68, 12, "#eeedfe", shadow=True, tags="add-schedule")
        text(624, 516, "+", 52, "bold", PRIMARY, tags="add-schedule")
        
# BAGIAN KANAN UNTUK STATUS PAKAN DAN JADWAL HARI INI
        rect(715, 20, 220, 340, 24, "#ffffff", shadow=True)
        rect(730, 32, 190, 145, 12, "#e6f1fb")
        text(740, 40, "Total pemberian\npakan hari ini", 18, "bold", justify="left")
        line(746, 102, 910, 102, "#6aa6d8", 1)
        text(808, 87, str(total_feed_today), 52, "bold", justify="center")
        text(749, 188, "Jadwal hari ini", 20)
        line(748, 222, 900, 222, PRIMARY, 1)
        if today_schedule:
            for index, schedule in enumerate(today_schedule[:3]):
                row_y = 240 + index * 33
                fill = "#000000" if schedule["status"] == "Next" else "#c0c0c0"
                text(748, row_y, schedule["time"], 20, fill=fill)
                self.app._pill(canvas, sx, sy, fs, 818, row_y, 110, schedule["status_text"], schedule["status_bg"], schedule["status_fg"])
        else:
            text(755, 250, "Kosong", 18, "bold", "#8b8b8b")

        card_fill = "#ffffff" if feeder_health["active"] else "#f2f2f2"
        button_fill = "#eeedfe" if feeder_health["active"] else "#d9d9d9"
        manual_tag = "manual-feed" if feeder_health["active"] else None
        text_fill = "#000000" if feeder_health["active"] else "#7f8c8d"
        rect(715, 380, 220, 238, 30, card_fill, shadow=True)
        circle(736, 398, 12, feeder_health["color"])
        text(752, 392, feeder_health["label"], 16, fill=text_fill)
        text(775, 460, "Manual\nFeed", 24, "bold", fill=text_fill, justify="center")
        self.app._draw_icon_image(canvas, sx, sy, scale, "fish ungu.png", 865, 510, 28, 28, fallback=lambda: self.app._draw_feed_button_icon(canvas, sx, sy, scale, 876, 491))
        rect(724, 570, 210, 35, 28, button_fill, tags=manual_tag)
        text(734, 575, "Tap untuk memberi makan", 15, fill=text_fill, tags=manual_tag)

# Fungsi tambahan untuk menggambar elemen jadwal pakan dan hitbox sidebar.
    def _schedule_row(self, canvas, sx, sy, fs, rect, x, y, index, time_text, detail_text, active):
        tag = f"schedule-toggle-{index}"
        row_fill = "#EEEDFE" if active else "#F5F5F5"
        text_fill = "#040000" if active else "#040000"
        track_fill = "#ffffff" if active else "#eeeeee"
        knob_fill = "#9747FF" if active else "#D9D9D9"
        knob_x = x + 465 if active else x + 442
        rect(x, y, 555, 70, 26, row_fill, shadow=True)
        canvas.create_text(sx(x + 32), sy(y + 1), text=time_text, anchor="nw", font=("Segoe UI", fs(34), "bold"), fill=text_fill)
        canvas.create_text(sx(x + 30), sy(y + 48), text=detail_text, anchor="nw", font=("Segoe UI", fs(14)), fill=text_fill)
        self.app._dashboard_round_rect(canvas, sx(x + 430), sy(y + 23), sx(x + 515), sy(y + 55), 18, track_fill, "#eeeeee", 1, tag)
        canvas.create_oval(sx(knob_x), sy(y + 22), sx(knob_x + 40), sy(y + 56), fill=knob_fill, outline=knob_fill, tags=tag)

    def _sidebar_hitbox(self, canvas, sx, sy, y1, y2, tag):
        # Area klik sidebar dibuat lebih besar dari icon agar mudah disentuh di LCD.
        canvas.create_rectangle(sx(0), sy(y1), sx(78), sy(y2), fill="", outline="", tags=tag)

    def _manual_feed_and_refresh(self, canvas):
        self.app.manual_feed()
        if canvas.winfo_exists():
            self.draw(canvas)

    def _manual_feed_count_today(self):
        try:
            raw_rows = self.app.db.get_feed_history(100)
        except Exception as exc:
            self.app._warn_database_once(exc)
            return 0

        today = datetime.now().date()
        total = 0
        for raw in raw_rows:
            if isinstance(raw, dict):
                action_type = raw.get("action_type", "")
                status = raw.get("status", "")
                created_at = raw.get("created_at", datetime.now())
            else:
                action_type, status, _message, _feed_percentage, created_at = raw

            if not isinstance(created_at, datetime):
                continue
            if created_at.date() != today:
                continue
            if str(action_type).lower().startswith("manual") and str(status).lower() == "success":
                total += 1
        return total
