from playwright.sync_api import sync_playwright
import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path

URL = "https://www.dipiuperlascuola.it/it/seopagemenulabel/punti-vendita/pm-13-21"

OUTPUT_FILE = Path("mappa-public-render/seed_data.json")

def scarica_pagina():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            locale="it-IT",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )

        page.goto(URL, wait_until="networkidle", timeout=60000)
        html = page.content()

        browser.close()
        return html
    
def estrai_punti_vendita(html):
    soup = BeautifulSoup(html, "html.parser")

    stores = []
    testi = soup.get_text("\n", strip=True).split("\n")

    parole_indirizzo = [
        "via", "viale", "corso", "piazza", "piazzale",
        "strada", "ss", "s.s.", "statale", "provinciale",
        "località", "loc.", "frazione", "fraz."
    ]

    parole_da_escludere = [
        "pavia", "aviano"
    ]

    for riga in testi:
        riga = " ".join(riga.strip().split())

        if not riga:
            continue

        riga_lower = riga.lower()

        # Esclude righe troppo corte o città isolate tipo "Pavia"
        if len(riga) < 8:
            continue

        # Esclude parole/città che non sono indirizzi
        if riga_lower in parole_da_escludere:
            continue

        # Tiene solo righe che sembrano indirizzi
        if not any(riga_lower.startswith(parola) or f" {parola} " in riga_lower for parola in parole_indirizzo):
            continue

        # Evita duplicati
        if any(store["indirizzo"].lower() == riga_lower for store in stores):
            continue

        stores.append({
            "nome": "Di Più",
            "indirizzo": riga,
            "azienda": "Di Più"
        })

    return stores

def salva_json(stores):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(stores, file, ensure_ascii=False, indent=2)

def main():
    html = scarica_pagina()

    soup = BeautifulSoup(html, "html.parser")
    testi = soup.get_text("\n", strip=True).split("\n")

    print("=== PRIME 200 RIGHE LETTE DALLA PAGINA ===")
    for i, riga in enumerate(testi[:200]):
        print(i, repr(riga))
    print("=== FINE RIGHE ===")

    stores = estrai_punti_vendita(html)
    salva_json(stores)

    print(f"Aggiornati {len(stores)} punti vendita.")
if __name__ == "__main__":
    main()
