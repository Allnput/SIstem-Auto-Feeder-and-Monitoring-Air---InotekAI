=======
# InotekAI APK Desktop

Aplikasi desktop Python untuk login InotekAI, dashboard monitoring air, dan simulasi autofeeder.

## Stack

- Front-end: Python Tkinter
- Back-end: Python, siap dihubungkan ke library sensor dan GPIO
- Database: PostgreSQL
- IDE: VS Code atau Thonny

## Cara menjalankan

```bash
pip install -r requirements.txt
python login.py
```

Jika PostgreSQL belum tersedia, aplikasi otomatis memakai data demo:

- `12345`
- `67890`
- `inotek`

## PostgreSQL

1. Buat database PostgreSQL.
2. Jalankan isi `schema.sql`.
3. Set environment variable `DATABASE_URL`.

Contoh:

```bash
set DATABASE_URL=postgresql://postgres:password@localhost:5432/inotekai
python login.py
```

## Sensor dan GPIO

Bagian sensor ada di `SensorService.read_water_quality()`.
Bagian autofeeder GPIO ada di `GpioService.dispense_feed()`.

Saat dijalankan di laptop/Windows, GPIO otomatis masuk mode demo.
>>>>>>> TEST
