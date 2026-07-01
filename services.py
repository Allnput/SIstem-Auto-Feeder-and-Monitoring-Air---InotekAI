import threading
from dataclasses import dataclass
from datetime import datetime
from urllib import request

from matplotlib.pylab import uniform

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

@dataclass
class SensorReading:
    ph: float
    last_synced: object = None
    sensor_ph_status: str = "active"


def read_ph_sensor():
    return round(uniform(6.0, 8.0), 2)

#READ SENSORNYA DISINI
class SensorService:
    
    def read_water_quality(self):
        try:
            ph_value = read_ph_sensor()

            return SensorReading(
                ph=ph_value,
                last_synced=datetime.now(),
                sensor_ph_status="active"
            )

        except Exception:
            return SensorReading(
                ph=0,
                last_synced=datetime.now(),
                sensor_ph_status="inactive"
            )