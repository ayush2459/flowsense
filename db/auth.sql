-- FlowSense authentication schema
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(320) NOT NULL UNIQUE,
    password_hash TEXT,
    auth_provider VARCHAR(20) NOT NULL DEFAULT 'local',
    google_subject_id VARCHAR(255) UNIQUE,
    profile_image TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT users_auth_provider_check CHECK (auth_provider IN ('local', 'google')),
    CONSTRAINT users_local_password_check CHECK ((auth_provider = 'local' AND password_hash IS NOT NULL) OR (auth_provider = 'google'))
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_google_subject ON users(google_subject_id);