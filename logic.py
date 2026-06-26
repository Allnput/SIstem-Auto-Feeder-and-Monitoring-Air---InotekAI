from datetime import datetime
from pathlib import Path
from PIL import ImageTk
from mlflow import Image

ICON_DIR = Path(__file__).resolve().parent / "icon"

PRIMARY = "#9157f5"
FIGMA_WIDTH = 960
FIGMA_HEIGHT = 640
PH_MIN = 0
PH_MAX = 15
PH_TICKS = [0, 3, 6, 9, 12, 15]
FOUR_HOUR_LABELS = [f"{hour:02d}.00" for hour in range(0, 24, 4)]
CHART_AXIS_LABELS = FOUR_HOUR_LABELS + ["00.59"]


def ph_status(ph):
    try:
        value = float(ph)
    except (TypeError, ValueError):
        return {"label": "Bahaya", "color": "#E74C3C"}
    if 1 <= value < 4:
        return {"label": "Sangat Asam", "color": ph_color(value)}
    if 4 <= value < 6:
        return {"label": "Asam", "color": ph_color(value)}
    if 6 <= value < 7:
        return {"label": "Hampir Netral", "color": ph_color(value)}
    if 7 <= value <= 8:
        return {"label": "Netral", "color": ph_color(value)}
    if 8 < value <= 9:
        return {"label": "Basa Ringan", "color": ph_color(value)}
    if 9 < value < 13:
        return {"label": "Basa Sedang", "color": ph_color(value)}
    if 13 <= value <= 14:
        return {"label": "Sangat Basa", "color": ph_color(value)}
    return {"label": "Bahaya", "color": "#E74C3C"}


def ph_color(ph):
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

def getpHStatus(ph):
    try:
        p = ph_status(ph)
        return {
            "ph": {
                "label": p["ph_status_label"],
                "color": p["ph_status_color"]
            }
        }
    except Exception:
        return {
            "ph": {
                "label": "Error Sensor",
                "color": "#E74C3C"
            }
        }

def get_device_health(data, status="active"):
    inactive_statuses = {"error", "inactive", "tidak aktif", "offline"}
    if data is None or str(status).strip().lower() in inactive_statuses:
        return {"label": "Tidak Aktif", "color": "#95A5A6", "active": False}
    return {"label": "Aktif", "color": "#27AE60", "active": True}

def format_last_synced(last_synced):
    if isinstance(last_synced, datetime):
        return last_synced.strftime("%H:%M")
    if not last_synced:
        return datetime.now().strftime("%H:%M")

    text = str(last_synced).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%H:%M:%S", "%H.%M"):
        try:
            return datetime.strptime(text[:19] if "%Y" in fmt else text, fmt).strftime("%H:%M")
        except ValueError:
            pass
    return text[:5].replace(".", ":")

def normalize_schedule_time(time_text):
    text = str(time_text).strip().replace(".", ":")
    parts = text.split(":")
    if len(parts) < 2:
        return text
    try:
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    except ValueError:
        return text

def format_today(last_synced):
    current = last_synced if isinstance(last_synced, datetime) else datetime.now()
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    months = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ]
    return f"{days[current.weekday()]}, {current.day} {months[current.month - 1]} {current.year}"

def four_hour_average(rows, metric):
    buckets = [[] for _ in FOUR_HOUR_LABELS]
    today_date = datetime.now().date()  # Kunci 1: Filter tanggal hari ini
    
    for row in rows:
        value, synced_at = row_value_time(row, metric)
        if value is None or not isinstance(synced_at, datetime):
            continue
            
        # Cegah kebocoran data: Hanya hitung data milik hari ini
        if synced_at.date() != today_date:
            continue
            
        bucket_index = synced_at.hour // 4
        if 0 <= bucket_index < len(buckets):
            buckets[bucket_index].append(value)
            
    return [sum(bucket) / len(bucket) if bucket else None for bucket in buckets]
    
def average_ph(rows):
    values = []
    today_date = datetime.now().date()
    
    for row in rows:
        ph, synced_at = row_value_time(row, "ph")
        if ph is not None and isinstance(synced_at, datetime):
            if synced_at.date() == today_date:
                values.append(ph)
                
    return sum(values) / len(values) if values else None

def row_value_time(row, metric):
    try:
        if isinstance(row, dict):
            value = row.get(metric)
            synced_at = row.get("last_synced")
        else:
            value = row[0]
        synced_at = row[3]
        
        if isinstance(synced_at, str):
            # Memperbaiki anomali spasi pada generator data dummy ('2026-04-0106:39:33')
            if len(synced_at) == 18 and synced_at[10] != ' ':
                synced_at = synced_at[:10] + ' ' + synced_at[10:]
            synced_at = datetime.strptime(synced_at, "%Y-%m-%d %H:%M:%S")
            
        return float(value), synced_at
    except (KeyError, IndexError, TypeError, ValueError):
        return None, None

def dot_color(value):
    if isinstance(value, (int, float)) and value != value:
        return "#E74C3C"
    return ph_color(value)

def mix_color(start_color, end_color, ratio):
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

def bucket_range_label(index):
    start_hour = index * 4
    if index == len(FOUR_HOUR_LABELS) - 1:
        return f"{start_hour:02d}.00-00.59"
    end_hour = start_hour + 3
    return f"{start_hour:02d}.00-{'end_hour:02d'}.59"

def format_number(value):
    if value is None:
        return "-"
    text = f"{float(value):.1f}"
    return text.rstrip("0").rstrip(".")


#dashboard

def draw_ph_bar(canvas, sx, sy, scale):
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
    
