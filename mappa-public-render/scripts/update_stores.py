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

    parole_da_escludere = [
        "pavia", "aviano"
    ]

    province_sigle = [
        "AG", "AL", "AN", "AO", "AR", "AP", "AT", "AV",
        "BA", "BT", "BL", "BN", "BG", "BI", "BO", "BZ", "BS", "BR",
        "CA", "CL", "CB", "CI", "CE", "CT", "CZ", "CH", "CO", "CS", "CR", "KR", "CN",
        "EN", "FM", "FE", "FI", "FG", "FC", "FR",
        "GE", "GO", "GR",
        "IM", "IS",
        "SP", "AQ", "LT", "LE", "LC", "LI", "LO", "LU",
        "MC", "MN", "MS", "MT", "VS", "ME", "MI", "MO", "MB",
        "NA", "NO", "NU",
        "OR",
        "PD", "PA", "PR", "PV", "PG", "PU", "PE", "PC", "PI", "PT", "PN", "PZ", "PO",
        "RG", "RA", "RC", "RE", "RI", "RN", "RM", "RO",
        "SA", "SS", "SV", "SI", "SR", "SO",
        "TA", "TE", "TR", "TO", "TP", "TN", "TV", "TS",
        "UD",
        "VA", "VE", "VB", "VC", "VR", "VV", "VI", "VT"
    ]

    def sembra_indirizzo(riga):
        riga_lower = riga.lower()

        if len(riga) < 8:
            return False

        if riga_lower in parole_da_escludere:
            return False

        return any(
            riga_lower.startswith(parola) or f" {parola} " in riga_lower
            for parola in parole_indirizzo
        )

    def sembra_comune_o_provincia(riga):
        if len(riga) < 3:
            return False

        if riga.lower() in parole_da_escludere:
            return False

        # Esempi: "Pavia", "Vittorio Veneto (TV)", "FIVIZZANO - Fraz. ROMETTA (MS)"
        if any(f"({sigla})" in riga.upper() for sigla in province_sigle):
            return True

        # Riga breve senza numeri: spesso è un comune
        if len(riga) <= 40 and not any(char.isdigit() for char in riga):
            parole_bloccate = [
                "home", "punti vendita", "contatti", "privacy",
                "cookie", "newsletter", "volantino", "login"
            ]

            if not any(blocco in riga.lower() for blocco in parole_bloccate):
                return True

        return False

    ultimo_comune = ""
    ultima_provincia = ""

    for i, riga in enumerate(testi):
        riga_pulita = riga.strip()
        riga_upper = riga_pulita.upper()

        # Se troviamo una riga tipo "Vittorio Veneto (TV)", salviamo comune e provincia
        provincia_trovata = ""
        for sigla in province_sigle:
            if f"({sigla})" in riga_upper:
                provincia_trovata = sigla
                break

        if sembra_comune_o_provincia(riga_pulita) and not sembra_indirizzo(riga_pulita):
            ultimo_comune = riga_pulita
            ultima_provincia = provincia_trovata
            continue

        if not sembra_indirizzo(riga_pulita):
            continue

        comune = ultimo_comune
        provincia = ultima_provincia

        # Se nelle 3 righe dopo l'indirizzo c'è una città/provincia, la usa
        for prossima in testi[i + 1:i + 4]:
            if sembra_comune_o_provincia(prossima) and not sembra_indirizzo(prossima):
                comune = prossima

                prossima_upper = prossima.upper()
                for sigla in province_sigle:
                    if f"({sigla})" in prossima_upper:
                        provincia = sigla
                        break

                break

        pezzi_indirizzo = [riga_pulita]

        if comune and comune.lower() not in riga_pulita.lower():
            pezzi_indirizzo.append(comune)

        indirizzo_completo = ", ".join(pezzi_indirizzo)

        # Evita duplicati
        if any(store["indirizzo_completo"].lower() == indirizzo_completo.lower() for store in stores):
            continue

        stores.append({
            "nome": "Di Più",
            "indirizzo": riga_pulita,
            "comune": comune,
            "provincia": provincia,
            "indirizzo_completo": indirizzo_completo,
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
