from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from pathlib import Path
import json
import re

OUTPUT_FILE = Path(__file__).resolve().parent.parent / "seed_data.json"

SOURCES = [
    {
        "brand": "Di Più",
        "url": "https://www.dipiuperlascuola.it/it/seopagemenulabel/punti-vendita/pm-13-21",
    },
    {
        "brand": "Basko",
        "url": "https://www.basko.it/supermercati",
    },
]

PROVINCE_NAMES = {
    "AL": "Alessandria",
    "AN": "Ancona",
    "AR": "Arezzo",
    "AT": "Asti",
    "BG": "Bergamo",
    "BI": "Biella",
    "BO": "Bologna",
    "BS": "Brescia",
    "CN": "Cuneo",
    "CO": "Como",
    "CR": "Cremona",
    "FE": "Ferrara",
    "FI": "Firenze",
    "FC": "Forlì-Cesena",
    "FR": "Frosinone",
    "GE": "Genova",
    "GO": "Gorizia",
    "IM": "Imperia",
    "LC": "Lecco",
    "LI": "Livorno",
    "LO": "Lodi",
    "MB": "Monza e Brianza",
    "MI": "Milano",
    "MN": "Mantova",
    "MO": "Modena",
    "MS": "Massa-Carrara",
    "NO": "Novara",
    "PD": "Padova",
    "PC": "Piacenza",
    "PG": "Perugia",
    "PI": "Pisa",
    "PN": "Pordenone",
    "PR": "Parma",
    "PT": "Pistoia",
    "PU": "Pesaro e Urbino",
    "PV": "Pavia",
    "RA": "Ravenna",
    "RE": "Reggio Emilia",
    "RM": "Roma",
    "RO": "Rovigo",
    "RN": "Rimini",
    "SI": "Siena",
    "SO": "Sondrio",
    "SP": "La Spezia",
    "SV": "Savona",
    "TE": "Teramo",
    "TO": "Torino",
    "TR": "Terni",
    "TS": "Trieste",
    "TV": "Treviso",
    "UD": "Udine",
    "VA": "Varese",
    "VC": "Vercelli",
    "VE": "Venezia",
    "VI": "Vicenza",
    "VR": "Verona",
    "VT": "Viterbo",
}

COMUNE_TO_PROVINCE = {
    "Pavia": "PV",
    "Bergamo": "BG",
    "Venezia": "VE",
    "Monza Brianza": "MB",
    "Bologna": "BO",
    "Roma": "RM",
    "Novara": "NO",
    "Vicenza": "VI",
    "Treviso": "TV",
    "Massa Carrara": "MS",
    "Pordenone": "PN",
    "Ravenna": "RA",
    "Verona": "VR",
    "Como": "CO",
    "Firenze": "FI",
    "Cuneo": "CN",
    "Brescia": "BS",
    "Milano": "MI",
    "Padova": "PD",
    "Varese": "VA",
    "Teramo": "TE",
    "Piacenza": "PC",
    "Pisa": "PI",
    "Ancona": "AN",
    "Modena": "MO",
    "Reggio Emilia": "RE",
    "Regg. Emilia": "RE",
    "Ferrara": "FE",
    "Udine": "UD",
    "Rimini": "RN",
    "Imperia": "IM",
    "Parma": "PR",
    "Forlì": "FC",
    "Forlì Cesena": "FC",
    "Forlì/Cesena": "FC",
    "Genova": "GE",
    "Gorizia": "GO",
    "Torino": "TO",
    "Mantova": "MN",
    "Lodi": "LO",
    "Belluno": "BL",
    "Arezzo": "AR",
    "Fermo": "FM",
    "Asti": "AT",
    "Siena": "SI",
    "Sondrio": "SO",
    "Vercelli": "VC",
    "Pesaro": "PU",
    "pesaro": "PU",
    "Pescara": "PE",
    "pistoia": "PT",
    "Pistoia": "PT",
    "Biella": "BI",
    "Prato": "PO",
    "Trieste": "TS",
    "Rovigo": "RO",
    "Livorno": "LI",
    "La Spezia": "SP",
    "Latina": "LT",
    "Viterbo": "VT",
    "Terni": "TR",
}


def normalizza(testo):
    return " ".join(str(testo or "").strip().split())


