BEGIN;

CREATE TABLE IF NOT EXISTS flowsense_settings (
    id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    organization_name VARCHAR(160) NOT NULL DEFAULT 'FlowSense',
    organization_code VARCHAR(80) NOT NULL DEFAULT 'FLOWSENSE',
    timezone VARCHAR(80) NOT NULL DEFAULT 'Asia/Kolkata',
    locale VARCHAR(30) NOT NULL DEFAULT 'en-IN',
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    date_format VARCHAR(30) NOT NULL DEFAULT 'DD/MM/YYYY',
    theme VARCHAR(20) NOT NULL DEFAULT 'dark',
    contact_email VARCHAR(255),
    contact_phone VARCHAR(40),
    monitoring JSONB NOT NULL DEFAULT '{}'::jsonb,
    notifications JSONB NOT NULL DEFAULT '{}'::jsonb,
    integrations JSONB NOT NULL DEFAULT '{}'::jsonb,
    system JSONB NOT NULL DEFAULT '{}'::jsonb,
    security JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_by UUID,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    theme VARCHAR(20),
    timezone VARCHAR(80),
    locale VARCHAR(30),
    preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    notifications JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(40) NOT NULL DEFAULT 'admin';
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(40);
ALTER TABLE users ADD COLUMN IF NOT EXISTS job_title VARCHAR(120);
ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(120);

INSERT INTO flowsense_settings (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

COMMIT;
