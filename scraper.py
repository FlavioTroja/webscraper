import sys
import csv
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import os

OUTPUT_CSV = "prodotti_shopify.csv"
VENDOR = "TwoWay"
PRODUCT_CATEGORY = "Apparel & Accessories > Clothing"
PRODUCT_TYPE = "Shirts"

DEFAULTS = {
    "Tags": "",
    "Published on online store": "TRUE",
    "Status": "active",
    "Barcode": "",
    "Compare-at price": "",
    "Cost per item": "",
    "Charge tax": "TRUE",
    "Tax code": "",
    "Unit price total measure": "",
    "Unit price total measure unit": "",
    "Unit price base measure": "",
    "Unit price base measure unit": "",
    "Inventory tracker": "shopify",
    "Inventory quantity": "200",
    "Continue selling when out of stock": "deny",
    "Weight value (grams)": "200",
    "Weight unit for display": "g",
    "Requires shipping": "TRUE",
    "Fulfillment service": "manual",
    "Image position": "1",
    "Image alt text": "",
    "Gift card": "FALSE",
    "Google Shopping / Google product category": PRODUCT_CATEGORY,
    "Google Shopping / Gender": "",
    "Google Shopping / Age group": "",
    "Google Shopping / MPN": "",
    "Google Shopping / AdWords Grouping": "",
    "Google Shopping / AdWords labels": "",
    "Google Shopping / Condition": "new",
    "Google Shopping / Custom product": "FALSE",
    "Google Shopping / Custom label 0": "",
    "Google Shopping / Custom label 1": "",
    "Google Shopping / Custom label 2": "",
    "Google Shopping / Custom label 3": "",
    "Google Shopping / Custom label 4": ""
}