def sembra_indirizzo(testo):
    testo = normalizza(testo)
    basso = testo.lower()

    parole = [
        "via ",
        "viale ",
        "corso ",
        "piazza ",
        "piazzale ",
        "strada ",
        "ss ",
        "s.s.",
        "statale ",
        "provinciale ",
        "località ",
        "loc.",
        "frazione ",
        "fraz.",
        "passo ",
    ]

    if len(testo) < 6:
        return False

    if basso.startswith("basko via") or basso.startswith("basko corso") or basso.startswith("basko piazza"):
        return False

    return any(basso.startswith(p) for p in parole)


def estrai_sigla_da_testo(testo):
    testo = f" {normalizza(testo).upper()} "
    match = re.search(r"\b([A-Z]{2})\b$", testo.strip())
    if match:
        sigla = match.group(1)
        if sigla in PROVINCE_NAMES:
            return sigla
    return ""


def estrai_cap(testo):
    match = re.search(r"\b\d{5}\b", testo)
    return match.group(0) if match else ""


def crea_record(brand, address, province_code, source_url):
    province_code = province_code.upper().strip()
    province_name = PROVINCE_NAMES.get(province_code, province_code)

    return {
        "brand": brand,
        "store_name": brand,
        "province_code": province_code,
        "province_name": province_name,
        "address": normalizza(address),
        "postal_code": estrai_cap(address),
        "source_url": source_url,
        "status": "active",
    }


def estrai_dipiu(html, brand, source_url):
    soup = BeautifulSoup(html, "html.parser")
    righe = [normalizza(x) for x in soup.get_text("\n", strip=True).split("\n")]
    righe = [x for x in righe if x]

    stores = []

    for i, riga in enumerate(righe):
        if not sembra_indirizzo(riga):
            continue

        comune = ""
        province_code = ""

        for prossima in righe[i + 1:i + 5]:
            prossima = normalizza(prossima)

            if prossima in COMUNE_TO_PROVINCE:
                comune = prossima
                province_code = COMUNE_TO_PROVINCE[prossima]
                break

            sigla = estrai_sigla_da_testo(prossima)
            if sigla:
                province_code = sigla
                comune = sigla
                break

        sigla_da_indirizzo = estrai_sigla_da_testo(riga)
        if sigla_da_indirizzo:
            province_code = sigla_da_indirizzo

        if not province_code:
            continue

        address = riga
        if comune and comune not in address:
            address = f"{riga}, {comune}"

        stores.append(crea_record(brand, address, province_code, source_url))

    return stores


def estrai_basko(html, brand, source_url):
    soup = BeautifulSoup(html, "html.parser")
    righe = [normalizza(x) for x in soup.get_text("\n", strip=True).split("\n")]
    righe = [x for x in righe if x]

    stores = []

    for riga in righe:
        if not sembra_indirizzo(riga):
            continue

        province_code = estrai_sigla_da_testo(riga)

        if not province_code:
            continue

        stores.append(crea_record(brand, riga, province_code, source_url))

    return stores


def rimuovi_duplicati(stores):
    visti = set()
    risultato = []

    for store in stores:
        chiave = (
            store["brand"].lower(),
            store["province_code"].lower(),
            store["address"].lower(),
        )

        if chiave in visti:
            continue

        visti.add(chiave)
        risultato.append(store)

    return risultato


def main():
    all_stores = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            locale="it-IT",
            user_agent="Mozilla/5.0"
        )

        for source in SOURCES:
            brand = source["brand"]
            url = source["url"]

            print(f"Scarico {brand}: {url}")

            page.goto(url, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(5000)
            html = page.content()

            if brand == "Di Più":
                stores = estrai_dipiu(html, brand, url)
            elif brand == "Basko":
                stores = estrai_basko(html, brand, url)
            else:
                stores = []

            stores = rimuovi_duplicati(stores)
            print(f"{brand}: {len(stores)} punti vendita puliti")

            all_stores.extend(stores)

        browser.close()

    all_stores = rimuovi_duplicati(all_stores)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_stores, f, ensure_ascii=False, indent=2)

    print(f"Totale punti vendita salvati: {len(all_stores)}")


if __name__ == "__main__":
    main()
