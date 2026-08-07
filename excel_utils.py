# -*- coding: utf-8 -*-
"""Farklı kargo firmalarının farklı formattaki excel dosyalarından
ortak alanları (gönderi tarihi, gönderi no, alıcı adı, alıcı adresi,
varış il, ödeme şekli, desi) çıkarmak için sütun eşleştirme."""
import pandas as pd

TR_MAP = str.maketrans({
    "İ": "I", "I": "I", "ı": "I", "Ş": "S", "ş": "s",
    "Ğ": "G", "ğ": "g", "Ü": "U", "ü": "u", "Ö": "O", "ö": "o", "Ç": "C", "ç": "c",
})


def norm(s: str) -> str:
    return str(s).translate(TR_MAP).upper().strip()


# Her alan için, sütun adında aranacak anahtar kelimeler (öncelik sırasıyla)
FIELD_KEYWORDS = {
    "gonderi_tarihi": ["GONDERI TARIHI", "TARIH"],
    "gonderi_no": ["TAKIP NO", "GONDERI NO", "TAKIP SERI"],
    "alici_adi": ["ALICI UNVAN", "ALICI ADI", "ALICI AD"],
    "alici_adresi": ["ALICI ADRES"],
    "varis_il": ["VARIS IL", "ALICI IL", "TESLIM IL"],
    "odeme_sekli": ["ODEME SEKLI", "ODEME TIPI"],
    "desi": ["KGDESI", "DESI"],
}


def bul_sutun(columns, keywords, haric=None):
    """Anahtar kelimeyi sütun adında KELİME SINIRI ile arar (örn. 'ALICI IL',
    'ALICI ILCE' içinde yanlışlıkla eşleşmesin diye). haric: içermemesi gereken kelimeler."""
    norm_cols = {c: norm(c) for c in columns}
    for kw in keywords:
        kw_n = norm(kw)
        for orig, n in norm_cols.items():
            if haric and any(h in n for h in haric):
                continue
            # kelime sınırı: kw_n tam kelime(ler) olarak geçsin, bir sonraki karakter harf olmasın
            idx = n.find(kw_n)
            if idx == -1:
                continue
            son_idx = idx + len(kw_n)
            if son_idx < len(n) and n[son_idx].isalpha():
                continue
            return orig
    return None


def esle_sutunlar(columns):
    """Her standart alan için (varsa) gerçek sütun adını döndürür."""
    sonuc = {}
    for field, kws in FIELD_KEYWORDS.items():
        haric = ["ILCE"] if field == "varis_il" else None
        sonuc[field] = bul_sutun(columns, kws, haric=haric)
    return sonuc


def _basliksatiri_bul(dosya):
    """İlk 6 satır içinde, tanıdık anahtar kelimeleri en çok içeren satırı başlık kabul eder."""
    ham = pd.read_excel(dosya, header=None, nrows=6)
    tum_kw = [kw for kws in FIELD_KEYWORDS.values() for kw in kws]
    en_iyi_satir, en_iyi_skor = 0, -1
    for i in range(len(ham)):
        hucreler = [norm(v) for v in ham.iloc[i].tolist() if pd.notna(v)]
        skor = sum(1 for h in hucreler for kw in tum_kw if norm(kw) in h)
        if skor > en_iyi_skor:
            en_iyi_skor, en_iyi_satir = skor, i
    return en_iyi_satir


def excel_oku(dosya) -> pd.DataFrame:
    """Yüklenen excel dosyasını (xls/xlsx) DataFrame olarak okur.
    Bazı kargo firmalarının excel'lerinde üstte rapor başlığı satırı olabildiği
    için gerçek sütun başlığı satırını otomatik tespit eder."""
    if hasattr(dosya, "seek"):
        dosya.seek(0)
    header_row = _basliksatiri_bul(dosya)
    if hasattr(dosya, "seek"):
        dosya.seek(0)
    df = pd.read_excel(dosya, header=header_row)
    return df


def standart_satirlara_donustur(df: pd.DataFrame):
    """DataFrame'i, esleşen sütunlara göre standart alan sözlükleri listesine çevirir."""
    mapping = esle_sutunlar(df.columns)
    satirlar = []
    for _, row in df.iterrows():
        satir = {}
        for field, col in mapping.items():
            if col is not None and col in df.columns:
                val = row[col]
                satir[field] = None if pd.isna(val) else str(val)
            else:
                satir[field] = None
        # Tamamen boş satırları atla
        if any(v not in (None, "", "nan") for v in satir.values()):
            satirlar.append(satir)
    return satirlar, mapping


def sayim_satirlarini_filtrele(dosya) -> pd.DataFrame:
    """Depo sayım excel'inde 'Sayım' sütununu bulur ve sadece bu sütunda
    (o gün fiilen sayılmış, yani) sayısal bir değer girilmiş satırları,
    diğer tüm sütunlarla birlikte döndürür."""
    if hasattr(dosya, "seek"):
        dosya.seek(0)
    df = pd.read_excel(dosya)
    sayim_col = bul_sutun(df.columns, ["SAYIM ADEDI", "SAYIM MIKTARI", "SAYILAN", "SAYIM"])
    if sayim_col is None:
        bos = df.iloc[0:0].copy()
        bos.attrs["hata"] = f"'Sayım' sütunu bulunamadı. Dosyadaki sütunlar: {list(df.columns)}"
        return bos

    def _sayisal_mi(v):
        if pd.isna(v) or str(v).strip() == "":
            return False
        try:
            float(str(v).replace(",", "."))
            return True
        except Exception:
            return False

    mask = df[sayim_col].apply(_sayisal_mi)
    sonuc = df[mask].reset_index(drop=True)
    if mask.sum() == 0:
        sonuc = sonuc.copy()
        ornek_degerler = df[sayim_col].dropna().astype(str).head(5).tolist()
        sonuc.attrs["hata"] = (
            f"'{sayim_col}' sütunu bulundu ({len(df)} satır tarandı) ama sayısal değer girilmiş satır "
            f"bulunamadı. Bu sütundaki dolu ilk birkaç değer: {ornek_degerler}"
        )
    return sonuc
