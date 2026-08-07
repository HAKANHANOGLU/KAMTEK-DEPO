# -*- coding: utf-8 -*-
"""DIA'dan internet satış sitesine beslenen ürün/stok XML'ini çeker ve
standart bir liste (sözlük listesi) haline getirir."""
import xml.etree.ElementTree as ET

import requests

XML_URL = "https://uzakdisk.com/kamtek/pdf/kamtek.xml"


def stok_verisini_getir():
    r = requests.get(XML_URL, timeout=20)
    r.raise_for_status()
    root = ET.fromstring(r.content)

    urunler = []
    for prod in root.findall(".//product"):
        def _metin(tag, _prod=prod):
            el = _prod.find(tag)
            if el is not None and el.text:
                return el.text.strip()
            return ""

        kategoriler = [c.text.strip() for c in prod.findall("categories/category/category_name") if c.text]
        gorseller = [g.text.strip() for g in prod.findall("images/image_url") if g.text]

        urunler.append({
            "Stok Kodu": _metin("sku"),
            "Ürün Adı": _metin("name"),
            "Marka": _metin("brand_name"),
            "Kategori": ", ".join(kategoriler),
            "Fiyat": _metin("price1"),
            "Para Birimi": _metin("price1_currency"),
            "Stok": _metin("b2b_stock_qty"),
            "Açıklama": _metin("note"),
            "Görsel": gorseller[0] if gorseller else "",
        })
    return urunler
