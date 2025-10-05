import sys
import csv
import requests
from bs4 import BeautifulSoup
import os

OUTPUT_CSV = "prodotti_completi.csv"
IMG_DIR = "immagini"

os.makedirs(IMG_DIR, exist_ok=True)

def scarica_pagina(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.text

def estrai_dati(html):
    soup = BeautifulSoup(html, "html.parser")

    # Titolo
    titolo = soup.select_one("h2.single-product__title")
    titolo = titolo.get_text(strip=True) if titolo else ""

    # Prezzo
    prezzo = soup.select_one(".single-product__price .amount")
    prezzo = prezzo.get_text(strip=True) if prezzo else ""

    # Descrizione breve
    breve = soup.select_one(".woocommerce-product-details__short-description")
    breve = breve.get_text(" ", strip=True) if breve else ""

    # Descrizione lunga
    lunga = soup.select_one("#tab-description")
    lunga = lunga.get_text(" ", strip=True) if lunga else ""

    # Immagini
    immagini = []
    for img in soup.select(".single-product__featured img, .single-product__gallery img"):
        url = img.get("data-src") or img.get("src")
        if url and url not in immagini:
            immagini.append(url)
            try:
                nome_file = os.path.join(IMG_DIR, os.path.basename(url.split("?")[0]))
                if not os.path.exists(nome_file):
                    r = requests.get(url, timeout=10)
                    with open(nome_file, "wb") as f:
                        f.write(r.content)
            except Exception as e:
                print(f"Errore download immagine {url}: {e}")

    # SKU principale
    sku = soup.select_one(".single-product__sku")
    sku = sku.get_text(strip=True) if sku else ""

    # Varianti (taglie)
    varianti = []
    for v in soup.select(".variation__item"):
        varianti.append({
            "variationId": v.get("data-variation"),
            "sku": v.get("data-sku"),
            "size": v.get("data-name")
        })

    # Tabs
    tabs = {}
    for tab in soup.select(".single-product__tabs .tab__item"):
        titolo_tab = tab.select_one(".tab__title")
        contenuto = tab.select_one(".tab__content")
        if titolo_tab and contenuto:
            tabs[titolo_tab.get_text(strip=True)] = contenuto.get_text(" ", strip=True)

    # Prodotti simili
    simili = []
    for prod in soup.select(".sk-carousel-products .sk-product .enhanced-product"):
        simili.append({
            "id": prod.get("data-id"),
            "name": prod.get("data-name"),
            "price": prod.get("data-price"),
            "brand": prod.get("data-brand")
        })

    return (
        titolo,
        prezzo,
        breve,
        lunga,
        "|".join(immagini),
        sku,
        ";".join([f"{v['size']}({v['sku']})" for v in varianti]),
        "; ".join([f"{k}: {v}" for k, v in tabs.items()]),
        "; ".join([f"{p['name']} ({p['price']}€)" for p in simili])
    )

def main():
    if len(sys.argv) < 2:
        print("❌ Devi passare un URL come parametro!")
        print("Esempio: python scraper.py \"https://www.two-way.it/prodotto/camicia-nero/\"")
        sys.exit(1)

    url = sys.argv[1]
    print(f"Elaboro {url} ...")

    try:
        html = scarica_pagina(url)
        titolo, prezzo, breve, lunga, immagini, sku, varianti, tabs, simili = estrai_dati(html)

        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fout:
            fieldnames = [
                "URL", "Titolo", "Prezzo", "Descrizione breve", "Descrizione lunga",
                "Immagini", "SKU", "Varianti", "Tabs", "Prodotti simili"
            ]
            writer = csv.DictWriter(fout, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow({
                "URL": url,
                "Titolo": titolo,
                "Prezzo": prezzo,
                "Descrizione breve": breve,
                "Descrizione lunga": lunga,
                "Immagini": immagini,
                "SKU": sku,
                "Varianti": varianti,
                "Tabs": tabs,
                "Prodotti simili": simili
            })

        print(f"✅ Dati salvati in {OUTPUT_CSV}")

    except Exception as e:
        print(f"❌ Errore con {url}: {e}")

if __name__ == "__main__":
    main()
