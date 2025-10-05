import sys
import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import os

OUTPUT_CSV = "prodotti_completi.csv"
IMG_DIR = "immagini"

os.makedirs(IMG_DIR, exist_ok=True)


def scarica_pagina(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.text


def parse_pagina(url):
    """Estrae i dati da una singola pagina prodotto"""
    html = scarica_pagina(url)
    soup = BeautifulSoup(html, "html.parser")

    # Titolo
    titolo_elem = soup.select_one("h2.single-product__title")
    titolo = titolo_elem.get_text(strip=True) if titolo_elem else ""
    titolo_slug = "-".join(titolo.lower().split()) if titolo else ""

    # Prezzo
    prezzo_elem = soup.select_one(".single-product__price .amount")
    prezzo = prezzo_elem.get_text(strip=True) if prezzo_elem else ""

    # Descrizione breve
    descrizione_elem = soup.select_one(".single-product__description")
    descrizione = descrizione_elem.get_text(" ", strip=True) if descrizione_elem else ""

    # Immagini principali
    immagini = []
    for img in soup.select(".single-product__featured img, .single-product__gallery img"):
        url_img = img.get("data-src") or img.get("src")
        if url_img:
            filename = os.path.basename(url_img.split("?")[0])
            if filename not in immagini:
                immagini.append(filename)
                # scarico immagine se non già presente
                try:
                    nome_file = os.path.join(IMG_DIR, filename)
                    if not os.path.exists(nome_file):
                        r = requests.get(url_img, timeout=10)
                        with open(nome_file, "wb") as f:
                            f.write(r.content)
                except Exception as e:
                    print(f"Errore download immagine {url_img}: {e}")

    # SKU principale (tolgo prefisso "SKU ")
    sku_elem = soup.select_one(".single-product__sku")
    sku = sku_elem.get_text(strip=True) if sku_elem else ""
    if sku.upper().startswith("SKU "):
        sku = sku[4:]

    # Taglie
    taglie = []
    for v in soup.select(".variation__item"):
        name = v.get("data-name")
        if name and name.upper() in ["XS", "S", "M", "L", "XL", "XXL"]:
            taglie.append(name)

    # Colore (dalla slug URL)
    slug_corrente = urlparse(url).path.strip("/").split("/")[-1]
    colore = ""
    if slug_corrente.startswith(titolo_slug):
        colore = slug_corrente.replace(titolo_slug, "").strip("-").capitalize()

    # Tabs (es. composizione, spedizione, resi)
    tabs = {}
    for tab in soup.select(".single-product__tabs .tab__item"):
        titolo_tab = tab.select_one(".tab__title")
        contenuto = tab.select_one(".tab__content")
        if titolo_tab and contenuto:
            tabs[titolo_tab.get_text(strip=True)] = contenuto.get_text(" ", strip=True)

    return (
        url,
        titolo,
        prezzo,
        descrizione,
        ";".join(immagini),
        sku,
        ";".join(taglie) if taglie else "",
        colore,
        "; ".join([f"{k}: {v}" for k, v in tabs.items()])
    ), soup, titolo_slug


def estrai_varianti(url):
    """Ritorna una lista di tuple: una per ogni colore (incluso quello corrente)."""
    risultati = []
    visitati = set()

    def aggiungi(url_page):
        if url_page in visitati:
            return
        row, soup, titolo_slug = parse_pagina(url_page)
        risultati.append(row)
        visitati.add(url_page)
        return soup, titolo_slug

    # 1. Pagina corrente
    soup, titolo_slug = aggiungi(url)

    # 2. Altri colori
    for a in soup.select(".product__colors .color__item a"):
        href = a.get("href")
        if href:
            aggiungi(href)

    return risultati

def main():
    if len(sys.argv) < 2:
        print("❌ Devi passare un URL come parametro!")
        print("Esempio: python scraper.py \"https://www.two-way.it/prodotto/camicia-con-laccio-bianco/\"")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Elaboro {url} ...")

    try:
        varianti = estrai_varianti(url)

        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fout:
            fieldnames = ["URL", "Titolo", "Prezzo", "Descrizione",
                          "Immagini", "SKU", "Taglie", "Colore", "Tabs"]
            writer = csv.DictWriter(fout, fieldnames=fieldnames)
            writer.writeheader()

            for row in varianti:
                writer.writerow({
                    "URL": row[0],
                    "Titolo": row[1],
                    "Prezzo": row[2],
                    "Descrizione": row[3],
                    "Immagini": row[4],
                    "SKU": row[5],
                    "Taglie": row[6],
                    "Colore": row[7],
                    "Tabs": row[8]
                })

        print(f"✅ Dati salvati in {OUTPUT_CSV}")

    except Exception as e:
        print(f"❌ Errore con {url}: {e}")


if __name__ == "__main__":
    main()
