# InotekAI APK Desktop

Aplikasi desktop Python untuk login InotekAI, dashboard monitoring air, dan simulasi autofeeder.

## Stack

- Front-end: Python Tkinter
- Back-end: Python, siap dihubungkan ke library sensor dan GPIO
- Database: SQLite
- IDE: VS Code atau Thonny

## Cara menjalankan

```bash
pip install -r requirements.txt
python login.py
```

Database SQLite otomatis dibuat di file `inotekai.db` saat aplikasi pertama kali dijalankan. User awal yang otomatis tersedia:

- `12345`

## SQLite

Secara default aplikasi menyimpan database di folder proyek:

```text
inotekai.db
```

Jika ingin memakai lokasi file database lain, set environment variable `DATABASE_PATH`.

Contoh Windows:

```bash
set DATABASE_PATH=E:\data\inotekai.db
python login.py
```

File `schema.sql` juga sudah disiapkan untuk SQLite jika ingin membuat database secara manual.

## Sensor dan GPIO

Bagian sensor ada di `SensorService.read_water_quality()`.
Bagian autofeeder GPIO ada di `GpioService.dispense_feed()`.

Saat dijalankan di laptop/Windows, GPIO otomatis masuk mode demo.
