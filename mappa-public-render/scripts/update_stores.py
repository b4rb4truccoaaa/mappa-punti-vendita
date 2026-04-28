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

    # ATTENZIONE:
    # Questa parte va adattata alla struttura reale della pagina.
    # Per ora cerca blocchi di testo generici.
    testi = soup.get_text("\n", strip=True).split("\n")

    for riga in testi:
        riga = riga.strip()

        if not riga:
            continue

        # Esempio molto semplice:
        # qui poi possiamo migliorarlo in base a come sono scritti i punti vendita
        if any(parola in riga.lower() for parola in ["via", "corso", "piazza", "viale"]):
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
