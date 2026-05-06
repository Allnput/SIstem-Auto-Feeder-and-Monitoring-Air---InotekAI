import tkinter as tk
from pathlib import Path
from tkinter import messagebox

try:
    from PIL import Image, ImageOps, ImageTk
except ImportError:
    Image = None
    ImageOps = None
    ImageTk = None


PRIMARY = "#9157f5"
FIGMA_WIDTH = 960
FIGMA_HEIGHT = 640
ICON_DIR = Path(__file__).resolve().parent / "icon"


class FeedNewPage:
    # Halaman form untuk membuat jadwal makan baru.
    def __init__(self, app):
        self.app = app
        self.hour_var = tk.StringVar(value="12")
        self.minute_var = tk.StringVar(value="00")
        self.distance = None
        self.days = set()
        self.canvas = None
        self.time_widgets = []
        self.geometry = None
        self._last_canvas_size = None
        self.image_cache = {}

    def render(self):
        self.app.clear()
        self.app.lock_window_size()

        self.canvas = tk.Canvas(self.app.window, bg="#f8f5fc", highlightthickness=0, bd=0)
        self.canvas.pack(expand=True, fill="both")
        self._bind_actions()
        self.canvas.update_idletasks()
        self.draw()
        self.canvas.bind("<Configure>", self._redraw_when_resized)

    def _redraw_when_resized(self, event):
        size = (event.width, event.height)
        if size == self._last_canvas_size:
            return
        self._last_canvas_size = size
        self.draw()

    def _bind_actions(self):
        self.canvas.tag_bind("cancel", "<Button-1>", lambda _event: self.app.show_schedule_page())
        self.canvas.tag_bind("save", "<Button-1>", lambda _event: self.save_schedule())
        self.canvas.tag_bind("distance-open", "<Button-1>", lambda _event: self.show_distance_popup())
        self.canvas.tag_bind("hour-up", "<Button-1>", lambda _event: self.change_time(hour_delta=1))
        self.canvas.tag_bind("hour-down", "<Button-1>", lambda _event: self.change_time(hour_delta=-1))
        self.canvas.tag_bind("minute-up", "<Button-1>", lambda _event: self.change_time(minute_delta=1))
        self.canvas.tag_bind("minute-down", "<Button-1>", lambda _event: self.change_time(minute_delta=-1))
        for day in ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]:
            self.canvas.tag_bind(f"day-{day}", "<Button-1>", lambda _event, value=day: self.toggle_day(value))
        for distance in range(1, 6):
            self.canvas.tag_bind(f"distance-{distance}", "<Button-1>", lambda _event, value=distance: self.select_distance(value))
        self.canvas.tag_bind("distance-close", "<Button-1>", lambda _event: self.close_distance_popup())

    def save_schedule(self):
        hour = self._parse_number(self.hour_var.get(), 0, 23)
        minute = self._parse_number(self.minute_var.get(), 0, 59)

        if hour is None or minute is None:
            messagebox.showerror("Jadwal Pakan", "Waktu pakan wajib diisi dengan angka yang valid.")
            return
        if self.distance is None:
            messagebox.showerror("Jadwal Pakan", "Jangkauan lontar wajib dipilih.")
            return
        if not self.days:
            messagebox.showerror("Jadwal Pakan", "Minimal satu hari wajib dipilih.")
            return

        selected_days = ", ".join(self._ordered_days())
        schedule = {
            "time": f"{hour:02d}.{minute:02d}",
            "detail": f"{selected_days}-{self.distance} Meter",
            "active": True,
        }
        self.app.add_feed_schedule(schedule)

    def change_time(self, hour_delta=0, minute_delta=0):
        # Panah hanya mengubah StringVar, jadi layar tidak redraw/berkedip.
        hour = self._parse_number(self.hour_var.get(), 0, 23)
        minute = self._parse_number(self.minute_var.get(), 0, 59)
        hour = 0 if hour is None else hour
        minute = 0 if minute is None else minute

        self.hour_var.set(f"{(hour + hour_delta) % 24:02d}")
        self.minute_var.set(f"{(minute + minute_delta) % 60:02d}")

    def toggle_day(self, day):
        if day in self.days:
            self.days.remove(day)
        else:
            self.days.add(day)
        self.draw()

    def show_distance_popup(self):
        self._draw_distance_popup()

    def select_distance(self, value):
        self.distance = value
        self.draw()

    def close_distance_popup(self):
        self.canvas.delete("popup")

    def draw(self):
        canvas = self.canvas
        self._last_canvas_size = (canvas.winfo_width(), canvas.winfo_height())
        canvas.delete("all")
        for widget in self.time_widgets:
            widget.destroy()
        self.time_widgets.clear()
        canvas.configure(bg="#f8f5fc")

        sx, sy, fs, rect, text, line = self._build_geometry()
        canvas.create_rectangle(0, 0, self.geometry["width"], self.geometry["height"], fill="#f8f5fc", outline="#f8f5fc")

        rect(18, 20, 915, 518, 35, "#ffffff", shadow=True)
        self.app._draw_icon_image(canvas, sx, sy, self.geometry["scale"], "fish schedule eat.png", 58, 45, 58, 58, fallback=lambda: self._draw_schedule_icon(canvas, sx, sy, self.geometry["scale"], 58, 52))
        text(128, 58, "Jadwal Makan Baru", 32, "bold")
        line(128, 100, 875, 100, PRIMARY, 1)

        text(405, 135, "Waktu Pakan", 24, "bold")
        self._draw_arrow_image(canvas, sx, sy, "arrow.png", 399, 182, 36, 24, "up", "hour-up")
        self._draw_arrow_image(canvas, sx, sy, "arrow.png", 517, 182, 36, 24, "up", "minute-up")
        self._draw_time_inputs(canvas, sx, sy, fs)
        self._draw_arrow_image(canvas, sx, sy, "arrow.png", 399, 300, 36, 24, "down", "hour-down")
        self._draw_arrow_image(canvas, sx, sy, "arrow.png", 517, 300, 36, 24, "down", "minute-down")

        rect(40, 345, 880, 67, 18, "#eeedfe", shadow=True, tags="distance-open")
        distance_label = "Jangkauan Lontar" if self.distance is None else f"Jangkauan Lontar - {self.distance} Meter"
        text(65, 365, distance_label, 24, "bold", tags="distance-open")
        text(875, 365, ">", 24, "bold", tags="distance-open")

        rect(40, 422, 880, 93, 18, "#ffffff", "#eeeeee", 1, shadow=True)
        text(65, 435, "Ulangi Hari", 22, "bold")
        self._draw_day_toggles(rect, text)

        rect(18, 555, 324, 68, 10, "#ffffff", shadow=True, tags="cancel")
        text(153, 575, "Batal", 22, "bold", tags="cancel")
        rect(370, 555, 550, 68, 10, "#e6f1fb", shadow=True, tags="save")
        text(575, 575, "Simpan Jadwal", 22, "bold", tags="save")

    def _build_geometry(self):
        canvas = self.canvas
        width = max(canvas.winfo_width(), self.app.width)
        height = max(canvas.winfo_height(), self.app.height)
        scale = min(width / self.app.width, height / self.app.height)
        ox = (width - self.app.width * scale) / 2
        oy = (height - self.app.height * scale) / 2
        x_ratio = self.app.width / FIGMA_WIDTH
        y_ratio = self.app.height / FIGMA_HEIGHT
        self.geometry = {
            "width": width,
            "height": height,
            "scale": scale,
            "x_ratio": x_ratio,
            "y_ratio": y_ratio,
        }

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

        return sx, sy, fs, rect, text, line

    def _draw_time_inputs(self, canvas, sx, sy, fs):
        hour_validate = (canvas.register(self._allow_hour), "%P")
        minute_validate = (canvas.register(self._allow_minute), "%P")
        entry_style = {
            "font": ("Segoe UI", fs(48)),
            "justify": "center",
            "bd": 0,
            "relief": "flat",
            "bg": "#ffffff",
            "fg": "#000000",
            "highlightthickness": 0,
            "validate": "key",
        }

        hour_entry = tk.Entry(canvas, textvariable=self.hour_var, width=2, validatecommand=hour_validate, **entry_style)
        minute_entry = tk.Entry(canvas, textvariable=self.minute_var, width=2, validatecommand=minute_validate, **entry_style)
        hour_entry.bind("<FocusOut>", lambda _event: self._format_time_inputs())
        minute_entry.bind("<FocusOut>", lambda _event: self._format_time_inputs())
        self.time_widgets.extend([hour_entry, minute_entry])
        canvas.create_window(sx(410), sy(260), window=hour_entry, width=max(20, int(70 * self.geometry["x_ratio"])), height=max(20, int(65 * self.geometry["y_ratio"])))
        canvas.create_text(sx(470), sy(228), text=":", fill="#000000", anchor="nw", font=("Segoe UI", fs(48)))
        canvas.create_window(sx(535), sy(260), window=minute_entry, width=max(20, int(70 * self.geometry["x_ratio"])), height=max(20, int(65 * self.geometry["y_ratio"])))

    def _draw_day_toggles(self, rect, text):
        days = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
        for index, day in enumerate(days):
            x = 58 + index * 88
            active = day in self.days
            fill = "#eeedfe" if active else "#d9d9d9"
            outline = PRIMARY if active else "#9a9a9a"
            fg = PRIMARY if active else "#666666"
            rect(x, 475, 82, 30, 15, fill, outline, 1, tags=f"day-{day}")
            text(x + 28, 481, day, 14, "bold", fg, tags=f"day-{day}")

    def _draw_distance_popup(self):
        sx, sy, fs, rect, text, line = self._build_geometry()
        canvas = self.canvas
        canvas.delete("popup")
        canvas.create_rectangle(0, 0, self.geometry["width"], self.geometry["height"], fill="#000000", stipple="gray50", outline="", tags="popup")
        rect(40, 345, 880, 145, 18, "#eeedfe", "#d6d1e5", 1, shadow=True, tags="popup")
        text(65, 365, "Jangkauan Lontar", 24, "bold", tags="popup")

        labels = ["1 Meter", "2 Meter", "3 Meter", "4 Meter", "5 Meter"]
        start_x = 140
        step = 170
        y = 463
        selected = self.distance or 4
        line(start_x, y, start_x + step * 4, y, "#c7a7ff", 8)
        line(start_x, y, start_x + step * (selected - 1), y, PRIMARY, 8)
        for index, label in enumerate(labels):
            value = index + 1
            x = start_x + index * step
            label_fill = "#000000" if value == selected else "#8b8b8b"
            text(x - 30, 425, label, 16, "bold" if value == selected else "normal", label_fill, tags=("popup", f"distance-{value}"))
            r = 6 if value != selected else 15
            fill = "#333333" if value != selected else "#ffffff"
            outline = "#333333" if value != selected else PRIMARY
            canvas.create_oval(sx(x) - r, sy(y) - r, sx(x) + r, sy(y) + r, fill=fill, outline=outline, width=max(1, int(3 * self.geometry["scale"])), tags=("popup", f"distance-{value}"))
        text(875, 440, ">", 24, "bold", tags=("popup", "distance-close"))

    def _ordered_days(self):
        order = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
        return [day for day in order if day in self.days]

    def _parse_number(self, value, minimum, maximum):
        if not value.isdigit():
            return None
        number = int(value)
        if minimum <= number <= maximum:
            return number
        return None

    def _allow_hour(self, value):
        if value == "":
            return True
        return value.isdigit() and len(value) <= 2 and 0 <= int(value) <= 23

    def _allow_minute(self, value):
        if value == "":
            return True
        return value.isdigit() and len(value) <= 2 and 0 <= int(value) <= 59

    def _format_time_inputs(self):
        hour = self._parse_number(self.hour_var.get(), 0, 23)
        minute = self._parse_number(self.minute_var.get(), 0, 59)
        self.hour_var.set(f"{0 if hour is None else hour:02d}")
        self.minute_var.set(f"{0 if minute is None else minute:02d}")

    def _draw_schedule_icon(self, canvas, sx, sy, scale, x, y):
        purple = PRIMARY
        size = max(3, int(12 * scale))
        for row in range(3):
            for col in range(3):
                if row == 0 or col == 0:
                    x1 = sx(x + col * 18)
                    y1 = sy(y + row * 18)
                    canvas.create_rectangle(x1, y1, x1 + size, y1 + size, fill=purple, outline=purple)

    def _draw_triangle(self, canvas, sx, sy, scale, x, y, direction, tag):
        stroke = max(2, int(4 * scale))
        if direction == "up":
            points = [sx(x + 16), sy(y), sx(x), sy(y + 16), sx(x + 32), sy(y + 16)]
        else:
            points = [sx(x), sy(y), sx(x + 32), sy(y), sx(x + 16), sy(y + 16)]
        canvas.create_polygon(points, fill="#ffffff", outline="#000000", width=stroke, tags=tag)

    def _draw_arrow_image(self, canvas, sx, sy, filename, x, y, width, height, direction, tag):
        image = self._load_arrow_image(filename, width, height, direction)
        if image:
            canvas.create_image(sx(x), sy(y), image=image, anchor="nw", tags=tag)
            return
        self._draw_triangle(canvas, sx, sy, self.geometry["scale"], x, y, direction, tag)

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
