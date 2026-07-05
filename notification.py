import tkinter as tk

PRIMARY = "#9157f5"
FIGMA_WIDTH = 960
FIGMA_HEIGHT = 640

class NotificationService:
    def __init__(self, app):
        self.app = app
        
    def check_sensor(self):
        current_reading = self.app.sensor.read_water_quality()
        current_status = getattr(current_reading, "sensor_ph_status", "active")
        user_id = 1
        
        last_status = self.app.db.get_last_device_status(user_id)
        
        if current_status != last_status:
            self.app.db.update_device_status(user_id, current_status)
            
            if current_status == "inactive":
                notif_type = "danger"
                title = "Sensor pH Mati"
                desc = "Koneksi sensor terputus, kondisi air tidak terdeteksi."
            else:
                notif_type = "success"
                title = "Sensor pH Kembali Aktif"
                desc = "Sensor berhasil terhubung kembali, memonitor air."
                
            self.app.db.insert_notification(user_id, notif_type, title, desc)

class NotificationPage:
    def __init__(self, app):
        self.app = app
        self.notification_service = NotificationService(app)
        self._last_canvas_size = None 
        
        # --- VARIABEL STATE UNTUK SCROLLING ---
        self.scroll_index = 0
        self._is_dragging_scroll = False
        self.current_notifs = []
        
    def render(self):
        self.app.clear()
        self.app.lock_window_size()
        
        canvas = tk.Canvas(self.app.window, bg="#f8f5fc", highlightthickness=0, bd=0)
        canvas.pack(expand=True, fill="both")
        
        canvas.tag_bind("home-nav", "<Button-1>", lambda _event: self.app.show_dashboard(self.app.current_user_name, mode="ph"))
        canvas.tag_bind("water-nav", "<Button-1>", lambda _event: self.app.show_water_history())
        canvas.tag_bind("notif-nav", "<Button-1>", lambda _event: self.app.show_notification())
        
        # --- BINDING EVENT SCROLLING ---
        canvas.bind("<MouseWheel>", self._on_mousewheel)
        canvas.tag_bind("scroll-thumb", "<Button-1>", self._start_scroll)
        canvas.tag_bind("scroll-track", "<Button-1>", self._click_track)
        canvas.bind("<B1-Motion>", self._drag_scroll)
        canvas.bind("<ButtonRelease-1>", self._stop_scroll)
    
        canvas.update_idletasks()
        self.draw(canvas)
        canvas.bind("<Configure>", self.app.redraw_when_resized)

    # --- FUNGSI LOGIKA SCROLL ---
    def _on_mousewheel(self, event):
        if not hasattr(self, 'current_notifs') or len(self.current_notifs) <= 5:
            return
        direction = -1 if event.delta > 0 else 1
        max_scroll = len(self.current_notifs) - 5
        self.scroll_index = max(0, min(max_scroll, self.scroll_index + direction))
        self.draw(event.widget)
        return "break"

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
        if not hasattr(self, 'current_notifs') or len(self.current_notifs) <= 5:
            return

        total_count = len(self.current_notifs)
        visible_count = 5
        max_scroll = total_count - visible_count
        
        # Sesuaikan dengan skala kanvas
        y = event.widget.canvasy(event.y)
        
        track_y1 = 120
        track_y2 = 600
        track_h = track_y2 - track_y1
        thumb_h = max(40, track_h * (visible_count / total_count))
        
        ratio = (y - track_y1 - (thumb_h / 2)) / (track_h - thumb_h)
        ratio = max(0.0, min(1.0, ratio))
        
        new_index = int(round(ratio * max_scroll))
        if new_index != self.scroll_index:
            self.scroll_index = new_index
            self.draw(event.widget)

    def draw(self, canvas):
        self._last_canvas_size = (canvas.winfo_width(), canvas.winfo_height())
        canvas.delete("all")
        canvas.configure(bg="#f8f5fc")

        self.notification_service.check_sensor()
        self.current_notifs = self.app.db.get_notifications(user_id=1, limit=1000)
        
        width = max(canvas.winfo_width(), self.app.width)
        height = max(canvas.winfo_height(), self.app.height)
        scale = min(width / self.app.width, height / self.app.height)
        ox = (width - self.app.width * scale) / 2
        oy = (height - self.app.height * scale) / 2
        x_ratio = self.app.width / FIGMA_WIDTH
        y_ratio = self.app.height / FIGMA_HEIGHT
        
        def sx(value): return ox + value * x_ratio * scale
        def sy(value): return oy + value * y_ratio * scale
        def fs(size): return max(7, int(size * y_ratio * scale))
        
        def rect(x, y, w, h, r, fill, outline="", width=0, shadow=False, tags=None):
            if shadow:
                self.app._dashboard_round_rect(canvas, sx(x + 4), sy(y + 5), sx(x + w + 4), sy(y + h + 5), r * y_ratio * scale, "#c9c9c9", "#c9c9c9", 0, None)
            self.app._dashboard_round_rect(canvas, sx(x), sy(y), sx(x + w), sy(y + h), r * y_ratio * scale, fill, outline or fill, width, tags)
            
        def text(x, y, value, size, weight="normal", fill="#000000", anchor="nw", tags=None, justify="left"):
            canvas.create_text(sx(x), sy(y), text=value, fill=fill, anchor=anchor, justify=justify, font=("Segoe UI", fs(size), weight), tags=tags)
            
        def line(x1, y1, x2, y2, fill=PRIMARY, width=1, dash=None):
            canvas.create_line(sx(x1), sy(y1), sx(x2), sy(y2), fill=fill, width=max(1, int(width * scale)), dash=dash)
        
        # --- MENGGAMBAR SIDEBAR ---
        rect(0, 0, 78, 640, 0, "#ffffff", shadow=True)
        rect(8, 20, 61, 52, 0, "#faf7ff")
        self.app._draw_icon_image(canvas, sx, sy, scale, "logo inotekai.jpeg", 8, 20, 61, 52, fallback=lambda: text(12, 35, "InotekAI", 10, "bold", PRIMARY))
        self.app._draw_icon_image(canvas, sx, sy, scale, "home hitam.png", 22, 235, 38, 38, fallback=lambda: self.app._draw_home_icon(canvas, sx, sy, scale, 24, 243, PRIMARY))
        self.app._draw_icon_image(canvas, sx, sy, scale, "water hitam.png", 22, 300, 42, 42, fallback=lambda: self.app._draw_water_icon(canvas, sx, sy, scale, 21, 302, label=True))
        self.app._draw_icon_image(canvas, sx, sy, scale, "notif ungu.png", 15, 360, 50, 50, fallback=lambda: self.app._draw_notif_icon(canvas, sx, sy, scale, 17, 367))
        self._sidebar_hitbox(canvas, sx, sy, 206, 284, "home-nav")
        self._sidebar_hitbox(canvas, sx, sy, 284, 352, "water-nav")
        self._sidebar_hitbox(canvas, sx, sy, 352, 430, "notif-nav")
        
        # --- MENGGAMBAR HEADER ---
        rect(90, 20, 845, 600, 45, "#ffffff", shadow=True)
        self.app._draw_icon_image(canvas, sx, sy, scale, "notif ungu.png", 116, 37, 58, 58, fallback=lambda: self.app._draw_water_icon(canvas, sx, sy, scale, 120, 39, label=True, color=PRIMARY))
        text(192, 43, "Notifikasi", 24, "bold")        
        line(150, 130, 850, 130, PRIMARY, 1)

        visible_count = 5
        total_count = len(self.current_notifs)
        visible_notifs = self.current_notifs[self.scroll_index : self.scroll_index + visible_count]
        
        y = 135
        if not self.current_notifs:
            canvas.create_text(192, 75, text="Belum ada notifikasi", font=("Segoe UI", 12), anchor="nw")
            
        for row in visible_notifs:
            notif_type, title, desc, timestamp_str = row
            dt = self.app.db._parse_datetime(timestamp_str)
            hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
            waktu_format = f"{hari[dt.weekday()]}, {dt.strftime('%H.%M')}\n{dt.day:02d} {dt.strftime('%b')} {dt.year}"

            # Garis bawah / kotak pemisah antar notifikasi
            line(130, y + 80, 880, y + 80, "#E5D9F2", 1)
            
            icon_name = "ph merah.png" if notif_type == "danger" else "ph hijau.png"
            self.app._draw_icon_image(canvas, sx, sy, scale, icon_name, 140, y + 15, 40, 40)
            
            text(200, y + 10, title, 16, "bold")
            text(200, y + 40, desc, 12, fill="#646464")
            
            # Waktu diposisikan di sisi kanan
            text(860, y + 15, waktu_format, 10, anchor="ne", justify="right")
            
            y += 90
        if total_count > visible_count:
            track_x = 940
            track_y1 = 135
            track_y2 = 590
            track_h = track_y2 - track_y1

            rect(track_x, track_y1, 6, track_h, 3, "#f4f4f4", tags="scroll-track")
            thumb_h = max(40, track_h * (visible_count / total_count))
            scroll_ratio = self.scroll_index / (total_count - visible_count)
            thumb_y = track_y1 + scroll_ratio * (track_h - thumb_h)
            
            rect(track_x - 1, thumb_y, 8, thumb_h, 4, "#ffffff", PRIMARY, 2, tags="scroll-thumb")
            
    def _sidebar_hitbox(self, canvas, sx, sy, y1, y2, tag):
        canvas.create_rectangle(sx(0), sy(y1), sx(78), sy(y2), fill="", outline="", tags=tag)