import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path

URL = "https://www.dipiuperlascuola.it/it/seopagemenulabel/punti-vendita/pm-13-21"

OUTPUT_FILE = Path("data/stores.json")

def scarica_pagina():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
        "Referer": "https://www.dipiuperlascuola.it/"
    }

    response = requests.get(URL, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text
    
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
    stores = estrai_punti_vendita(html)
    salva_json(stores)

    print(f"Aggiornati {len(stores)} punti vendita.")

if __name__ == "__main__":
    main()
