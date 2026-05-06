import threading
from dataclasses import dataclass
from datetime import datetime
from urllib import request

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

@dataclass
class SensorReading:
    ph: float
    temperature: float
    water_level: str
    last_synced: object = None
    sensor_temp_status: str = "active"
    sensor_ph_status: str = "active"
    auto_feeder_status: str = "active"
    feed_percentage: int = 75


#READ SENSORNYA DISINI
class SensorService:
    def read_water_quality(self):
        return SensorReading(
            ph=7.2,
            temperature=28.4,
            water_level="Normal",
            last_synced=datetime.now(),
            sensor_temp_status="active",
            sensor_ph_status="active",
            auto_feeder_status="active",
            feed_percentage=75,
        )


class GpioService:
    FEEDER_PIN = 18

    def __init__(self):
        self.available = GPIO is not None
        if self.available:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.FEEDER_PIN, GPIO.OUT)

    def dispense_feed(self):
        if not self.available:
            return "Mode demo: perintah pakan berhasil disimulasikan."

        GPIO.output(self.FEEDER_PIN, GPIO.HIGH)
        threading.Timer(0.7, lambda: GPIO.output(self.FEEDER_PIN, GPIO.LOW)).start()
        return "Pakan ikan dikirim."


class IoTManualFeedClient:
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def triggerManualFeed(self):
        if not self.endpoint:
            return True

        payload = b'{"action":"manual_feed"}'
        api_request = request.Request(
            self.endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(api_request, timeout=5) as response:
            return 200 <= response.status < 300
