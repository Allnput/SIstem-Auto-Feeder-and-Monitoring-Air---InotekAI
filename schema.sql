CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    credential_code VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS water_readings (
    id SERIAL PRIMARY KEY,
    temperature NUMERIC(5, 2) NOT NULL,
    ph NUMERIC(4, 2) NOT NULL,
    water_level VARCHAR(50),
    status_label VARCHAR(30) NOT NULL,
    status_color VARCHAR(20) NOT NULL,
    sensor_temp_status VARCHAR(30) NOT NULL DEFAULT 'active',
    sensor_ph_status VARCHAR(30) NOT NULL DEFAULT 'active',
    feed_percentage INTEGER,
    last_synced TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feed_schedules (
    id SERIAL PRIMARY KEY,
    time_label VARCHAR(5) NOT NULL,
    detail TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    is_executed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feed_history (
    id SERIAL PRIMARY KEY,
    action_type VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL,
    message TEXT NOT NULL,
    feed_percentage INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO users (name, credential_code)
VALUES
    ('Chyntya', '12345')
ON CONFLICT (credential_code) DO NOTHING;
