import json
import os
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Script per aggiornare automaticamente seed_data.json.
# Obiettivo:
# - aprire i locator ufficiali delle catene
# - intercettare JSON/API/caricamenti pagina
# - estrarre record negozi con brand, indirizzo, provincia, cap
# - NON bloccare tutto se un brand fallisce
#
# Nota importante:
# alcuni siti cambiano spesso struttura o bloccano scraping automatico.
# Se un brand restituisce pochi risultati, lo script continua comunque
# e ti segnala il problema nei log.

BASE_DIR = Path(__file__).resolve().parents[1]
OUT_PATH = BASE_DIR / "seed_data.json"
MANUAL_PATH = BASE_DIR / "manual_seed.json"

TIMEOUT_MS = int(os.environ.get("SCRAPER_TIMEOUT_MS", "45000"))
HEADLESS = os.environ.get("HEADLESS", "true").lower() != "false"

PROVINCES = {
    "AG": "Agrigento", "AL": "Alessandria", "AN": "Ancona", "AO": "Aosta", "AR": "Arezzo",
    "AP": "Ascoli Piceno", "AT": "Asti", "AV": "Avellino", "BA": "Bari", "BT": "Barletta-Andria-Trani",
    "BL": "Belluno", "BN": "Benevento", "BG": "Bergamo", "BI": "Biella", "BO": "Bologna",
    "BZ": "Bolzano", "BS": "Brescia", "BR": "Brindisi", "CA": "Cagliari", "CL": "Caltanissetta",
    "CB": "Campobasso", "CI": "Carbonia-Iglesias", "CE": "Caserta", "CT": "Catania", "CZ": "Catanzaro",
    "CH": "Chieti", "CO": "Como", "CS": "Cosenza", "CR": "Cremona", "KR": "Crotone",
    "CN": "Cuneo", "EN": "Enna", "FM": "Fermo", "FE": "Ferrara", "FI": "Firenze",
    "FG": "Foggia", "FC": "Forlì-Cesena", "FR": "Frosinone", "GE": "Genova", "GO": "Gorizia",
    "GR": "Grosseto", "IM": "Imperia", "IS": "Isernia", "SP": "La Spezia", "AQ": "L'Aquila",
    "LT": "Latina", "LE": "Lecce", "LC": "Lecco", "LI": "Livorno", "LO": "Lodi",
    "LU": "Lucca", "MC": "Macerata", "MN": "Mantova", "MS": "Massa-Carrara", "MT": "Matera",
    "ME": "Messina", "MI": "Milano", "MO": "Modena", "MB": "Monza e Brianza", "NA": "Napoli",
    "NO": "Novara", "NU": "Nuoro", "OR": "Oristano", "PD": "Padova", "PA": "Palermo",
    "PR": "Parma", "PV": "Pavia", "PG": "Perugia", "PU": "Pesaro e Urbino", "PE": "Pescara",
    "PC": "Piacenza", "PI": "Pisa", "PT": "Pistoia", "PN": "Pordenone", "PZ": "Potenza",
    "PO": "Prato", "RG": "Ragusa", "RA": "Ravenna", "RC": "Reggio Calabria", "RE": "Reggio Emilia",
    "RI": "Rieti", "RN": "Rimini", "RM": "Roma", "RO": "Rovigo", "SA": "Salerno",
    "SS": "Sassari", "SV": "Savona", "SI": "Siena", "SR": "Siracusa", "SO": "Sondrio",
    "SU": "Sud Sardegna", "TA": "Taranto", "TE": "Teramo", "TR": "Terni", "TO": "Torino",
    "TP": "Trapani", "TN": "Trento", "TV": "Treviso", "TS": "Trieste", "UD": "Udine",
    "VA": "Varese", "VE": "Venezia", "VB": "Verbano-Cusio-Ossola", "VC": "Vercelli",
    "VR": "Verona", "VV": "Vibo Valentia", "VI": "Vicenza", "VT": "Viterbo"
}

