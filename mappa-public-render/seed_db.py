import json
import os
from pathlib import Path
import psycopg

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"
SEED_PATH = BASE_DIR / "seed_data.json"

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL non impostata")

with psycopg.connect(DATABASE_URL) as conn:
    with conn.cursor() as cur:
        cur.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
        data = json.loads(SEED_PATH.read_text(encoding="utf-8"))

        for row in data:
            cur.execute(
                '''
                INSERT INTO stores (
                    brand, store_name, province_code, province_name, address,
                    postal_code, source_url, status, is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (brand, store_name, province_code, address)
                DO UPDATE SET
                    province_name = EXCLUDED.province_name,
                    postal_code = EXCLUDED.postal_code,
                    source_url = EXCLUDED.source_url,
                    status = EXCLUDED.status,
                    is_active = TRUE,
                    updated_at = NOW()
                ''',
                (
                    row["brand"], row["store_name"], row["province_code"], row["province_name"],
                    row["address"], row["postal_code"], row["source_url"], row["status"]
                )
            )

        cur.execute(
            '''
            UPDATE stores
            SET is_active = FALSE, updated_at = NOW()
            WHERE (brand, store_name, province_code, address) NOT IN (
                SELECT x.brand, x.store_name, x.province_code, x.address
                FROM json_to_recordset(%s::json) AS x(
                    brand text,
                    store_name text,
                    province_code text,
                    province_name text,
                    address text,
                    postal_code text,
                    source_url text,
                    status text
                )
            )
            ''',
            (json.dumps(data, ensure_ascii=False),)
        )
    conn.commit()

print(f"Seed completato. Record attivi: {len(data)}")
