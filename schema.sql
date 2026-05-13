CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    credential_code TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS water_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    temperature REAL NOT NULL,
    ph REAL NOT NULL,
    water_level TEXT,
    status_label TEXT NOT NULL,
    status_color TEXT NOT NULL,
    sensor_temp_status TEXT NOT NULL DEFAULT 'active',
    sensor_ph_status TEXT NOT NULL DEFAULT 'active',
    feed_percentage INTEGER,
    last_synced TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feed_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time_label TEXT NOT NULL,
    detail TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    is_executed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feed_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    feed_percentage INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO users (name, credential_code)
VALUES
    ('Chyntya', '12345');
