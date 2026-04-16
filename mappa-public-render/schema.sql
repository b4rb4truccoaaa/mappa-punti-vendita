CREATE TABLE IF NOT EXISTS stores (
  id SERIAL PRIMARY KEY,
  brand TEXT NOT NULL,
  store_name TEXT NOT NULL,
  province_code TEXT NOT NULL,
  province_name TEXT NOT NULL,
  address TEXT,
  postal_code TEXT,
  source_url TEXT,
  status TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_store_identity
ON stores(brand, store_name, province_code, address);

CREATE INDEX IF NOT EXISTS idx_brand ON stores(brand);
CREATE INDEX IF NOT EXISTS idx_province ON stores(province_code);
