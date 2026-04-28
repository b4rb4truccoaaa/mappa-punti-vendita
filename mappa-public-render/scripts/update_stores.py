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
    testi = [" ".join(riga.strip().split()) for riga in testi if riga.strip()]

    parole_indirizzo = [
        "via", "viale", "corso", "piazza", "piazzale",
        "strada", "ss", "s.s.", "statale", "provinciale",
        "località", "loc.", "frazione", "fraz."
    ]

    regioni = [
        "abruzzo", "basilicata", "calabria", "campania",
        "emilia romagna", "friuli venezia giulia", "lazio",
        "liguria", "lombardia", "marche", "molise", "piemonte",
        "puglia", "sardegna", "sicilia", "toscana",
        "trentino alto adige", "umbria", "valle d'aosta",
        "veneto"
    ]

    parole_da_escludere = [
        "home", "punti vendita", "contatti", "privacy",
        "cookie", "newsletter", "volantino", "login"
    ]

    def sembra_indirizzo(riga):
        riga_lower = riga.lower()

        if len(riga) < 8:
            return False

        if riga_lower in regioni:
            return False

        if any(blocco in riga_lower for blocco in parole_da_escludere):
            return False

        return any(
            riga_lower.startswith(parola) or f" {parola} " in riga_lower
            for parola in parole_indirizzo
        )

    def pulisci_comune(riga):
        riga = riga.strip()

        # Se è una regione, non usarla come comune
        if riga.lower() in regioni:
            return ""

        # Se è troppo lunga, probabilmente non è un comune
        if len(riga) > 35:
            return ""

        # Se contiene numeri, probabilmente non è un comune
        if any(char.isdigit() for char in riga):
            return ""

        # Se contiene parole da menu/sito, scartala
        if any(blocco in riga.lower() for blocco in parole_da_escludere):
            return ""

        return riga

    for i, riga in enumerate(testi):
        riga_pulita = riga.strip()

        if not sembra_indirizzo(riga_pulita):
            continue

        comune = ""

        # Guarda solo le 2 righe dopo l'indirizzo
        for prossima in testi[i + 1:i + 3]:
            possibile_comune = pulisci_comune(prossima)

            if possibile_comune and not sembra_indirizzo(possibile_comune):
                comune = possibile_comune
                break

        indirizzo_completo = riga_pulita

        if comune and comune.lower() not in riga_pulita.lower():
            indirizzo_completo = f"{riga_pulita}, {comune}"

        if any(store["indirizzo_completo"].lower() == indirizzo_completo.lower() for store in stores):
            continue

        stores.append({
            "nome": "Di Più",
            "indirizzo": riga_pulita,
            "comune": comune,
            "provincia": "",
            "indirizzo_completo": indirizzo_completo,
            "azienda": "Di Più"
        })

    return stores
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
