"""
serial_reader.py

File terpisah, khusus urusan komunikasi serial ke Arduino (inotekai.ino).
Tidak menyentuh services.py sama sekali — file ini hanya diimport dari sana.

Cara pakai di services.py:

    from serial_reader import get_ph_value

    ph_value = get_ph_value()   # ganti baris "ph_value = 7.5"

get_ph_value() akan:
- mengembalikan angka pH terbaru dari Arduino kalau datanya masih segar, atau
- melempar RuntimeError kalau belum ada data / koneksi putus / data basi
  (>STALE_AFTER detik) -> otomatis kena blok "except Exception" yang SUDAH
  ADA di services.py lama kamu, jadi status sensor otomatis jadi "inactive"
  tanpa perlu kode tambahan di sana.
"""

import re
import threading
import time
from datetime import datetime

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None


# =====================================================================
# KONFIGURASI — sesuaikan kalau perlu
# =====================================================================
SERIAL_PORT = None        # None = auto-detect. Atau isi manual, mis. "COM3" (Windows)
                           # atau "/dev/ttyUSB0" / "/dev/ttyACM0" (Linux/Raspberry Pi)
                           # atau "/dev/tty.usbmodemXXXX" (Mac)
SERIAL_BAUDRATE = 9600     # HARUS sama dengan Serial.begin(9600) di inotekai.ino
SERIAL_READ_TIMEOUT = 1.0  # detik, timeout tiap readline() di background thread
RECONNECT_INTERVAL = 3.0   # detik, jeda sebelum mencoba sambung ulang kalau putus
STALE_AFTER = 5.0          # detik, kalau tidak ada data baru selama ini -> dianggap basi

# Arduino ngirim baris seperti: "Ph: 7.23"
PH_PATTERN = re.compile(r"[-+]?\d*\.?\d+")


class _SerialPHReader:
    """Baca port serial terus-menerus di background thread (non-blocking untuk GUI)."""

    def __init__(self, port=SERIAL_PORT, baudrate=SERIAL_BAUDRATE, timeout=SERIAL_READ_TIMEOUT):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self._serial = None
        self._state_lock = threading.Lock()
        self._last_ph = None
        self._last_synced = None
        self._last_connect_attempt = 0.0
        self._stop_event = threading.Event()

        self._thread = None
        if serial is None:
            print("[serial_reader] pyserial belum terpasang. Jalankan: pip install pyserial")
            return

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------
    def get_ph_value(self):
        """Dipanggil dari services.py. Cepat, tidak pernah blocking."""
        with self._state_lock:
            ph_value = self._last_ph
            last_synced = self._last_synced

        if ph_value is None:
            raise RuntimeError("Belum ada data pH dari Arduino.")

        if (datetime.now() - last_synced).total_seconds() > STALE_AFTER:
            raise RuntimeError("Data pH dari Arduino sudah basi (koneksi mungkin putus).")

        return ph_value

    def close(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._close_serial()

    # ------------------------------------------------------------------
    # Background thread
    # ------------------------------------------------------------------
    def _run_loop(self):
        while not self._stop_event.is_set():
            if not self._ensure_connection():
                time.sleep(RECONNECT_INTERVAL)
                continue

            try:
                raw_line = self._serial.readline().decode("utf-8", errors="ignore").strip()
                ph_value = self._parse_ph(raw_line)

                if ph_value is not None:
                    with self._state_lock:
                        self._last_ph = ph_value
                        self._last_synced = datetime.now()

            except (OSError, serial.SerialException):
                self._close_serial()
                time.sleep(RECONNECT_INTERVAL)
            except Exception:
                time.sleep(0.5)

    def _parse_ph(self, line):
        if not line:
            return None
        match = PH_PATTERN.search(line)
        if not match:
            return None
        try:
            return float(match.group())
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # Koneksi serial
    # ------------------------------------------------------------------
    def _find_port(self):
        if list_ports is None:
            return None
        candidates = list(list_ports.comports())
        for p in candidates:
            desc = f"{p.description} {p.manufacturer or ''}".lower()
            if any(key in desc for key in ("arduino", "ch340", "usb-serial", "usb serial", "wch")):
                return p.device
        return candidates[0].device if candidates else None

    def _ensure_connection(self):
        if self._serial is not None and self._serial.is_open:
            return True

        now = time.time()
        if now - self._last_connect_attempt < RECONNECT_INTERVAL:
            return False
        self._last_connect_attempt = now

        target_port = self.port or self._find_port()
        if not target_port:
            return False

        try:
            self._serial = serial.Serial(target_port, self.baudrate, timeout=self.timeout)
            time.sleep(2)  # beri waktu board Arduino selesai reset setelah port dibuka
            self._serial.reset_input_buffer()
            self.port = target_port
            return True
        except Exception:
            self._serial = None
            return False

    def _close_serial(self):
        try:
            if self._serial is not None:
                self._serial.close()
        except Exception:
            pass
        self._serial = None


# Singleton module-level: thread cuma dibuat sekali walau diimport di banyak tempat.
_reader = _SerialPHReader()


def get_ph_value():
    """Ambil nilai pH terbaru dari Arduino. Raise RuntimeError kalau belum/tidak ada data."""
    return _reader.get_ph_value()


def close():
    """Panggil ini (opsional) saat aplikasi ditutup, untuk melepas port serial dengan rapi."""
    _reader.close()