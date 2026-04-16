import os
from pathlib import Path
from flask import Flask, jsonify, render_template
import psycopg

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, template_folder="templates")
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL non impostata")
    return psycopg.connect(DATABASE_URL)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
def health():
    return {"ok": True}

@app.route("/api/brands")
def brands():
    with get_conn() as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute("SELECT brand, COUNT(*) AS total FROM stores WHERE is_active = TRUE GROUP BY brand ORDER BY brand")
            rows = cur.fetchall()
    return jsonify(rows)

@app.route("/api/brand/<brand>/province-summary")
def province_summary(brand):
    with get_conn() as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                '''
                SELECT province_code, province_name, COUNT(*) AS count
                FROM stores
                WHERE is_active = TRUE AND brand = %s
                GROUP BY province_code, province_name
                ORDER BY count DESC, province_name ASC
                ''',
                (brand,)
            )
            rows = cur.fetchall()
    return jsonify(rows)

@app.route("/api/brand/<brand>/stores")
def stores(brand):
    with get_conn() as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                '''
                SELECT brand, store_name, province_code, province_name, address, postal_code, source_url, status
                FROM stores
                WHERE is_active = TRUE AND brand = %s
                ORDER BY province_name ASC, store_name ASC
                ''',
                (brand,)
            )
            rows = cur.fetchall()
    return jsonify(rows)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
