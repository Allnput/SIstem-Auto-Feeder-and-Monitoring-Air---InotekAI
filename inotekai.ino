// ============================================================
// Sensor pH - ESP32
// PERBAIKAN: ESP32 ADC 12-bit (rentang 0-4095), bukan 10-bit (0-1023)
// seperti Arduino Uno. Sebelumnya kode ini membagi dengan 1024.0
// (nilai untuk Uno) padahal analogRead() di ESP32 mengembalikan
// nilai 0-4095, sehingga hasil pH jadi salah (~21-22, dekat nilai
// "calibration" karena voltage yang terhitung mendekati 0).
// ============================================================

float calibration = 22.00;
const int analogInPin = A0;   // pastikan pin ini memang input ADC yang valid di ESP32 kamu

const float ADC_RESOLUTION = 4095.0;  // ESP32 = 12-bit ADC
const float ADC_VREF = 3.3;           // tegangan referensi ESP32

int buf[10], temp;
unsigned long avgValue;

void setup() {
  Serial.begin(9600);

  // Opsional tapi direkomendasikan: pastikan ADC bisa baca sampai 3.3V penuh.
  // Default attenuation ESP32 kadang cuma akurat sampai ~3.1V.
  analogSetAttenuation(ADC_11db);
}

void loop() {

  for (int i = 0; i < 10; i++) {
    buf[i] = analogRead(analogInPin);
    delay(30);
  }

  // Sort
  for (int i = 0; i < 9; i++) {
    for (int j = i + 1; j < 10; j++) {
      if (buf[i] > buf[j]) {
        temp = buf[i];
        buf[i] = buf[j];
        buf[j] = temp;
      }
    }
  }

  avgValue = 0;

  for (int i = 2; i < 8; i++)
    avgValue += buf[i];

  float adc = avgValue / 6.0;
  float voltage = adc * ADC_VREF / ADC_RESOLUTION;   // <-- FIX: 4095.0, bukan 1024.0
  float pH = -5.70 * voltage + calibration;

  // Debug: aktifkan baris di bawah kalau mau lihat nilai mentahnya
  // saat proses kalibrasi ulang.
  // Serial.print("adc="); Serial.print(adc);
  // Serial.print(" voltage="); Serial.println(voltage, 3);

  Serial.print("Ph: ");
  Serial.println(pH, 2);

  delay(1000);
}
