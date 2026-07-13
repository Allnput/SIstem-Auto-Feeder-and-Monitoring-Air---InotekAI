from dataclasses import dataclass
from datetime import datetime

from serial_reader import get_ph_value

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None

@dataclass
class SensorReading:
    ph: float
    last_synced: object = None
    sensor_ph_status: str = "active"


# def read_ph_sensor():
#     return read_ph_sensor(7.5)

#READ SENSORNYA DISINI
class SensorService:
    
    def read_water_quality(self):
        try:
            
            ph_value = get_ph_value() #DATA ASLI DARI ARDUINO (lihat serial_reader.py)

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