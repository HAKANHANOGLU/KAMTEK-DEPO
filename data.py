# -*- coding: utf-8 -*-
"""Sabit veriler: kargo fiyat tarifeleri, il listesi, il bazlı kargo istisnaları."""

# 81 il (Türkiye siyasi haritası / il seçim listesi için)
IL_LISTESI = [
    "ADANA", "ADIYAMAN", "AFYONKARAHİSAR", "AĞRI", "AMASYA", "ANKARA", "ANTALYA",
    "ARTVİN", "AYDIN", "BALIKESİR", "BİLECİK", "BİNGÖL", "BİTLİS", "BOLU",
    "BURDUR", "BURSA", "ÇANAKKALE", "ÇANKIRI", "ÇORUM", "DENİZLİ", "DİYARBAKIR",
    "EDİRNE", "ELAZIĞ", "ERZİNCAN", "ERZURUM", "ESKİŞEHİR", "GAZİANTEP",
    "GİRESUN", "GÜMÜŞHANE", "HAKKARİ", "HATAY", "ISPARTA", "MERSİN", "İSTANBUL",
    "İZMİR", "KARS", "KASTAMONU", "KAYSERİ", "KIRKLARELİ", "KIRŞEHİR", "KOCAELİ",
    "KONYA", "KÜTAHYA", "MALATYA", "MANİSA", "KAHRAMANMARAŞ", "MARDİN", "MUĞLA",
    "MUŞ", "NEVŞEHİR", "NİĞDE", "ORDU", "RİZE", "SAKARYA", "SAMSUN", "SİİRT",
    "SİNOP", "SİVAS", "TEKİRDAĞ", "TOKAT", "TRABZON", "TUNCELİ", "ŞANLIURFA",
    "UŞAK", "VAN", "YOZGAT", "ZONGULDAK", "AKSARAY", "BAYBURT", "KARAMAN",
    "KIRIKKALE", "BATMAN", "ŞIRNAK", "BARTIN", "ARDAHAN", "IĞDIR", "YALOVA",
    "KARABÜK", "KİLİS", "OSMANİYE", "DÜZCE",
]

# Kargo firmalarının desi bazlı fiyat tarifesi (KDV HARİÇ).
# tiers: (alt_desi, ust_desi, tutar). artan_desi: üst sınırı aşan desi başına ek ücret (yoksa None).
# iller: "ALL" (her ile gönderim yapar) veya sadece gönderim yapılan iki harfli il listesi.
PRICING = {
    "DHL": {
        "logo": "dhl_logo.jpg",
        "tiers": [
            (1, 5, 143.70), (6, 10, 164.23), (11, 15, 197.06), (16, 20, 235.56),
            (21, 25, 293.40), (26, 30, 386.65), (31, 35, 420.76), (36, 40, 557.23),
            (41, 45, 665.25),
        ],
        "artan_desi": None,
        "iller": "ALL",
    },
    "İNTERGLOBAL": {
        "logo": "interglobal_logo.png",
        "tiers": [
            (1, 5, 100), (6, 10, 120), (11, 15, 160), (16, 20, 200), (21, 30, 242),
        ],
        "artan_desi": 10.6,
        "iller": ["İZMİR", "BALIKESİR", "İSTANBUL", "KOCAELİ", "ESKİŞEHİR", "ANKARA", "DENİZLİ"],
    },
    "ARAS": {
        "logo": "aras_logo.jpg",
        "tiers": [
            (1, 10, 176.45), (11, 15, 186.34), (16, 20, 229.51), (21, 25, 269.52),
            (26, 30, 307.17),
        ],
        "artan_desi": 9.8,
        "iller": "ALL",
    },
    "YURTİÇİ": {
        "logo": "yurtici_logo.jpg",
        "tiers": [
            (1, 5, 125), (6, 10, 160), (11, 15, 185), (16, 20, 235), (21, 30, 320),
        ],
        "artan_desi": 10.6,
        "iller": "ALL",
    },
}

# Her kargo firmasının HALKA AÇIK gönderi sorgulama sayfasına, takip numarasıyla
# doğrudan gidecek link kalıbı. {no} yerine gönderi numarası konur.
# Not: Bu resmi bir API değil - firmanın herkese açık web sorgulama sayfasına
# yönlendirir; İnterglobal için doğrulanmış bir sorgu linki bulunamadığı için
# sadece ana sayfaya yönlendirilir (numara kullanıcı tarafından elle girilir).
TRACKING_URL_TEMPLATES = {
    "DHL": "https://www.dhl.com.tr/exp-tr/express/tracking.html?AWB={no}&brand=DHL",
    "İNTERGLOBAL": "https://www.globalkargo.com/",
    "ARAS": "http://kargotakip.araskargo.com.tr/mainpage.aspx?code={no}",
    "YURTİÇİ": "https://www.yurticikargo.com/tr/online-servisler/gonderi-sorgula?code={no}",
}


def tracking_url(carrier: str, no: str):
    tpl = TRACKING_URL_TEMPLATES.get(carrier)
    if not tpl or not no:
        return None
    try:
        return tpl.format(no=no)
    except Exception:
        return tpl


def carrier_ships_to(carrier: str, il: str) -> bool:
    cfg = PRICING[carrier]
    if cfg["iller"] == "ALL":
        return True
    return il.upper() in cfg["iller"]


def calc_unit_price(carrier: str, desi: float):
    """Tek bir gönderi (desi) için birim fiyatı (KDV hariç) hesaplar."""
    cfg = PRICING[carrier]
    for lo, hi, price in cfg["tiers"]:
        if lo <= desi <= hi:
            return price
    # Aralığın üstünde
    max_lo, max_hi, max_price = cfg["tiers"][-1]
    if desi > max_hi:
        if cfg["artan_desi"] is not None:
            return max_price + (desi - max_hi) * cfg["artan_desi"]
        # Artan desi bilgisi yok (örn. DHL) -> en yakın (son) tarifeyi kullan, yaklaşık değerdir
        return max_price
    return None  # desi <= 0 gibi geçersiz durum