def draw_gradient_fill(canvas, sx, sy, point_items, bottom, color_for_value):
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
            color = mix_color(color_for_value(start_value), color_for_value(end_value), (ratio_a + ratio_b) / 2)
            canvas.create_polygon(
                sx(x1), sy(bottom),
                sx(x1), sy(y1),
                sx(x2), sy(y2),
                sx(x2), sy(bottom),
                fill=color,
                outline="",
                stipple="gray50",
            )
            
            
#chart
def draw_chart_today(self, canvas, sx, sy, fs, line, text, accent, fill, values):
    left, top, right, bottom = 140, 365, 885, 590
    height=31 
    times = CHART_AXIS_LABELS
    chart_width = right - left
    chart_height = bottom - top
    self._selected_bucket_index = None
    def y_for(value):
        bounded = max(PH_MIN, min(PH_MAX, float(value)))
        return bottom - ((bounded - PH_MIN) / (PH_MAX - PH_MIN)) * chart_height

    def x_for_time(dt):
        # Mengubah jam aktual menjadi total detik (0 - 86400 dalam sehari)
        seconds = dt.hour * 3600 + dt.minute * 60 + dt.second
        # Rasio terhadap total waktu 24 jam untuk menempatkan titik secara presisi
        ratio = seconds / 86400.0
        return left + ratio * chart_width

    # 1. Gambar Garis Grid Horizontal & Label Y (Tetap Sama)
    for value in PH_TICKS:
        y = y_for(value)
        line(left, y, right, y, "#dddddd", 1, dash=(2, 2))
        text(left - 25, y - 15, str(value), 10, fill="#a0a0a0")
                
    line(left, bottom, right, bottom, "#aaaaaa", 1)
    line(left, top, left, bottom, "#aaaaaa", 1)
    line(left + 8, top + 0, left, top, "#aaaaaa", 1)
    line(right - 8, bottom - 5, right, bottom, "#aaaaaa", 1)
        
    for boundary in (6, 8):
        line(left, y_for(boundary), right, y_for(boundary), "#000000", 1, dash=(4, 2))

    # 2. Logika Tooltip yang di-update dengan waktu aktual
    def show_tooltip(selected_index):
        if selected_index is None or selected_index < 0 or selected_index >= len(values):
            return
            
        data = values[selected_index]
        if data is None: return
        
        val = data["value"]
        dt = data["time"]
            
        self._selected_bucket_index = selected_index
        canvas.delete("chart-tooltip")
        
        # Hitung posisi dot tooltip
        cx = x_for_time(dt)
        cy = y_for(val)
            
        tooltip_x = min(right - 140, max(left + 8, cx - 55))
        tooltip_y = max(top + 12, cy - 64)
                
        self._dashboard_round_rect(canvas, sx(tooltip_x), sy(tooltip_y), sx(tooltip_x + 132), sy(tooltip_y + 48), 4, "#000000", "#000000", 0, "chart-tooltip")
        canvas.create_oval(sx(tooltip_x + 12), sy(tooltip_y + 17), sx(tooltip_x + 24), sy(tooltip_y + 29), fill=ph_color(val), outline=ph_color(val), tags="chart-tooltip")
        
        value_label = "pH air"
        time_str = dt.strftime("%H:%M") # Format Jam:Menit untuk Tooltip
        
        text(tooltip_x + 30, tooltip_y + 8, f"Pukul {time_str}", 8, fill="#ffffff", tags="chart-tooltip")
        text(tooltip_x + 30, tooltip_y + 24, f"{value_label}: {format_number(val)}", 10, "bold", "#ffffff", tags="chart-tooltip")

    # 3. Proses Pengumpulan Titik Koordinat dari Data Aktual
    points = []
    point_items = []
    for index, data in enumerate(values):
        if data is None: continue
        val = data["value"]
        dt = data["time"]
                
        x = x_for_time(dt)
        y = y_for(val)
                
        points.extend([sx(x), sy(y)])
        point_items.append((index, val, x, y))

            # 4. Gambar Area Gradient
    if points:
        
        draw_gradient_fill(canvas, sx, sy, point_items, bottom, ph_color)

            # 5. Gambar Garis Poligon Grafik
    if len(points) == 4:
        canvas.create_line(points, fill=accent, width=max(2, int(2 * height / FIGMA_HEIGHT)), smooth=False)
    elif len(points) > 4:
        canvas.create_line(points, fill=accent, width=max(2, int(2 * height / FIGMA_HEIGHT)), smooth=True)

            # 6. Gambar Dot pada Setiap Pembacaan
    for index, val, x, y in point_items:
        r = 4
        tag = f"chart-point-{index}"
        canvas.create_oval(sx(x) - r, sy(y) - r, sx(x) + r, sy(y) + r, fill=ph_color(val), outline="#ffffff", tags=tag)
        canvas.tag_bind(tag, "<Button-1>", lambda _event, selected=index: show_tooltip(selected))

    # 7. Distribusikan Label Teks Sumbu X Secara Merata (Tetap 4-jaman)
    for index, label in enumerate(times):
        denominator = max(1, len(times) - 1)
        # Label di bagian bawah tidak bergantung pada data aktual, diposisikan rata sepanjang sumbu X
        label_x = left + (index / denominator) * chart_width
        text(label_x, bottom + 8, label, 7, fill="#a0a0a0", anchor="n")

    # 8. Render kembali tooltip yang sedang aktif (jika window di-resize dll)
    selected_index = self._selected_bucket_index
    if selected_index is not None:
        show_tooltip(selected_index)