# Città/province usate per stimolare i locator con barra ricerca.
# Non serve che siano tutte: servono come "sonde" per far partire API e risultati.
SEARCH_PROBES = [
    "Torino", "Milano", "Bergamo", "Brescia", "Varese", "Como", "Pavia", "Monza", "Novara",
    "Alessandria", "Genova", "Imperia", "Savona", "La Spezia",
    "Verona", "Vicenza", "Padova", "Venezia", "Treviso", "Rovigo", "Belluno",
    "Bologna", "Modena", "Parma", "Reggio Emilia", "Piacenza", "Ferrara", "Ravenna", "Forlì", "Rimini",
    "Firenze", "Prato", "Pistoia", "Pisa", "Livorno", "Lucca", "Arezzo", "Siena", "Massa",
    "Roma", "Latina", "Frosinone", "Viterbo", "Rieti",
    "Napoli", "Caserta", "Salerno", "Bari", "Lecce", "Taranto", "Palermo", "Catania", "Cagliari"
]

BRANDS = {
    "Bennet": "https://www.bennet.com/storefinder",
    "Basko": "https://www.basko.it/supermercati",
    "Coop": "https://www.coop.it/negozi",
    "Conad": "https://www.conad.it/negozi-e-volantini",
    "Esselunga": "https://www.esselunga.it/statics/geocms/store_locator/",
    "Eurospin": "https://www.eurospin.it/punti-vendita/",
    "Lidl": "https://www.lidl.it/c/punti-vendita-e-orari/s10019838",
    "MD": "https://www.mdspa.it/punti-vendita",
    "Tigros": "https://www.tigros.it/negozi",
    "Carrefour": "https://www.carrefour.it/punti-vendita"
}

ADDRESS_KEYS = {
    "address", "indirizzo", "indirizzoCompleto", "fullAddress", "formattedAddress",
    "streetAddress", "address1", "addressLine1", "line1", "via", "street", "locationAddress"
}
NAME_KEYS = {"name", "nome", "title", "storeName", "store_name", "label", "denomination", "ragioneSociale"}
ZIP_KEYS = {"postalCode", "cap", "zip", "zipcode", "postCode"}
PROV_KEYS = {"province", "provincia", "provinceCode", "province_code", "siglaProvincia", "prov_sigla", "prov_acr", "county"}
CITY_KEYS = {"city", "comune", "locality", "town", "municipality"}

PROVINCE_RE = re.compile(r"(?<![A-Z])(" + "|".join(sorted(PROVINCES.keys(), key=len, reverse=True)) + r")(?![A-Z])")
ZIP_RE = re.compile(r"\b([0-9]{5})\b")


def clean_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).replace("\xa0", " ")).strip()


def get_any(d, keys):
    for k in keys:
        if isinstance(d, dict) and k in d and d[k] not in (None, ""):
            return d[k]
    return None