def scarica_pagina(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.text


def parse_pagina(url):
    html = scarica_pagina(url)
    soup = BeautifulSoup(html, "html.parser")

    # Titolo
    titolo_elem = soup.select_one("h2.single-product__title")
    titolo = titolo_elem.get_text(strip=True) if titolo_elem else ""
    handle = "-".join(titolo.lower().split())

    # Prezzo
    prezzo_elem = soup.select_one(".single-product__price .amount")
    prezzo_txt = prezzo_elem.get_text(strip=True).replace("€", "").replace(",", ".") if prezzo_elem else "0"
    try:
        prezzo = float(prezzo_txt)
    except:
        prezzo = 0.0

    # Descrizione breve
    descrizione_elem = soup.select_one(".single-product__description")
    descrizione = descrizione_elem.get_text(" ", strip=True) if descrizione_elem else ""

    # Immagini
    immagini = []
    for img in soup.select(".single-product__featured img, .single-product__gallery img"):
        url_img = img.get("data-src") or img.get("src")
        if url_img and url_img not in immagini:
            immagini.append(url_img)

    # SKU principale
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

    # Colore dal path URL
    slug_corrente = urlparse(url).path.strip("/").split("/")[-1]
    colore_corrente = ""
    if handle and slug_corrente.startswith(handle):
        colore_corrente = slug_corrente.replace(handle, "").strip("-").capitalize()

    # Tabs per SEO description
    tabs = []
    for tab in soup.select(".single-product__tabs .tab__item"):
        titolo_tab = tab.select_one(".tab__title")
        contenuto = tab.select_one(".tab__content")
        if titolo_tab and contenuto:
            tabs.append(f"{titolo_tab.get_text(strip=True)}: {contenuto.get_text(' ', strip=True)}")
    seo_description = " ".join(tabs)[:320]

    # Altri colori
    colori = []
    for a in soup.select(".product__colors .color__item a"):
        href = a.get("href")
        if not href:
            continue
        slug = urlparse(href).path.strip("/").split("/")[-1]
        if handle and slug.startswith(handle):
            colore = slug.replace(handle, "").strip("-").capitalize()
            if colore and colore not in colori:
                colori.append(colore)

    if colore_corrente and colore_corrente not in colori:
        colori.insert(0, colore_corrente)

    return {
        "url": url,
        "titolo": titolo,
        "handle": handle,
        "prezzo": prezzo,
        "descrizione": descrizione,
        "immagini": immagini,
        "sku": sku,
        "taglie": taglie,
        "colori": colori,
        "seo_description": seo_description
    }


def estrai_varianti(url):
    """Genera master + varianti"""
    visitati = set()
    prodotti = []

    def aggiungi_varianti(url_page):
        if url_page in visitati:
            return
        visitati.add(url_page)
        dati = parse_pagina(url_page)

        # Riga MASTER
        master = {**DEFAULTS}
        master.update({
            "Title": dati["titolo"],
            "URL handle": dati["handle"],
            "Description": dati["descrizione"],
            "Vendor": VENDOR,
            "Product category": PRODUCT_CATEGORY,
            "Type": PRODUCT_TYPE,
            "SKU": "",
            "Option1 name": "Title",
            "Option1 value": f'{dati["titolo"]}',
            "Option2 name": "",
            "Option2 value": "",
            "Option3 name": "",
            "Option3 value": "",
            "Price": dati["prezzo"],
            "Product image URL": dati["immagini"][0] if dati["immagini"] else "",
            "Image position": "1",
            "Variant image URL": "",
            "SEO title": dati["titolo"],
            "SEO description": dati["seo_description"]
        })
        prodotti.append(master)

        # Varianti taglia × colore
        for colore in dati["colori"]:
            for taglia in (dati["taglie"] or ["Unica"]):
                variante = {**DEFAULTS}
                variante.update({
                    "Title": "",
                    "URL handle": dati["handle"],
                    "Description": "",
                    "Vendor": "",
                    "Product category": "",
                    "Type": "",
                    "SKU": f"{dati['sku']}_{colore}_{taglia}".replace(" ", ""),
                    "Option1 name": "Size",
                    "Option1 value": taglia,
                    "Option2 name": "Color",
                    "Option2 value": colore,
                    "Option3 name": "",
                    "Option3 value": "",
                    "Price": dati["prezzo"],
                    "Product image URL": "",
                    "Variant image URL": dati["immagini"][0] if dati["immagini"] else "",
                    "SEO title": "",
                    "SEO description": ""
                })
                prodotti.append(variante)
        return dati

    dati_corrente = aggiungi_varianti(url)

    html = scarica_pagina(url)
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.select(".product__colors .color__item a"):
        href = a.get("href")
        if href:
            aggiungi_varianti(href)

    return prodotti


def main():
    if len(sys.argv) < 2:
        print("❌ Devi passare un URL come parametro!")
        print("Esempio: python shopify_scraper_full.py \"https://www.two-way.it/prodotto/camicia-con-laccio-bianco/\"")
        sys.exit(1)

    url = sys.argv[1]
    print(f"🧵 Elaboro {url} ...")

    try:
        prodotti = estrai_varianti(url)

        fieldnames = [
            "Title","URL handle","Description","Vendor","Product category","Type","Tags",
            "Published on online store","Status","SKU","Barcode","Option1 name","Option1 value",
            "Option2 name","Option2 value","Option3 name","Option3 value","Price","Compare-at price",
            "Cost per item","Charge tax","Tax code","Unit price total measure",
            "Unit price total measure unit","Unit price base measure","Unit price base measure unit",
            "Inventory tracker","Inventory quantity","Continue selling when out of stock",
            "Weight value (grams)","Weight unit for display","Requires shipping","Fulfillment service",
            "Product image URL","Image position","Image alt text","Variant image URL","Gift card",
            "SEO title","SEO description","Google Shopping / Google product category",
            "Google Shopping / Gender","Google Shopping / Age group","Google Shopping / MPN",
            "Google Shopping / AdWords Grouping","Google Shopping / AdWords labels",
            "Google Shopping / Condition","Google Shopping / Custom product",
            "Google Shopping / Custom label 0","Google Shopping / Custom label 1",
            "Google Shopping / Custom label 2","Google Shopping / Custom label 3",
            "Google Shopping / Custom label 4"
        ]

        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as fout:
            writer = csv.DictWriter(fout, fieldnames=fieldnames)
            writer.writeheader()
            for row in prodotti:
                writer.writerow(row)

        print(f"✅ File generato: {OUTPUT_CSV}")
        print(f"📦 Righe totali: {len(prodotti)}")

    except Exception as e:
        print(f"❌ Errore: {e}")


if __name__ == "__main__":
    main()
