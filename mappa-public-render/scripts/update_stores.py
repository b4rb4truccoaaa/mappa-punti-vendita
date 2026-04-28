from playwright.sync_api import sync_playwright
import json
from bs4 import BeautifulSoup
from pathlib import Path

OUTPUT_FILE = Path("mappa-public-render/seed_data.json")

SOURCES = [
    {
        "brand": "Di Più",
        "url": "https://www.dipiuperlascuola.it/it/seopagemenulabel/punti-vendita/pm-13-21"
    },
    {
        "brand": "Bennet",
        "url": "https://www.bennet.com/storefinder"
    },
    {
        "brand": "Basko",
        "url": "https://www.basko.it/supermercati"
    }
]


def scarica_pagina(page, url):
    page.goto(url, wait_until="networkidle", timeout=90000)
    return page.content()


def normalizza_spazi(testo):
    return " ".join(str(testo or "").strip().split())


def sembra_indirizzo(riga):
    riga_lower = riga.lower()

    parole_indirizzo = [
        "via", "viale", "corso", "piazza", "piazzale",
        "strada", "ss", "s.s.", "statale", "provinciale",
        "località", "loc.", "frazione", "fraz.", "passo"
    ]

    if len(riga) < 6:
        return False

    return any(
        riga_lower.startswith(parola) or f" {parola} " in riga_lower
        for parola in parole_indirizzo
    )


def pulisci_comune(riga):
    riga = normalizza_spazi(riga)

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
        "cookie", "newsletter", "volantino", "login",
        "mostra", "filtri", "annulla", "cancella",
        "servizi", "orari", "indicazioni"
    ]

    if not riga:
        return ""

    if riga.lower() in regioni:
        return ""

    if len(riga) > 40:
        return ""

    if any(char.isdigit() for char in riga):
        return ""

    if any(blocco in riga.lower() for blocco in parole_da_escludere):
        return ""

    if sembra_indirizzo(riga):
        return ""

    return riga


def estrai_generico(html, brand, source_url):
    soup = BeautifulSoup(html, "html.parser")
    testi = soup.get_text("\n", strip=True).split("\n")
    testi = [normalizza_spazi(riga) for riga in testi if normalizza_spazi(riga)]

    stores = []

    for i, riga in enumerate(testi):
        if not sembra_indirizzo(riga):
            continue

        comune = ""

        for prossima in testi[i + 1:i + 4]:
            possibile_comune = pulisci_comune(prossima)
            if possibile_comune:
                comune = possibile_comune
                break

        indirizzo_completo = riga
        if comune and comune.lower() not in riga.lower():
            indirizzo_completo = f"{riga}, {comune}"

        stores.append({
            "nome": brand,
            "indirizzo": riga,
            "comune": comune,
            "provincia": "",
            "indirizzo_completo": indirizzo_completo,
            "azienda": brand,
            "source_url": source_url
        })

    return stores


def rimuovi_duplicati(stores):
    visti = set()
    puliti = []

    for store in stores:
        chiave = (
            normalizza_spazi(store.get("azienda")).lower(),
            normalizza_spazi(store.get("indirizzo_completo")).lower()
        )

        if chiave in visti:
            continue

        visti.add(chiave)
        puliti.append(store)

    return puliti


def salva_json(stores):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(stores, file, ensure_ascii=False, indent=2)


def main():
    all_stores = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            locale="it-IT",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )

        for source in SOURCES:
            brand = source["brand"]
            url = source["url"]

            print(f"Scarico {brand}: {url}")

            try:
                html = scarica_pagina(page, url)
                stores = estrai_generico(html, brand, url)
                stores = rimuovi_duplicati(stores)

                print(f"{brand}: trovati {len(stores)} punti vendita")
                all_stores.extend(stores)

            except Exception as errore:
                print(f"Errore durante aggiornamento {brand}: {errore}")

        browser.close()

    all_stores = rimuovi_duplicati(all_stores)
    salva_json(all_stores)

    print(f"Aggiornati {len(all_stores)} punti vendita totali.")


if __name__ == "__main__":
    main()