def flatten_strings(obj):
    out = []
    if isinstance(obj, dict):
        for v in obj.values():
            out.extend(flatten_strings(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(flatten_strings(v))
    elif isinstance(obj, str):
        s = clean_text(obj)
        if s:
            out.append(s)
    return out


def infer_postal_code(*values):
    joined = " ".join(clean_text(v) for v in values if v)
    m = ZIP_RE.search(joined)
    return m.group(1) if m else ""


def infer_province_code(*values):
    joined = " ".join(clean_text(v).upper() for v in values if v)
    m = PROVINCE_RE.search(joined)
    if m:
        return m.group(1)
    return ""


def dict_to_store(brand, d):
    """Prova a trasformare un dizionario qualsiasi in record store."""
    if not isinstance(d, dict):
        return None

    raw_addr = get_any(d, ADDRESS_KEYS)
    raw_name = get_any(d, NAME_KEYS)
    raw_zip = get_any(d, ZIP_KEYS)
    raw_prov = get_any(d, PROV_KEYS)
    raw_city = get_any(d, CITY_KEYS)

    strings = flatten_strings(d)
    joined = " | ".join(strings)

    address = clean_text(raw_addr)
    if not address:
        # fallback: prendi la stringa più probabile come indirizzo
        candidates = [
            s for s in strings
            if (
                re.search(r"\b(via|viale|corso|piazza|strada|ss|s\.s\.|localit[aà]|largo)\b", s, re.I)
                or ZIP_RE.search(s)
            )
        ]
        if candidates:
            address = max(candidates, key=len)

    if not address:
        return None

    # Evita testi troppo generici/pagine legali.
    bad_words = ["privacy", "cookie", "newsletter", "lavora con noi", "termini", "condizioni"]
    if any(w in address.lower() for w in bad_words):
        return None

    name = clean_text(raw_name) or brand
    if len(name) > 90:
        name = brand

    postal_code = clean_text(raw_zip) or infer_postal_code(address, joined)
    province_code = clean_text(raw_prov).upper()
    if province_code not in PROVINCES:
        province_code = infer_province_code(address, joined)

    if province_code not in PROVINCES:
        return None

    province_name = PROVINCES[province_code]

    return {
        "brand": brand,
        "store_name": name,
        "province_code": province_code,
        "province_name": province_name,
        "address": address,
        "postal_code": postal_code,
        "source_url": BRANDS.get(brand, ""),
        "status": "active"
    }


def walk_json_for_stores(brand, obj, found):
    if isinstance(obj, dict):
        store = dict_to_store(brand, obj)
        if store:
            found.append(store)
        for v in obj.values():
            walk_json_for_stores(brand, v, found)
    elif isinstance(obj, list):
        for item in obj:
            walk_json_for_stores(brand, item, found)


def parse_json_text(brand, text):
    found = []
    if not text:
        return found
    text = text.strip()
    try:
        obj = json.loads(text)
        walk_json_for_stores(brand, obj, found)
    except Exception:
        return found
    return found


def extract_json_from_html(brand, html):
    found = []

    # JSON-LD e blob JSON nei tag script
    for m in re.finditer(r"<script[^>]*>(.*?)</script>", html, flags=re.I | re.S):
        body = m.group(1).strip()
        if not body:
            continue

        # JSON puro
        if body.startswith("{") or body.startswith("["):
            found.extend(parse_json_text(brand, body))

        # __NEXT_DATA__ / window.__data = {...}
        for jm in re.finditer(r"(\{.{200,}\})", body, flags=re.S):
            candidate = jm.group(1)
            if len(candidate) > 2_000_000:
                continue
            found.extend(parse_json_text(brand, candidate))

    return found


def static_fetch(brand, url):
    try:
        req = Request(url, headers={
            "User-Agent": "Mozilla/5.0 store-updater",
            "Accept": "text/html,application/xhtml+xml,application/json"
        })
        with urlopen(req, timeout=30) as resp:
            content_type = resp.headers.get("content-type", "")
            body = resp.read().decode("utf-8", errors="ignore")
            if "json" in content_type:
                return parse_json_text(brand, body)
            return extract_json_from_html(brand, body)
    except (HTTPError, URLError, TimeoutError, Exception) as e:
        print(f"[{brand}] static fetch non riuscito: {e}")
        return []


def scrape_with_playwright(brand, url):
    found = []
    seen_responses = set()

    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print(f"[{brand}] Playwright non disponibile: {e}")
        return found

    def handle_response(response):
        try:
            rurl = response.url
            if rurl in seen_responses:
                return
            seen_responses.add(rurl)

            ctype = response.headers.get("content-type", "")
            if "json" not in ctype and not any(x in rurl.lower() for x in ["store", "stores", "negoz", "punti", "locator", "api"]):
                return

            txt = response.text()
            if not txt or len(txt) > 8_000_000:
                return

            batch = parse_json_text(brand, txt)
            if batch:
                print(f"[{brand}] +{len(batch)} da risposta: {rurl[:120]}")
                found.extend(batch)
        except Exception:
            pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(
            locale="it-IT",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
            viewport={"width": 1440, "height": 1200}
        )
        page = context.new_page()
        page.on("response", handle_response)

        try:
            print(f"[{brand}] apro {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
        except Exception as e:
            print(f"[{brand}] goto fallito ma continuo: {e}")

        # Accetta cookie se presenti
        for selector in [
            "button:has-text('Accetta')",
            "button:has-text('Accetto')",
            "button:has-text('OK')",
            "button:has-text('Consenti')",
            "#onetrust-accept-btn-handler"
        ]:
            try:
                page.locator(selector).first.click(timeout=2000)
                time.sleep(1)
                break
            except Exception:
                pass

        # Scroll per far caricare liste lazy
        for _ in range(5):
            try:
                page.mouse.wheel(0, 2500)
                time.sleep(1)
            except Exception:
                pass

        # Estrai JSON presente nel DOM
        try:
            html = page.content()
            found.extend(extract_json_from_html(brand, html))
        except Exception:
            pass

        # Prova a usare la prima barra ricerca visibile.
        # Questo serve per locator che caricano risultati solo dopo una città.
        try:
            inputs = page.locator("input[type='search'], input[type='text'], input:not([type])")
            count = min(inputs.count(), 3)
            for i in range(count):
                inp = inputs.nth(i)
                if not inp.is_visible(timeout=1000):
                    continue
                for probe in SEARCH_PROBES:
                    try:
                        inp.fill(probe, timeout=3000)
                        inp.press("Enter", timeout=3000)
                        time.sleep(2)
                        try:
                            page.keyboard.press("Enter")
                        except Exception:
                            pass
                        time.sleep(2)
                        for _ in range(2):
                            page.mouse.wheel(0, 1500)
                            time.sleep(0.5)
                    except Exception:
                        continue
                break
        except Exception as e:
            print(f"[{brand}] ricerca automatica saltata: {e}")

        try:
            html = page.content()
            found.extend(extract_json_from_html(brand, html))
        except Exception:
            pass

        context.close()
        browser.close()

    return found


def normalize_manual_row(row):
    """Accetta sia il vecchio formato italiano sia il nuovo formato seed_data."""
    brand = row.get("brand") or row.get("azienda") or row.get("nome")
    address = row.get("address") or row.get("indirizzo") or row.get("indirizzo_completo")
    province_code = (row.get("province_code") or row.get("provincia") or "").upper().strip()
    province_name = row.get("province_name") or row.get("comune") or ""

    if province_code not in PROVINCES:
        province_code = infer_province_code(address, province_code, province_name)

    if province_code not in PROVINCES:
        return None

    postal_code = row.get("postal_code") or infer_postal_code(address)
    return {
        "brand": clean_text(brand),
        "store_name": clean_text(row.get("store_name") or row.get("nome") or brand),
        "province_code": province_code,
        "province_name": PROVINCES[province_code],
        "address": clean_text(address),
        "postal_code": clean_text(postal_code),
        "source_url": clean_text(row.get("source_url") or BRANDS.get(clean_text(brand), "")),
        "status": clean_text(row.get("status") or "active")
    }


def load_manual_seed():
    if not MANUAL_PATH.exists():
        return []
    try:
        data = json.loads(MANUAL_PATH.read_text(encoding="utf-8"))
        rows = []
        for row in data:
            fixed = normalize_manual_row(row)
            if fixed:
                rows.append(fixed)
        print(f"[manual_seed] caricati {len(rows)} record")
        return rows
    except Exception as e:
        print(f"[manual_seed] errore lettura: {e}")
        return []


def dedupe(rows):
    out = {}
    for r in rows:
        if not r:
            continue
        brand = clean_text(r.get("brand"))
        address = clean_text(r.get("address"))
        province_code = clean_text(r.get("province_code")).upper()
        if not brand or not address or province_code not in PROVINCES:
            continue

        r["brand"] = brand
        r["store_name"] = clean_text(r.get("store_name") or brand)
        r["province_code"] = province_code
        r["province_name"] = PROVINCES[province_code]
        r["address"] = address
        r["postal_code"] = clean_text(r.get("postal_code") or infer_postal_code(address))
        r["source_url"] = clean_text(r.get("source_url") or BRANDS.get(brand, ""))
        r["status"] = clean_text(r.get("status") or "active")

        key = (
            r["brand"].lower(),
            re.sub(r"[^a-z0-9]", "", r["address"].lower()),
            r["province_code"]
        )
        out[key] = r

    return sorted(out.values(), key=lambda x: (x["brand"], x["province_code"], x["address"]))


def main():
    all_rows = []

    wanted = os.environ.get("ONLY_BRANDS", "").strip()
    if wanted:
        brand_items = [(b, BRANDS[b]) for b in BRANDS if b.lower() in {x.strip().lower() for x in wanted.split(",")}]
    else:
        brand_items = list(BRANDS.items())

    for brand, url in brand_items:
        print("=" * 80)
        print(f"Brand: {brand}")

        rows = []
        rows.extend(static_fetch(brand, url))
        rows.extend(scrape_with_playwright(brand, url))

        rows = dedupe(rows)
        print(f"[{brand}] totale estratto: {len(rows)}")

        if len(rows) == 0:
            print(f"[{brand}] ATTENZIONE: nessun punto vendita estratto. Il sito potrebbe bloccare lo scraping o richiedere adapter dedicato.")

        all_rows.extend(rows)

    all_rows.extend(load_manual_seed())
    final_rows = dedupe(all_rows)

    OUT_PATH.write_text(
        json.dumps(final_rows, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("=" * 80)
    print(f"Creato {OUT_PATH}")
    print(f"Totale record: {len(final_rows)}")
    by_brand = {}
    for r in final_rows:
        by_brand[r["brand"]] = by_brand.get(r["brand"], 0) + 1
    print(json.dumps(by_brand, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
