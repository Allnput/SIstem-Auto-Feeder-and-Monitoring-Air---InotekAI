from datetime import datetime


def getWaterStatus(temp, ph):
    try:
        temp_value = float(temp)
        ph_value = float(ph)
    except (TypeError, ValueError):
        return {"label": "Risiko", "color": "#E74C3C"}

    if 26 <= temp_value <= 30 and 6.5 <= ph_value <= 8.5:
        return {"label": "Optimal", "color": "#2ECC71"}
    if 20 <= temp_value <= 35 and 6.0 <= ph_value <= 9.0:
        return {"label": "Toleransi", "color": "#F1C40F"}
    return {"label": "Risiko", "color": "#E74C3C"}


def get_device_health(data, status="active"):
    inactive_statuses = {"error", "inactive", "tidak aktif", "offline"}
    if data is None or str(status).strip().lower() in inactive_statuses:
        return {"label": "Tidak Aktif", "color": "#95A5A6", "active": False}
    return {"label": "Aktif", "color": "#27AE60", "active": True}


def get_feed_level_label(feed_percentage):
    try:
        value = int(feed_percentage)
    except (TypeError, ValueError):
        value = 0

    value = max(0, min(100, value))
    if value >= 75:
        return "Aman"
    if value >= 50:
        return "Cukup"
    if value >= 25:
        return "Kurang"
    return "Kritis"


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


def get_today_schedule(feed_schedules, now=None):
    now = now or datetime.now()
    today_name = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"][now.weekday()]
    rows = []

    for schedule in feed_schedules:
        detail = schedule.get("detail", "")
        active = schedule.get("active", True)
        if not active or (detail and today_name not in detail):
            continue
        time_label = normalize_schedule_time(schedule.get("time", ""))
        try:
            hour, minute = [int(part) for part in time_label.split(":")[:2]]
            scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except (TypeError, ValueError):
            scheduled_time = now
        rows.append({**schedule, "time": time_label, "scheduled_time": scheduled_time})

    rows.sort(key=lambda item: item["scheduled_time"])
    next_marked = False
    for row in rows:
        if row.get("is_executed"):
            row["status"] = "Done"
            row["status_text"] = "Selesai"
            row["status_bg"] = "#E1F5EE"
            row["status_fg"] = "#2ECC71"
        elif not next_marked and row["scheduled_time"] >= now:
            row["status"] = "Next"
            row["status_text"] = "Menunggu"
            row["status_bg"] = "#E6F1FB"
            row["status_fg"] = "#1E63A7"
            next_marked = True
        else:
            row["status"] = "Upcoming"
            row["status_text"] = "Terjadwal"
            row["status_bg"] = "#D9D9D9"
            row["status_fg"] = "#000000"
    return rows
